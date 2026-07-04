from __future__ import annotations

import csv
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol


Verdict = Literal[
    "hazard_demonstrated", "no_divergence_observed", "inconclusive"
]


class TraceError(ValueError):
    pass


class InstrumenterUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class TraceSample:
    cycle: int
    clock: str
    values: dict[str, str]


@dataclass(frozen=True)
class Trace:
    schema_version: str
    trace_id: str
    candidate_digest: str
    observer: dict[str, str]
    signals: tuple[str, ...]
    samples: tuple[TraceSample, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "candidate_digest": self.candidate_digest,
            "observer": self.observer,
            "signals": list(self.signals),
            "samples": [asdict(sample) for sample in self.samples],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class Divergence:
    cycle: int
    signal: str
    golden: str
    observed: str


@dataclass(frozen=True)
class ComparisonResult:
    equivalent: bool
    matched_shift: int | None = None
    first_divergence: Divergence | None = None
    diagnostics: tuple[str, ...] = ()


class Instrumenter(Protocol):
    name: str
    version: str
    mode: str

    def trace_for_seed(self, seed: int) -> Trace: ...


class MockPrerecordedInstrumenter:
    name = "mock-prerecorded"
    version = "1.0"
    mode = "mock_prerecorded"

    def __init__(self, traces: dict[int, Trace]):
        self.traces = traces

    def trace_for_seed(self, seed: int) -> Trace:
        try:
            return self.traces[seed]
        except KeyError as exc:
            raise InstrumenterUnavailable(f"no prerecorded trace for seed {seed}") from exc


class ResetReleaseSkewInstrumenter:
    """Capability marker; deliberately contains no perturbation implementation."""

    name = "reset-release-skew"
    version = "unavailable"
    mode = "unavailable"

    def trace_for_seed(self, seed: int) -> Trace:
        raise InstrumenterUnavailable(
            "ResetReleaseSkewInstrumenter is BLOCKED_PENDING_PATENT_AND_EMPLOYER_REVIEW; "
            "no netlist rewrite or reset-skew execution is included"
        )


def load_trace(path: Path) -> Trace:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceError(f"cannot read trace {path}: {exc}") from exc
    return trace_from_dict(payload)


def trace_from_dict(payload: Any) -> Trace:
    if not isinstance(payload, dict):
        raise TraceError("trace must be an object")
    allowed = {
        "schema_version",
        "trace_id",
        "candidate_digest",
        "observer",
        "signals",
        "samples",
        "provenance",
    }
    required = allowed - {"provenance"}
    if set(payload) - allowed or not required.issubset(payload):
        raise TraceError("trace fields do not match schema v1")
    if payload["schema_version"] != "1.0":
        raise TraceError("unsupported trace schema_version")
    if not isinstance(payload["trace_id"], str) or not payload["trace_id"].strip():
        raise TraceError("trace_id must be a nonempty string")
    if (
        not isinstance(payload["candidate_digest"], str)
        or not payload["candidate_digest"].strip()
    ):
        raise TraceError("candidate_digest must be a nonempty string")
    signals = payload["signals"]
    if (
        not isinstance(signals, list)
        or not signals
        or len(signals) != len(set(signals))
        or not all(isinstance(item, str) and item for item in signals)
    ):
        raise TraceError("signals must be a nonempty unique string array")
    observer = payload["observer"]
    if not isinstance(observer, dict) or set(observer) != {"name", "version", "sampling"}:
        raise TraceError("observer fields do not match schema v1")
    if not all(isinstance(value, str) and value for value in observer.values()):
        raise TraceError("observer fields must be nonempty strings")
    samples_raw = payload["samples"]
    if not isinstance(samples_raw, list) or not samples_raw:
        raise TraceError("samples must be a nonempty array")
    samples: list[TraceSample] = []
    prior_cycle = -1
    for item in samples_raw:
        if not isinstance(item, dict) or set(item) != {"cycle", "clock", "values"}:
            raise TraceError("sample fields do not match schema v1")
        cycle, clock, values = item["cycle"], item["clock"], item["values"]
        if not isinstance(cycle, int) or cycle < 0 or cycle <= prior_cycle:
            raise TraceError("sample cycles must be strictly increasing nonnegative integers")
        if not isinstance(clock, str) or not clock:
            raise TraceError("sample clock must be nonempty")
        if not isinstance(values, dict) or set(values) != set(signals):
            raise TraceError("every sample must contain exactly the declared signals")
        if not all(
            isinstance(key, str) and isinstance(value, str) and bool(value)
            for key, value in values.items()
        ):
            raise TraceError("sample values must map strings to nonempty strings")
        samples.append(TraceSample(cycle=cycle, clock=clock, values=dict(values)))
        prior_cycle = cycle
    provenance = payload.get("provenance", {})
    if not isinstance(provenance, dict):
        raise TraceError("trace provenance must be an object")
    return Trace(
        schema_version="1.0",
        trace_id=payload["trace_id"],
        candidate_digest=payload["candidate_digest"],
        observer={key: str(value) for key, value in observer.items()},
        signals=tuple(signals),
        samples=tuple(samples),
        provenance=dict(provenance),
    )


def trace_digest(trace: Trace) -> str:
    payload = json.dumps(trace.to_dict(), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def derive_seed_bits(
    study_digest: str, candidate_digest: str, seed: int, width: int
) -> tuple[int, ...]:
    if seed < 0 or width < 0:
        raise ValueError("seed and width must be nonnegative")
    key = hashlib.sha256(study_digest.encode()).digest()
    output: list[int] = []
    counter = 0
    while len(output) < width:
        message = f"{candidate_digest}:{seed}:{counter}".encode()
        block = hmac.new(key, message, hashlib.sha256).digest()
        output.extend((byte >> bit) & 1 for byte in block for bit in range(8))
        counter += 1
    return tuple(output[:width])


def compare_traces(
    golden: Trace,
    observed: Trace,
    *,
    max_shift: int = 0,
    warmup_samples: int = 0,
    x_policy: Literal["exact", "golden_x_wildcard"] = "exact",
) -> ComparisonResult:
    if max_shift < 0 or warmup_samples < 0:
        raise TraceError("max_shift and warmup_samples must be nonnegative")
    if golden.candidate_digest != observed.candidate_digest:
        raise TraceError("trace candidate digests differ")
    if golden.signals != observed.signals:
        raise TraceError("trace signal declarations differ")
    if warmup_samples >= min(len(golden.samples), len(observed.samples)):
        raise TraceError("warmup removes every comparable sample")
    attempts: list[tuple[int, int, Divergence | None]] = []
    for shift in range(max_shift + 1):
        golden_end = len(golden.samples) - shift if shift else len(golden.samples)
        golden_samples = golden.samples[warmup_samples:golden_end]
        observed_samples = observed.samples[warmup_samples + shift :]
        if not golden_samples or not observed_samples:
            continue
        if len(golden_samples) != len(observed_samples):
            attempts.append(
                (
                    0,
                    shift,
                    Divergence(
                        observed_samples[0].cycle,
                        "<trace-length>",
                        str(len(golden_samples)),
                        str(len(observed_samples)),
                    ),
                )
            )
            continue
        first: Divergence | None = None
        prefix = 0
        for index in range(len(golden_samples)):
            left = golden_samples[index]
            right = observed_samples[index]
            if left.clock != right.clock:
                first = Divergence(right.cycle, "<clock>", left.clock, right.clock)
                break
            mismatch = first_value_mismatch(left.values, right.values, golden.signals, x_policy)
            if mismatch:
                signal, expected, actual = mismatch
                first = Divergence(right.cycle, signal, expected, actual)
                break
            prefix += 1
        if first is None:
            return ComparisonResult(equivalent=True, matched_shift=shift)
        attempts.append((prefix, shift, first))
    if not attempts:
        raise TraceError("traces have no comparable samples")
    _prefix, shift, divergence = max(attempts, key=lambda item: (item[0], -item[1]))
    return ComparisonResult(
        equivalent=False,
        matched_shift=None,
        first_divergence=divergence,
        diagnostics=(f"no global shift in 0..{max_shift} matched; best attempted shift={shift}",),
    )


def first_value_mismatch(
    golden: dict[str, str],
    observed: dict[str, str],
    signals: tuple[str, ...],
    x_policy: str,
) -> tuple[str, str, str] | None:
    if x_policy not in {"exact", "golden_x_wildcard"}:
        raise TraceError(f"unsupported x_policy: {x_policy}")
    for signal in signals:
        expected, actual = golden[signal], observed[signal]
        if x_policy == "golden_x_wildcard" and set(expected.lower()) <= {"x", "z"}:
            continue
        if expected != actual:
            return signal, expected, actual
    return None


def adjudicate_prerecorded(
    *,
    candidate_id: str,
    rule_id: str,
    golden: Trace,
    instrumenter: MockPrerecordedInstrumenter,
    seeds: list[int],
    semantics_name: str,
    semantics_version: str,
    calibration_status: Literal["pass", "fail", "not_run"],
    calibration_suite_digest: str,
    max_shift: int = 0,
    warmup_samples: int = 0,
) -> dict[str, Any]:
    diagnostics: list[str] = []
    reproducer = None
    completed = 0
    verdict: Verdict = "no_divergence_observed"
    if calibration_status != "pass":
        verdict = "inconclusive"
        diagnostics.append("calibration gate did not pass")
    else:
        for seed in seeds:
            try:
                observed = instrumenter.trace_for_seed(seed)
                comparison = compare_traces(
                    golden,
                    observed,
                    max_shift=max_shift,
                    warmup_samples=warmup_samples,
                )
            except (InstrumenterUnavailable, TraceError) as exc:
                diagnostics.append(f"seed {seed}: {exc}")
                verdict = "inconclusive"
                continue
            completed += 1
            if not comparison.equivalent:
                verdict = "hazard_demonstrated"
                divergence = comparison.first_divergence
                if divergence is None:
                    raise AssertionError("non-equivalent comparison lacks divergence")
                reproducer = {
                    "seed": seed,
                    "observed_trace_digest": trace_digest(observed),
                    "first_divergence": asdict(divergence),
                }
                diagnostics.extend(comparison.diagnostics)
                break
        if completed == 0 and verdict != "hazard_demonstrated":
            verdict = "inconclusive"
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "candidate_digest": golden.candidate_digest,
        "rule_id": rule_id,
        "semantics": {"name": semantics_name, "version": semantics_version},
        "instrumenter": {
            "name": instrumenter.name,
            "version": instrumenter.version,
            "mode": instrumenter.mode,
        },
        "observer": {
            "name": golden.observer["name"],
            "version": golden.observer["version"],
        },
        "verdict": verdict,
        "seed_budget": len(seeds),
        "seeds_completed": completed,
        "golden_trace_digest": trace_digest(golden),
        "reproducer": reproducer,
        "calibration": {
            "status": calibration_status,
            "suite_digest": calibration_suite_digest,
        },
        "diagnostics": diagnostics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def trace_from_csv(
    path: Path,
    *,
    trace_id: str,
    candidate_digest: str,
    observer_name: str,
    observer_version: str,
    sampling: str,
) -> Trace:
    for name, value in (
        ("trace_id", trace_id),
        ("candidate_digest", candidate_digest),
        ("observer_name", observer_name),
        ("observer_version", observer_version),
        ("sampling", sampling),
    ):
        if not value.strip():
            raise TraceError(f"{name} must be nonempty")
    grouped: dict[tuple[int, str], dict[str, str]] = {}
    signals: set[str] = set()
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["cycle", "clock", "signal", "value"]:
                raise TraceError("trace CSV header must be cycle,clock,signal,value")
            for row in reader:
                cycle = int(row["cycle"])
                clock, signal, value = row["clock"], row["signal"], row["value"]
                if cycle < 0 or not clock or not signal or not value:
                    raise TraceError("trace CSV contains an invalid row")
                key = (cycle, clock)
                values = grouped.setdefault(key, {})
                if signal in values:
                    raise TraceError(f"duplicate trace value at cycle {cycle}: {signal}")
                values[signal] = value
                signals.add(signal)
    except (OSError, ValueError) as exc:
        raise TraceError(f"cannot normalize trace CSV: {exc}") from exc
    ordered_signals = tuple(sorted(signals))
    samples = tuple(
        TraceSample(cycle=cycle, clock=clock, values=values)
        for (cycle, clock), values in sorted(grouped.items())
    )
    if not samples or any(set(sample.values) != set(ordered_signals) for sample in samples):
        raise TraceError("every CSV sample must contain every observed signal")
    return Trace(
        schema_version="1.0",
        trace_id=trace_id,
        candidate_digest=candidate_digest,
        observer={"name": observer_name, "version": observer_version, "sampling": sampling},
        signals=ordered_signals,
        samples=samples,
        provenance={"source": path.name, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
    )


def run_calibration_suite(
    path: Path, *, max_shift: int = 0, warmup_samples: int = 0
) -> dict[str, Any]:
    path = path.resolve()
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceError(f"cannot read calibration suite: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "suite_id",
        "instrumenter",
        "cases",
    }:
        raise TraceError("calibration suite fields do not match schema v1")
    if payload["schema_version"] != "1.0" or payload["instrumenter"] != "mock_prerecorded":
        raise TraceError("unsupported calibration suite")
    if not isinstance(payload["suite_id"], str) or not payload["suite_id"].strip():
        raise TraceError("calibration suite_id must be nonempty")
    cases = payload["cases"]
    if not isinstance(cases, list) or len(cases) < 2:
        raise TraceError("calibration suite requires at least two cases")
    outcomes = []
    files = [path]
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "case_id",
            "expected",
            "golden",
            "observed",
        }:
            raise TraceError("calibration case fields do not match schema v1")
        if not isinstance(case["case_id"], str) or not case["case_id"].strip():
            raise TraceError("calibration case_id must be nonempty")
        if case["expected"] not in {
            "hazard_demonstrated",
            "no_divergence_observed",
            "inconclusive",
        }:
            raise TraceError("calibration expected verdict is unsupported")
        if not isinstance(case["golden"], str) or not case["golden"]:
            raise TraceError("calibration golden path must be nonempty")
        if (
            not isinstance(case["observed"], list)
            or not case["observed"]
            or not all(isinstance(item, str) and item for item in case["observed"])
        ):
            raise TraceError("calibration observed paths must be a nonempty string array")
        golden_path = (path.parent / case["golden"]).resolve()
        observed_paths = [(path.parent / item).resolve() for item in case["observed"]]
        if not golden_path.is_relative_to(path.parent) or any(
            not item.is_relative_to(path.parent) for item in observed_paths
        ):
            raise TraceError("calibration trace paths must remain inside the suite directory")
        files.extend([golden_path, *observed_paths])
        try:
            golden = load_trace(golden_path)
            actual: Verdict = "no_divergence_observed"
            diagnostics: list[str] = []
            for observed_path in observed_paths:
                observed = load_trace(observed_path)
                comparison = compare_traces(
                    golden,
                    observed,
                    max_shift=max_shift,
                    warmup_samples=warmup_samples,
                )
                if not comparison.equivalent:
                    actual = "hazard_demonstrated"
                    break
        except TraceError as exc:
            actual = "inconclusive"
            diagnostics = [str(exc)]
        outcomes.append(
            {
                "case_id": case["case_id"],
                "expected": case["expected"],
                "actual": actual,
                "pass": actual == case["expected"],
                "diagnostics": diagnostics,
            }
        )
    digest = hashlib.sha256()
    for file_path in sorted(set(files)):
        relative = file_path.relative_to(path.parent).as_posix()
        data = file_path.read_bytes()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return {
        "schema_version": "1.0",
        "suite_id": payload["suite_id"],
        "suite_digest": "sha256:" + digest.hexdigest(),
        "status": "pass" if all(item["pass"] for item in outcomes) else "fail",
        "cases": outcomes,
    }
