from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


BenchmarkKind = Literal["verilog-eval", "rtllm", "cvdp"]

CLOCK_NAME = re.compile(
    r"(?i)^(?:a?clk|clk[a-z0-9_]*|clock[a-z0-9_]*|[a-z][a-z0-9_]*_(?:a?clk|clock)|[wr]clk)$"
)
RESET_NAME = re.compile(
    r"(?i)(?:^|_)(?:a?reset|[a-z]*rstn?|rst_n)(?:$|_)"
)
ASYNC_RELATION = re.compile(
    r"(?i)\b(?:asynchronous|async(?:hronous)?|clock[- ]domain|synchroni[sz](?:e|er|ation|ed|ing))\b"
)
SYNC_DEASSERT = re.compile(
    r"(?i)\b(?:synchronous(?:ly)?\s+deassert|deassert(?:ion|ed|s)?[^.\n]{0,40}synchron)"
)
RESET_POLARITY = re.compile(
    r"(?i)\b(?:active[- ](?:high|low)|positive|negative|falling|rising)[- ](?:edge[- ])?(?:async(?:hronous)?[- ])?reset\b|defined\s+as\s+[01]\s+for\s+reset"
)


@dataclass(frozen=True)
class TaskAudit:
    task_id: str
    specification: str
    input_ports: tuple[str, ...]
    clock_ports: tuple[str, ...]
    reset_ports: tuple[str, ...]
    multi_clock: bool
    multi_reset: bool
    asynchronous_relation_explicit: bool
    synchronous_deassertion_explicit: bool
    reset_polarity_explicit: bool
    functional_oracle: bool
    constraint_files: tuple[str, ...]
    structural_oracle_files: tuple[str, ...]
    structural_risk_exposed: bool
    intent_sufficient_for_reference_audit: bool
    natively_structurally_scored: bool
    manual_review: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkAudit:
    schema_version: str
    benchmark: str
    source_revision: str
    task_count: int
    tasks: tuple[TaskAudit, ...]

    def summary(self) -> dict[str, int | str]:
        return {
            "benchmark": self.benchmark,
            "source_revision": self.source_revision,
            "tasks": self.task_count,
            "multi_clock": sum(task.multi_clock for task in self.tasks),
            "multi_reset": sum(task.multi_reset for task in self.tasks),
            "structural_risk_exposed": sum(
                task.structural_risk_exposed for task in self.tasks
            ),
            "intent_sufficient_for_reference_audit": sum(
                task.intent_sufficient_for_reference_audit for task in self.tasks
            ),
            "native_structural_scoring": sum(
                task.natively_structurally_scored for task in self.tasks
            ),
            "functional_oracle": sum(task.functional_oracle for task in self.tasks),
            "manual_review": sum(task.manual_review for task in self.tasks),
        }


def audit_benchmark(kind: BenchmarkKind, root: Path) -> BenchmarkAudit:
    root = root.resolve()
    if kind == "verilog-eval":
        tasks = tuple(audit_verilog_eval(root))
    elif kind == "rtllm":
        tasks = tuple(audit_rtllm(root))
    elif kind == "cvdp":
        tasks = tuple(audit_cvdp(root))
    else:
        raise ValueError(f"unsupported benchmark kind: {kind}")
    return BenchmarkAudit(
        schema_version="1.0",
        benchmark=kind,
        source_revision=file_revision(root) if root.is_file() else git_revision(root),
        task_count=len(tasks),
        tasks=tasks,
    )


def audit_verilog_eval(root: Path) -> Iterable[TaskAudit]:
    dataset = root / "dataset_spec-to-rtl"
    for prompt_path in sorted(dataset.glob("*_prompt.txt")):
        prefix = prompt_path.name.removesuffix("_prompt.txt")
        text = prompt_path.read_text(encoding="utf-8", errors="replace")
        inputs = tuple(
            dict.fromkeys(
                re.findall(r"(?im)^\s*-\s*input\s+([A-Za-z_][A-Za-z0-9_]*)", text)
            )
        )
        test_path = dataset / f"{prefix}_test.sv"
        yield classify_task(
            task_id=prefix,
            specification=prompt_path.relative_to(root),
            text=text,
            input_ports=inputs,
            functional_oracle=test_path.is_file(),
            task_root=dataset,
            constraint_candidates=(),
        )


def audit_rtllm(root: Path) -> Iterable[TaskAudit]:
    descriptions = sorted(
        path
        for category in ("Arithmetic", "Control", "Memory", "Miscellaneous")
        for path in (root / category).glob("**/design_description.txt")
    )
    for description in descriptions:
        text = description.read_text(encoding="utf-8", errors="replace")
        inputs = tuple(dict.fromkeys(parse_rtllm_inputs(text)))
        task_root = description.parent
        constraints = tuple(
            path for path in task_root.iterdir() if path.suffix.lower() in (".sdc", ".xdc")
        )
        yield classify_task(
            task_id=str(task_root.relative_to(root)),
            specification=description.relative_to(root),
            text=text,
            input_ports=inputs,
            functional_oracle=(task_root / "testbench.v").is_file(),
            task_root=task_root,
            constraint_candidates=constraints,
        )


def parse_rtllm_inputs(text: str) -> list[str]:
    match = re.search(r"(?is)\bInput ports\s*:(.*?)(?:\bOutput ports\s*:|\bParameter\s*:)", text)
    if match is None:
        return re.findall(
            r"(?im)^\s*input(?:\s+(?:wire|reg|logic))?(?:\s*\[[^]]+\])?\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
        )
    block = match.group(1)
    return re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", block)


def audit_cvdp(dataset_path: Path) -> Iterable[TaskAudit]:
    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            input_data = row.get("input", {})
            prompt = str(input_data.get("prompt", ""))
            context = input_data.get("context", {})
            context_text = "\n".join(
                str(value) for value in context.values()
            ) if isinstance(context, dict) else str(context)
            text = prompt + "\n" + context_text
            parsed_inputs = parse_verilog_inputs(prompt) or parse_markdown_inputs(prompt)
            if not parsed_inputs:
                parsed_inputs = parse_verilog_inputs(context_text)
            input_ports = tuple(dict.fromkeys(parsed_inputs))
            harness = row.get("harness", {})
            harness_files = harness.get("files", {}) if isinstance(harness, dict) else {}
            file_names = tuple(harness_files) if isinstance(harness_files, dict) else ()
            constraints = tuple(
                dataset_path.parent / name
                for name in file_names
                if Path(name).suffix.lower() in (".sdc", ".xdc")
            )
            structural_names = tuple(
                name
                for name in file_names
                if Path(name).suffix.lower() in (".sdc", ".xdc", ".sva")
                or re.search(r"(?i)structural[_-](?:check|report)", Path(name).name)
            )
            yield classify_task(
                task_id=str(row.get("id", "<missing-id>")),
                specification=Path(f"{row.get('id', '<missing-id>')}:input.prompt"),
                text=text,
                input_ports=input_ports,
                functional_oracle=bool(file_names),
                task_root=dataset_path.parent,
                constraint_candidates=constraints,
                structural_names=structural_names,
            )


def parse_markdown_inputs(text: str) -> list[str]:
    match = re.search(
        r"(?is)(?:^|\n)(?:#{1,5}\s*)?(?:\*{0,2})Inputs?(?:\s+(?:Ports?|Signals?))?\s*:?(?:\*{0,2})\s*:?[ \t]*\n(.*?)(?=\n(?:#{1,5}\s*)?(?:\*{0,2})(?:Outputs?(?:\s+(?:Ports?|Signals?))?|Parameters?|Behavior)\s*:?(?:\*{0,2})\s*:?[ \t]*\n|\Z)",
        text,
    )
    if match is None:
        return re.findall(
            r"(?im)^\s*-\s*(?:\*\*|`)([A-Za-z_][A-Za-z0-9_]*)(?:\*\*|`)\s*:\s*Input\b",
            text,
        )
    names: list[str] = []
    for line in match.group(1).splitlines():
        bullet = re.match(
            r"\s*-\s*(?:\*\*|`)?([A-Za-z_][A-Za-z0-9_]*)(?:\*\*|`)?(?:\s*\[[^]]+\])?\s*:",
            line,
        )
        if bullet:
            names.append(bullet.group(1))
            continue
        if "|" not in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        candidate = cells[0]
        if candidate.lower() in ("name", "signal", "port", "input") or set(candidate) <= {"-", ":"}:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate):
            names.append(candidate)
    return names


def parse_verilog_inputs(text: str) -> list[str]:
    module_match = re.search(
        r"(?ims)^\s*module\s+[A-Za-z_][A-Za-z0-9_$]*\b.*?^\s*endmodule\b",
        text,
    )
    if module_match is None:
        return []
    text = module_match.group(0)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    names: list[str] = []
    declarations = re.finditer(
        r"(?is)\binput\b(.*?)(?=;|\b(?:input|output|inout)\b|\)\s*;)", text
    )
    keywords = {"wire", "reg", "logic", "signed", "unsigned", "var"}
    for declaration in declarations:
        body = re.sub(r"\[[^]]+\]", " ", declaration.group(1))
        for item in body.split(","):
            item = item.split("=", 1)[0]
            identifiers = re.findall(r"[A-Za-z_][A-Za-z0-9_$]*", item)
            identifiers = [name for name in identifiers if name.lower() not in keywords]
            if identifiers:
                names.append(identifiers[-1])
    return names


def classify_task(
    *,
    task_id: str,
    specification: Path,
    text: str,
    input_ports: tuple[str, ...],
    functional_oracle: bool,
    task_root: Path,
    constraint_candidates: tuple[Path, ...],
    structural_names: tuple[str, ...] | None = None,
) -> TaskAudit:
    clocks = tuple(port for port in input_ports if is_clock_port(port))
    resets = tuple(port for port in input_ports if RESET_NAME.search(port))
    multi_clock = len(clocks) >= 2
    multi_reset = len(resets) >= 2
    async_relation = bool(ASYNC_RELATION.search(text))
    sync_deassert = bool(SYNC_DEASSERT.search(text))
    reset_polarity = bool(RESET_POLARITY.search(text))
    constraint_files = tuple(str(path.relative_to(task_root)) for path in constraint_candidates)
    if structural_names is None:
        structural_candidates = tuple(
            path
            for path in task_root.iterdir()
            if path.is_file()
            and (
                path.suffix.lower() in (".sdc", ".xdc", ".sva")
                or re.search(r"(?i)(?:cdc|rdc|structural)", path.name)
            )
        )
        structural_oracles = tuple(
            str(path.relative_to(task_root)) for path in structural_candidates
        )
    else:
        structural_oracles = structural_names
    structural_risk = multi_clock or sync_deassert
    sufficient = (multi_clock and async_relation) or (
        bool(resets) and sync_deassert and reset_polarity
    )
    evidence: list[str] = []
    if clocks:
        evidence.append("clock ports: " + ", ".join(clocks))
    if resets:
        evidence.append("reset ports: " + ", ".join(resets))
    if async_relation:
        evidence.append("specification contains asynchronous/synchronization intent")
    if sync_deassert:
        evidence.append("specification requires synchronous reset deassertion")
    if constraint_files:
        evidence.append("constraints: " + ", ".join(constraint_files))
    manual_review = multi_clock or multi_reset or bool(structural_oracles) or sync_deassert
    return TaskAudit(
        task_id=task_id,
        specification=str(specification),
        input_ports=input_ports,
        clock_ports=clocks,
        reset_ports=resets,
        multi_clock=multi_clock,
        multi_reset=multi_reset,
        asynchronous_relation_explicit=async_relation,
        synchronous_deassertion_explicit=sync_deassert,
        reset_polarity_explicit=reset_polarity,
        functional_oracle=functional_oracle,
        constraint_files=constraint_files,
        structural_oracle_files=structural_oracles,
        structural_risk_exposed=structural_risk,
        intent_sufficient_for_reference_audit=sufficient,
        natively_structurally_scored=bool(structural_oracles),
        manual_review=manual_review,
        evidence=tuple(evidence),
    )


def write_audit(audit: BenchmarkAudit, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{audit.benchmark}.json"
    csv_path = output_dir / f"{audit.benchmark}.csv"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": audit.schema_version,
                "summary": audit.summary(),
                "tasks": [asdict(task) for task in audit.tasks],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = [asdict(task) for task in audit.tasks]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def git_revision(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def is_clock_port(name: str) -> bool:
    lowered = name.lower()
    if (
        lowered.endswith(("_en", "_enable"))
        or lowered in ("clken", "clocken")
        or re.search(r"(?:^|_)(?:en|enable)(?:_|$)", lowered)
    ):
        return False
    return CLOCK_NAME.fullmatch(name) is not None


def file_revision(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
