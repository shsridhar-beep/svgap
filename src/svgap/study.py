from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def summarize_reports(report_paths: Iterable[Path]) -> dict[str, Any]:
    reports: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(report_paths):
        reports.append((path, json.loads(path.read_text(encoding="utf-8"))))
    outcome_counts: Counter[tuple[str, str, bool]] = Counter()
    by_task: dict[str, Counter[tuple[str, str, bool]]] = defaultdict(Counter)
    by_model: dict[str, Counter[tuple[str, str, bool]]] = defaultdict(Counter)
    rule_counts: Counter[str] = Counter()
    for path, report in reports:
        outcome = (
            report["functional"]["status"],
            report["structural"]["status"],
            bool(report["gap_member"]),
        )
        outcome_counts[outcome] += 1
        by_task[report["candidate_id"]][outcome] += 1
        run_id = path.parent.parent.name
        model = run_id.split("--sample-", 1)[0]
        by_model[model][outcome] += 1
        rule_counts.update(
            finding["rule_id"] for finding in report["structural"].get("findings", [])
        )
    functional_pass = sum(
        count for (functional, _structural, _gap), count in outcome_counts.items()
        if functional == "pass"
    )
    determinate_pass = sum(
        count for (functional, structural, _gap), count in outcome_counts.items()
        if functional == "pass" and structural in ("pass", "fail")
    )
    gap_members = sum(
        count for (_functional, _structural, gap), count in outcome_counts.items() if gap
    )
    return {
        "schema_version": "1.0",
        "report_count": len(reports),
        "functional_pass": functional_pass,
        "structurally_determinate_functional_pass": determinate_pass,
        "gap_members": gap_members,
        "detected_gap_fraction": gap_members / determinate_pass if determinate_pass else None,
        "outcomes": [
            {
                "functional": key[0],
                "structural": key[1],
                "gap_member": key[2],
                "count": value,
            }
            for key, value in sorted(outcome_counts.items())
        ],
        "rules": dict(sorted(rule_counts.items())),
        "by_task": {key: compact_counts(value) for key, value in sorted(by_task.items())},
        "by_model": {key: compact_counts(value) for key, value in sorted(by_model.items())},
    }


def compact_counts(counts: Counter[tuple[str, str, bool]]) -> dict[str, int]:
    return {
        "candidates": sum(counts.values()),
        "functional_pass": sum(
            count for (functional, _structural, _gap), count in counts.items()
            if functional == "pass"
        ),
        "gap_members": sum(
            count for (_functional, _structural, gap), count in counts.items() if gap
        ),
    }
