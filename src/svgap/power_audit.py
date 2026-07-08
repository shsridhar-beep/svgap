from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from svgap.audit import RESET_NAME, is_clock_port


SEQUENTIAL_LANGUAGE = re.compile(
    r"(?i)\b(?:sequential|always_ff|posedge|negedge|flip[- ]flop|register|"
    r"counter|finite state machine|\bFSM\b|pipeline|state machine)\b"
)
RESET_BEHAVIOR = re.compile(
    r"(?i)(?:\b(?:on|when|if|during|upon)\b[^.\n]{0,50}\b(?:reset|rst_n?|reset_n)\b|"
    r"\b(?:reset|rst_n?|reset_n)\b[^.\n]{0,70}\b(?:set|clear|initiali[sz]e|"
    r"value|state|zero|0|1|low|high|assert))"
)
POWER_ON_LANGUAGE = re.compile(
    r"(?i)(?:\b(?:power[- ]?on|power[- ]?up|startup|start[- ]up|"
    r"unknown initial|uninitiali[sz]ed|X[- ]propagation)\b|"
    r"\breset\b[^.\n]{0,70}\binitial state\b|"
    r"\binitial state\b[^.\n]{0,70}\breset\b)"
)
COMPREHENSIVE_RESET = re.compile(
    r"(?i)(?:\b(?:all|every|each)\b[^.\n]{0,45}\b(?:state|registers?|"
    r"state elements?|flops?|sequential elements?)\b[^.\n]{0,55}\breset|"
    r"\breset\b[^.\n]{0,55}\b(?:all|every|each)\b[^.\n]{0,45}\b(?:state|"
    r"registers?|state elements?|flops?|sequential elements?)\b)"
)
X_AWARE_HARNESS = re.compile(
    r"(?i)(?:\$isunknown\s*\(|\$anyinit\b|\banyinit\b|\bxprop\b|"
    r"(?:random|nondeterministic|arbitrary)[-_ ](?:init(?:iali[sz]ation)?|"
    r"initial[-_ ]state|power[- ]?on)|"
    r"(?:===|!==)\s*(?:\d+'[bho])?[xXzZ]+|"
    r"(?:\d+'[bho])?[xXzZ]+\s*(?:===|!==)|"
    r"\bunknown initial state\b|\buninitiali[sz]ed state\b)"
)
UNINITIALIZED_STATE_PROHIBITED = re.compile(
    r"(?i)(?:\b(?:address|fix|remove|avoid|prohibit|forbid)\b[^.\n]{0,45}"
    r"\buninitiali[sz]ed\s+(?:register|state|flop)\b|"
    r"\buninitiali[sz]ed\s+(?:register|state|flop)\b[^.\n]{0,45}"
    r"\b(?:issue|error|warning|not allowed|prohibited)\b|"
    r"\b(?:lint|issues?)\b[\s\S]{0,400}\buninitiali[sz]ed\s+register\b)"
)


@dataclass(frozen=True)
class PowerOnTaskAudit:
    task_id: str
    specification: str
    input_ports: tuple[str, ...]
    clock_ports: tuple[str, ...]
    reset_ports: tuple[str, ...]
    sequential_task: bool
    reset_exposed: bool
    reset_behavior_specified: bool
    power_on_or_initial_state_language_explicit: bool
    uninitialized_state_prohibited: bool
    comprehensive_reset_coverage_required: bool
    native_unknown_initial_state_scoring: bool
    intent_sufficient_for_ref_xprop_001: bool
    functional_oracle: bool
    manual_review: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class PowerOnBenchmarkAudit:
    benchmark: str
    source_revision: str
    tasks: tuple[PowerOnTaskAudit, ...]
    schema_version: str = "1.0"

    def summary(self) -> dict[str, int | str]:
        return {
            "benchmark": self.benchmark,
            "source_revision": self.source_revision,
            "tasks": len(self.tasks),
            "sequential_tasks": sum(task.sequential_task for task in self.tasks),
            "reset_exposed": sum(task.reset_exposed for task in self.tasks),
            "reset_behavior_specified": sum(
                task.reset_behavior_specified for task in self.tasks
            ),
            "power_on_or_initial_state_language_explicit": sum(
                task.power_on_or_initial_state_language_explicit for task in self.tasks
            ),
            "uninitialized_state_prohibited": sum(
                task.uninitialized_state_prohibited for task in self.tasks
            ),
            "comprehensive_reset_coverage_required": sum(
                task.comprehensive_reset_coverage_required for task in self.tasks
            ),
            "intent_sufficient_for_ref_xprop_001": sum(
                task.intent_sufficient_for_ref_xprop_001 for task in self.tasks
            ),
            "native_unknown_initial_state_scoring": sum(
                task.native_unknown_initial_state_scoring for task in self.tasks
            ),
            "functional_oracle": sum(task.functional_oracle for task in self.tasks),
            "manual_review": sum(task.manual_review for task in self.tasks),
        }


def classify_power_on_task(
    *,
    task_id: str,
    specification: Path,
    specification_text: str,
    harness_text: str,
    input_ports: tuple[str, ...],
    functional_oracle: bool,
) -> PowerOnTaskAudit:
    clocks = tuple(port for port in input_ports if is_clock_port(port))
    resets = tuple(port for port in input_ports if RESET_NAME.search(port))
    comprehensive_match = bool(COMPREHENSIVE_RESET.search(specification_text))
    uninitialized_prohibited = bool(
        UNINITIALIZED_STATE_PROHIBITED.search(specification_text)
    )
    comprehensive = comprehensive_match
    sequential = (
        bool(clocks)
        or bool(SEQUENTIAL_LANGUAGE.search(specification_text))
        or comprehensive
        or uninitialized_prohibited
    )
    reset_behavior = bool(resets) and bool(RESET_BEHAVIOR.search(specification_text))
    power_on_explicit = bool(POWER_ON_LANGUAGE.search(specification_text))
    x_scoring = bool(X_AWARE_HARNESS.search(harness_text))
    sufficient = sequential and comprehensive
    evidence: list[str] = []
    if clocks:
        evidence.append("clock ports: " + ", ".join(clocks))
    if resets:
        evidence.append("reset ports: " + ", ".join(resets))
    if reset_behavior:
        evidence.append("specification states reset behavior")
    if power_on_explicit:
        evidence.append("specification uses explicit power-on or initial-state language")
    if uninitialized_prohibited:
        evidence.append("specification prohibits uninitialized sequential state")
    if comprehensive:
        evidence.append("specification requires comprehensive state reset coverage")
    if x_scoring:
        evidence.append("harness contains explicit unknown-initial-state scoring")
    return PowerOnTaskAudit(
        task_id=task_id,
        specification=str(specification),
        input_ports=input_ports,
        clock_ports=clocks,
        reset_ports=resets,
        sequential_task=sequential,
        reset_exposed=bool(resets),
        reset_behavior_specified=reset_behavior,
        power_on_or_initial_state_language_explicit=power_on_explicit,
        uninitialized_state_prohibited=uninitialized_prohibited,
        comprehensive_reset_coverage_required=comprehensive,
        native_unknown_initial_state_scoring=x_scoring,
        intent_sufficient_for_ref_xprop_001=sufficient,
        functional_oracle=functional_oracle,
        manual_review=comprehensive or power_on_explicit or x_scoring,
        evidence=tuple(evidence),
    )


def write_power_on_audit(audit: PowerOnBenchmarkAudit, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"power-on-{audit.benchmark}"
    payload = {
        "schema_version": audit.schema_version,
        "summary": audit.summary(),
        "tasks": [asdict(task) for task in audit.tasks],
    }
    (output_dir / f"{stem}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = [asdict(task) for task in audit.tasks]
    with (output_dir / f"{stem}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def combine_harness_files(files: Iterable[Path]) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in files
        if path.is_file()
    )
