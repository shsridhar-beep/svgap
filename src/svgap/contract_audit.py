from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from svgap.audit import file_revision, git_revision


BOUNDED_TEMPORAL = re.compile(
    r"(?i)(?:\bwithin\s+(?:\d+|one|two|three|four|a)\s*(?:clock[- ]?)?cycles?\b|"
    r"\b(?:exactly\s+)?(?:\d+|one|two|three|four|single)[- ]cycles?\b|"
    r"\b(?:next|following)\s+(?:clock\s+)?cycle\b|"
    r"\bcycle\s+(?:after|before|later)\b|"
    r"\blatency\s+(?:of|is|=)?\s*(?:\d+|one|two|three|four)\s*cycles?\b|"
    r"\bafter\s+(?:\d+|one|two|three|four)\s*(?:clock[- ]?)?cycles?\b|"
    r"\bfor\s+(?:exactly\s+)?(?:\d+|one|two|three|four)\s+consecutive\s+cycles?\b)"
)
PERSISTENCE_TEMPORAL = re.compile(
    r"(?i)(?:\b(?:remain|stay|hold|keep)\b[^.\n]{0,100}"
    r"\b(?:asserted|deasserted|high|low|stable|unchanged)\b[^.\n]{0,100}"
    r"\b(?:until|while)\b|"
    r"\b(?:must|shall)\s+not\s+change\b[^.\n]{0,100}\b(?:until|while)\b|"
    r"\bvalid\b[^.\n]{0,100}\b(?:until|while)\b[^.\n]{0,70}\bready\b)"
)
PROGRESS_TEMPORAL = re.compile(
    r"(?i)(?:\beventually\b|\bforward progress\b|"
    r"\b(?:deadlock|livelock|starvation)[- ]?free\b|"
    r"\bno\s+(?:deadlock|livelock|starvation)\b|\bfairness\b|"
    r"\bevery\s+request\b[^.\n]{0,120}\b(?:acknowledg|respond|response|grant|complete)|"
    r"\brequest\b[^.\n]{0,100}\b(?:must|shall)\b[^.\n]{0,50}"
    r"\b(?:acknowledg|respond|grant|complete))"
)
PROTOCOL_TEMPORAL = re.compile(
    r"(?i)(?:\b(?:ready\s*[/&_-]\s*valid|valid\s*[/&_-]\s*ready)\b|"
    r"\b(?:req(?:uest)?\s*[/&_-]\s*ack(?:nowledge)?)\b|"
    r"\bhandshake\b|\bback[- ]?pressure\b|"
    r"\b(?:drop|duplicate|reorder)(?:ped|s|ing)?\s+(?:data|requests?|responses?|transactions?|packets?)\b|"
    r"\b(?:requests?|responses?|transactions?|packets?|beats?)\b[^.\n]{0,60}"
    r"\b(?:in[- ]order|out[- ]of[- ]order)\b|"
    r"\b(?:fifo|queue|buffer)\b[^.\n]{0,60}\b(?:overflow|underflow)\b|"
    r"\b(?:overflow|underflow)\b[^.\n]{0,60}\b(?:fifo|queue|buffer)\b)"
)

SVA_SCORING = re.compile(
    r"(?is)(?:\bassert\s+property\b|\bassume\s+property\b|"
    r"\bcover\s+property\b|\bproperty\s+[A-Za-z_$][A-Za-z0-9_$]*\b.*?"
    r"\bendproperty\b|\bsequence\s+[A-Za-z_$][A-Za-z0-9_$]*\b.*?"
    r"\bendsequence\b|\|->|\|=>|"
    r"\$(?:past|stable|rose|fell|changed)\s*\(|\bs_eventually\b|"
    r"\bthroughout\b)"
)
FORMAL_SCORING = re.compile(
    r"(?i)(?:\bsymbiyosys\b|(?:^|[/_.-])sby(?:\s|$)|\bsmtbmc\b|"
    r"\bmode\s+(?:prove|bmc|cover)\b|\byosys[^\n]{0,160}\bsat\b[^\n]{0,100}\bprove|"
    r"\bformal[-_ ](?:engine|property verification|proof)\b)"
)
FINITE_TRACE_EVENT = re.compile(
    r"(?is)(?:(?:RisingEdge|FallingEdge|ClockCycles|Timer)\s*\(|"
    r"@\s*\(\s*(?:posedge|negedge)|\brepeat\s*\([^)]*\)\s*@|"
    r"\bwait\s*\([^)]*\)|#\s*(?:\d+|\())"
)
FINITE_TRACE_CHECK = re.compile(
    r"(?i)(?:\bassert\b|\$fatal|\$error|AssertionError|mismatch|expected|"
    r"reference_data|\bpassed\b|\berror\b)"
)
REFERENCE_TRACE_SCORING = re.compile(
    r"(?i)(?:\bRefModule\b|\breference[-_ ](?:model|design|output)\b|"
    r"\bgolden[-_ ](?:model|design|output|trace)\b|\bscoreboard\b)"
)

SYNTHESIS_CONTRACT = re.compile(
    r"(?i)(?:\bsynthesi[sz](?:able|ability|e|ed|is)\b|\bpost[- ]synthesis\b|"
    r"\bgate[- ]level\b|\bnetlist\b|\barea optimization\b|"
    r"\b(?:timing|power|PPA)\s+optimization\b|"
    r"\b(?:reduc(?:e|ed|ing)|minimi[sz](?:e|ed|ing)|"
    r"optimi[sz](?:e|ed|ing))\b[^.\n]{0,40}"
    r"\b(?:cell|logic|circuit|design)?\s*area\b)"
)
EQUIVALENCE_CONTRACT = re.compile(
    r"(?i)(?:\bfunctional(?:ly)?\s+equivalen(?:t|ce)\b|"
    r"\bequivalent\s+to\s+(?:the\s+)?(?:original|reference|golden)\b|"
    r"\bpreserv(?:e|es|ing)\s+(?:the\s+)?(?:behavior|semantics)\s+of\s+"
    r"(?:the\s+)?(?:original|reference|golden)\b|"
    r"\bpreserv(?:e|es|ing)\b[^.\n]{0,80}\b(?:original|reference|golden)\b"
    r"[^.\n]{0,80}\b(?:functionality|behavior|semantics)\b)"
)
SYNTHESIS_SCORING = re.compile(
    r"(?i)(?:\byosys\b|\bsynth_design\b|\bquartus_sh\b|\bvivado\b|"
    r"\bdc_shell\b|\bgenus\b|\bopenroad\b|\bwrite_(?:verilog|edif|json)\b)"
)
POST_SYNTHESIS_BEHAVIOR = re.compile(
    r"(?i)(?:\bpost[-_ ]synth(?:esis)?[-_ ]sim(?:ulation)?\b|"
    r"\bgate[-_ ]level[-_ ]sim(?:ulation)?\b|"
    r"\bnetlist\b[^\n]{0,160}\b(?:iverilog|verilator|cocotb|simulate|simulation)\b|"
    r"\b(?:iverilog|verilator|cocotb|simulate|simulation)\b[^\n]{0,160}\bnetlist\b)"
)
EQUIVALENCE_SCORING = re.compile(
    r"(?i)(?:\beqy\b|\bequiv_(?:make|simple|induct|status)\b|"
    r"\bformal[-_ ]equivalence\b|\blogic[-_ ]equivalence\b|"
    r"\b(?:conformal|formality)\b|\bcompare[-_ ]points\b|\bLEC\b)"
)


@dataclass(frozen=True)
class ContractTaskAudit:
    task_id: str
    specification: str
    functional_oracle: bool
    public_reference_rtl: bool
    bounded_temporal_contract: bool
    persistence_temporal_contract: bool
    progress_or_liveness_contract: bool
    protocol_or_ordering_contract: bool
    temporal_contract_explicit: bool
    native_temporal_assertion_scoring: bool
    formal_temporal_scoring: bool
    finite_trace_temporal_scoring: bool
    reference_trace_scoring: bool
    synthesis_contract_explicit: bool
    equivalence_contract_explicit: bool
    synthesis_scoring: bool
    post_synthesis_behavior_scoring: bool
    formal_equivalence_scoring: bool
    temporal_contract_without_property_or_formal: bool
    progress_contract_without_formal: bool
    equivalence_contract_without_formal_equivalence: bool
    synthesis_contract_without_synthesis: bool
    manual_review: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ContractBenchmarkAudit:
    benchmark: str
    source_revision: str
    tasks: tuple[ContractTaskAudit, ...]
    schema_version: str = "1.0"

    def summary(self) -> dict[str, int | str]:
        fields = (
            "functional_oracle",
            "public_reference_rtl",
            "bounded_temporal_contract",
            "persistence_temporal_contract",
            "progress_or_liveness_contract",
            "protocol_or_ordering_contract",
            "temporal_contract_explicit",
            "native_temporal_assertion_scoring",
            "formal_temporal_scoring",
            "finite_trace_temporal_scoring",
            "reference_trace_scoring",
            "synthesis_contract_explicit",
            "equivalence_contract_explicit",
            "synthesis_scoring",
            "post_synthesis_behavior_scoring",
            "formal_equivalence_scoring",
            "temporal_contract_without_property_or_formal",
            "progress_contract_without_formal",
            "equivalence_contract_without_formal_equivalence",
            "synthesis_contract_without_synthesis",
            "manual_review",
        )
        summary: dict[str, int | str] = {
            "benchmark": self.benchmark,
            "source_revision": self.source_revision,
            "tasks": len(self.tasks),
        }
        summary.update(
            {field: sum(bool(getattr(task, field)) for task in self.tasks) for field in fields}
        )
        return summary


def classify_contract_task(
    *,
    task_id: str,
    specification: Path,
    specification_text: str,
    harness_text: str,
    harness_names: tuple[str, ...],
    functional_oracle: bool,
    public_reference_rtl: bool,
) -> ContractTaskAudit:
    bounded = bool(BOUNDED_TEMPORAL.search(specification_text))
    persistence = bool(PERSISTENCE_TEMPORAL.search(specification_text))
    progress = bool(PROGRESS_TEMPORAL.search(specification_text))
    protocol = bool(PROTOCOL_TEMPORAL.search(specification_text))
    temporal = bounded or persistence or progress or protocol
    assertion_scoring = bool(SVA_SCORING.search(harness_text)) or any(
        Path(name).suffix.lower() == ".sva" for name in harness_names
    )
    formal_scoring = bool(FORMAL_SCORING.search(harness_text)) or any(
        Path(name).suffix.lower() in (".sby", ".tcl") and "formal" in name.lower()
        for name in harness_names
    )
    finite_trace = bool(FINITE_TRACE_EVENT.search(harness_text)) and bool(
        FINITE_TRACE_CHECK.search(harness_text)
    )
    reference_trace = bool(REFERENCE_TRACE_SCORING.search(harness_text))
    synthesis_contract = bool(SYNTHESIS_CONTRACT.search(specification_text))
    equivalence_contract = bool(EQUIVALENCE_CONTRACT.search(specification_text))
    combined_harness = "\n".join((*harness_names, harness_text))
    synthesis_scoring = bool(SYNTHESIS_SCORING.search(combined_harness))
    post_synthesis = bool(POST_SYNTHESIS_BEHAVIOR.search(combined_harness))
    formal_equivalence = bool(EQUIVALENCE_SCORING.search(combined_harness))

    evidence: list[str] = []
    for label, pattern, text in (
        ("bounded temporal contract", BOUNDED_TEMPORAL, specification_text),
        ("persistence temporal contract", PERSISTENCE_TEMPORAL, specification_text),
        ("progress/liveness contract", PROGRESS_TEMPORAL, specification_text),
        ("protocol/ordering contract", PROTOCOL_TEMPORAL, specification_text),
        ("synthesis contract", SYNTHESIS_CONTRACT, specification_text),
        ("equivalence contract", EQUIVALENCE_CONTRACT, specification_text),
        ("temporal assertion scoring", SVA_SCORING, harness_text),
        ("formal temporal scoring", FORMAL_SCORING, harness_text),
        ("synthesis scoring", SYNTHESIS_SCORING, combined_harness),
        ("post-synthesis behavior scoring", POST_SYNTHESIS_BEHAVIOR, combined_harness),
        ("formal equivalence scoring", EQUIVALENCE_SCORING, combined_harness),
    ):
        excerpt = matching_excerpt(pattern, text)
        if excerpt:
            evidence.append(f"{label}: {excerpt}")
    if public_reference_rtl:
        evidence.append("public reference RTL is present")
    if finite_trace:
        evidence.append("harness contains finite cycle/event-driven checks")
    if reference_trace:
        evidence.append("harness contains recognizable reference/scoreboard comparison")

    return ContractTaskAudit(
        task_id=task_id,
        specification=str(specification),
        functional_oracle=functional_oracle,
        public_reference_rtl=public_reference_rtl,
        bounded_temporal_contract=bounded,
        persistence_temporal_contract=persistence,
        progress_or_liveness_contract=progress,
        protocol_or_ordering_contract=protocol,
        temporal_contract_explicit=temporal,
        native_temporal_assertion_scoring=assertion_scoring,
        formal_temporal_scoring=formal_scoring,
        finite_trace_temporal_scoring=finite_trace,
        reference_trace_scoring=reference_trace,
        synthesis_contract_explicit=synthesis_contract,
        equivalence_contract_explicit=equivalence_contract,
        synthesis_scoring=synthesis_scoring,
        post_synthesis_behavior_scoring=post_synthesis,
        formal_equivalence_scoring=formal_equivalence,
        temporal_contract_without_property_or_formal=(
            temporal and not assertion_scoring and not formal_scoring
        ),
        progress_contract_without_formal=progress and not formal_scoring,
        equivalence_contract_without_formal_equivalence=(
            equivalence_contract and not formal_equivalence
        ),
        synthesis_contract_without_synthesis=(
            synthesis_contract and not synthesis_scoring
        ),
        manual_review=(
            temporal
            or synthesis_contract
            or equivalence_contract
            or assertion_scoring
            or formal_scoring
            or synthesis_scoring
            or post_synthesis
            or formal_equivalence
        ),
        evidence=tuple(evidence),
    )


def audit_verilog_eval(root: Path) -> ContractBenchmarkAudit:
    root = root.resolve()
    dataset = root / "dataset_spec-to-rtl"
    tasks: list[ContractTaskAudit] = []
    for prompt_path in sorted(dataset.glob("*_prompt.txt")):
        prefix = prompt_path.name.removesuffix("_prompt.txt")
        test_path = dataset / f"{prefix}_test.sv"
        reference_path = dataset / f"{prefix}_ref.sv"
        tasks.append(
            classify_contract_task(
                task_id=prefix,
                specification=prompt_path.relative_to(root),
                specification_text=read_text(prompt_path),
                harness_text=read_text(test_path),
                harness_names=(test_path.name,) if test_path.is_file() else (),
                functional_oracle=test_path.is_file(),
                public_reference_rtl=reference_path.is_file(),
            )
        )
    return ContractBenchmarkAudit("verilog-eval", git_revision(root), tuple(tasks))


def audit_rtllm(root: Path) -> ContractBenchmarkAudit:
    root = root.resolve()
    descriptions = sorted(
        path
        for category in ("Arithmetic", "Control", "Memory", "Miscellaneous")
        for path in (root / category).glob("**/design_description.txt")
    )
    tasks: list[ContractTaskAudit] = []
    for description in descriptions:
        task_root = description.parent
        harness_paths = tuple(
            path
            for path in sorted(task_root.iterdir())
            if path.is_file()
            and (path.name == "makefile" or path.suffix.lower() in (".v", ".sv", ".py", ".tcl", ".sby"))
            and not path.name.startswith("verified_")
        )
        references = tuple(task_root.glob("verified_*.v")) + tuple(
            task_root.glob("verified_*.sv")
        )
        test_path = task_root / "testbench.v"
        tasks.append(
            classify_contract_task(
                task_id=str(task_root.relative_to(root)),
                specification=description.relative_to(root),
                specification_text=read_text(description),
                harness_text=combine_text(harness_paths),
                harness_names=tuple(path.name for path in harness_paths),
                functional_oracle=test_path.is_file(),
                public_reference_rtl=bool(references),
            )
        )
    return ContractBenchmarkAudit("rtllm", git_revision(root), tuple(tasks))


def audit_cvdp(dataset_path: Path) -> ContractBenchmarkAudit:
    dataset_path = dataset_path.resolve()
    tasks: list[ContractTaskAudit] = []
    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            input_data = row.get("input", {})
            prompt = str(input_data.get("prompt", ""))
            context = input_data.get("context", {})
            if isinstance(context, dict):
                context_text = "\n".join(str(value) for value in context.values())
            else:
                context_text = str(context)
            specification_text = prompt + "\n" + context_text
            harness = row.get("harness", {})
            files = harness.get("files", {}) if isinstance(harness, dict) else {}
            harness_files = files if isinstance(files, dict) else {}
            equivalence_contract = bool(EQUIVALENCE_CONTRACT.search(specification_text))
            context_has_reference = equivalence_contract and bool(
                re.search(r"(?i)\bmodule\s+[A-Za-z_$][A-Za-z0-9_$]*\b", context_text)
            )
            tasks.append(
                classify_contract_task(
                    task_id=str(row.get("id", "<missing-id>")),
                    specification=Path(f"{row.get('id', '<missing-id>')}:input.prompt"),
                    specification_text=specification_text,
                    harness_text="\n".join(str(value) for value in harness_files.values()),
                    harness_names=tuple(harness_files),
                    functional_oracle=bool(harness_files),
                    public_reference_rtl=context_has_reference,
                )
            )
    return ContractBenchmarkAudit("cvdp", file_revision(dataset_path), tuple(tasks))


def write_contract_audit(audit: ContractBenchmarkAudit, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"temporal-equivalence-{audit.benchmark}"
    payload = {
        "schema_version": audit.schema_version,
        "summary": audit.summary(),
        "tasks": [asdict(task) for task in audit.tasks],
    }
    (output_dir / f"{stem}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = [asdict(task) for task in audit.tasks]
    with (output_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def combined_contract_summary(
    audits: Iterable[ContractBenchmarkAudit],
) -> dict[str, Any]:
    frozen = tuple(audits)
    tasks = tuple(task for audit in frozen for task in audit.tasks)

    def count(predicate: Any) -> int:
        return sum(bool(predicate(task)) for task in tasks)

    temporal_lower_bound = count(
        lambda task: task.temporal_contract_explicit
        and not task.native_temporal_assertion_scoring
        and not task.formal_temporal_scoring
    )
    equivalence_lower_bound = count(
        lambda task: task.equivalence_contract_explicit
        and task.public_reference_rtl
        and task.synthesis_scoring
        and not task.formal_equivalence_scoring
        and not task.post_synthesis_behavior_scoring
    )
    return {
        "schema_version": "1.0",
        "sources": {
            audit.benchmark: audit.source_revision for audit in frozen
        },
        "tasks": len(tasks),
        "functional_oracle": count(lambda task: task.functional_oracle),
        "temporal_contract_explicit": count(
            lambda task: task.temporal_contract_explicit
        ),
        "bounded_temporal_contract": count(
            lambda task: task.bounded_temporal_contract
        ),
        "persistence_temporal_contract": count(
            lambda task: task.persistence_temporal_contract
        ),
        "progress_or_liveness_contract": count(
            lambda task: task.progress_or_liveness_contract
        ),
        "protocol_or_ordering_contract": count(
            lambda task: task.protocol_or_ordering_contract
        ),
        "temporal_contract_with_finite_trace_scoring": count(
            lambda task: task.temporal_contract_explicit
            and task.finite_trace_temporal_scoring
        ),
        "temporal_contract_with_native_property_scoring": count(
            lambda task: task.temporal_contract_explicit
            and task.native_temporal_assertion_scoring
        ),
        "temporal_contract_with_formal_scoring": count(
            lambda task: task.temporal_contract_explicit
            and task.formal_temporal_scoring
        ),
        "temporal_property_gap_lower_bound": temporal_lower_bound,
        "synthesis_contract_explicit": count(
            lambda task: task.synthesis_contract_explicit
        ),
        "synthesis_contract_with_synthesis_scoring": count(
            lambda task: task.synthesis_contract_explicit
            and task.synthesis_scoring
        ),
        "synthesis_contract_without_synthesis_scoring": count(
            lambda task: task.synthesis_contract_explicit
            and not task.synthesis_scoring
        ),
        "equivalence_contract_explicit": count(
            lambda task: task.equivalence_contract_explicit
        ),
        "equivalence_contract_with_synthesis_scoring": count(
            lambda task: task.equivalence_contract_explicit
            and task.synthesis_scoring
        ),
        "equivalence_contract_with_formal_equivalence": count(
            lambda task: task.equivalence_contract_explicit
            and task.formal_equivalence_scoring
        ),
        "equivalence_contract_with_post_synthesis_behavior": count(
            lambda task: task.equivalence_contract_explicit
            and task.post_synthesis_behavior_scoring
        ),
        "synthesis_equivalence_gap_lower_bound": equivalence_lower_bound,
        "public_reference_rtl": count(lambda task: task.public_reference_rtl),
        "interpretation": {
            "lower_bound": (
                "Counts only detector-positive contracts whose supplied scoring "
                "artifacts lack the named evidence; additional gaps may exist."
            ),
            "not_prevalence": (
                "The three heterogeneous suites are a descriptive inventory, "
                "not a random sample of RTL work."
            ),
        },
    }


def write_combined_contract_summary(
    audits: Iterable[ContractBenchmarkAudit], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "temporal-equivalence-summary.json"
    path.write_text(
        json.dumps(combined_contract_summary(audits), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def matching_excerpt(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if match is None:
        return ""
    start = max(0, match.start() - 80)
    end = min(len(text), match.end() + 80)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    if start:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt += "…"
    return excerpt


def combine_text(paths: Iterable[Path]) -> str:
    return "\n".join(read_text(path) for path in paths)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
