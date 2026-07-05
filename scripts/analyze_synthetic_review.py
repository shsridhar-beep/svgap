#!/usr/bin/env python3
"""Summarize blinded synthetic reset adjudication without exposing identities."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/generated/synthetic-review-v0.1"
DEFAULT_OUTPUT = ROOT / "reports/generated/synthetic-review-v0.1-summary.json"
TARGET_MAPPING = ROOT / "reports/generated/reset-replication-v0.3-review-mapping.json"
CALIBRATION_MAPPING = ROOT / "reports/generated/synthetic-calibration-v0.1-mapping.json"
REVIEWERS = (
    "openai-frontier-b",
    "gpt-5.5",
    "claude-fable-5",
    "claude-haiku-4-5",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    calibration = mapping_by_id(CALIBRATION_MAPPING)
    targets = mapping_by_id(TARGET_MAPPING)
    expected_ids = set(calibration) | set(targets)
    panels: dict[str, dict[str, str]] = {}
    calibration_scores = []
    missing = []
    panel_metadata = []

    for reviewer in REVIEWERS:
        for repeat in (1, 2):
            panel = f"{reviewer}/repeat-{repeat:02d}"
            directory = args.input / reviewer / f"repeat-{repeat:02d}"
            decisions = load_decisions(directory)
            metadata_path = directory / "metadata.json"
            if not metadata_path.is_file():
                missing.append({"panel": panel, "metadata": "missing"})
                metadata = {}
            else:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("completed_count") != len(expected_ids) or metadata.get("failures"):
                    missing.append(
                        {
                            "panel": panel,
                            "metadata_completed": metadata.get("completed_count"),
                            "metadata_failures": len(metadata.get("failures", [])),
                        }
                    )
                panel_metadata.append(
                    {
                        "panel": panel,
                        "provider": metadata.get("provider"),
                        "model": metadata.get("model"),
                        "interface_version": metadata.get("interface_version"),
                        "rubric_sha256": metadata.get("rubric_sha256"),
                        "schema_sha256": metadata.get("schema_sha256"),
                    }
                )
            absent = sorted(expected_ids - decisions.keys())
            if absent:
                missing.append({"panel": panel, "missing_count": len(absent)})
            panels[panel] = decisions
            correct = sum(
                decisions.get(case_id) == item["expected"]
                for case_id, item in calibration.items()
            )
            calibration_scores.append(
                {
                    "panel": panel,
                    "correct": correct,
                    "total": len(calibration),
                    "accuracy": correct / len(calibration),
                }
            )

    if missing:
        raise SystemExit("incomplete review matrix: " + json.dumps(missing))
    if len({item["rubric_sha256"] for item in panel_metadata}) != 1:
        raise SystemExit("repeat panels do not share one rubric hash")
    if len({item["schema_sha256"] for item in panel_metadata}) != 1:
        raise SystemExit("repeat panels do not share one schema hash")

    within_reviewer = []
    for reviewer in REVIEWERS:
        first = panels[f"{reviewer}/repeat-01"]
        second = panels[f"{reviewer}/repeat-02"]
        within_reviewer.append(
            agreement_record(reviewer, first, second, sorted(targets))
        )

    pairwise = []
    for left, right in itertools.combinations(sorted(panels), 2):
        pairwise.append(
            agreement_record(f"{left} vs {right}", panels[left], panels[right], sorted(targets))
        )

    target_matrix = {
        case_id: [panels[panel][case_id] for panel in sorted(panels)]
        for case_id in targets
    }
    alpha = krippendorff_alpha_nominal(target_matrix.values())

    collapsed: dict[str, dict[str, str]] = {}
    for reviewer in REVIEWERS:
        first = panels[f"{reviewer}/repeat-01"]
        second = panels[f"{reviewer}/repeat-02"]
        collapsed[reviewer] = {
            case_id: first[case_id] if first[case_id] == second[case_id] else "uncertain"
            for case_id in targets
        }

    consensus = {}
    for case_id in targets:
        votes = Counter(collapsed[reviewer][case_id] for reviewer in REVIEWERS)
        yes = votes["yes"]
        no = votes["no"]
        if yes >= 3:
            decision = "yes"
        elif no >= 3:
            decision = "no"
        else:
            decision = "unresolved"
        consensus[case_id] = {"decision": decision, "votes": dict(sorted(votes.items()))}

    consensus_counts = Counter(item["decision"] for item in consensus.values())
    functional_pass_ids = {
        case_id for case_id, item in targets.items() if item["functional_status"] == "pass"
    }
    functional_consensus = Counter(
        consensus[case_id]["decision"] for case_id in functional_pass_ids
    )
    oracle_confusion = Counter()
    for case_id, item in targets.items():
        oracle = "yes" if item["structural_status"] == "fail" else "no"
        oracle_confusion[f"oracle_{oracle}__consensus_{consensus[case_id]['decision']}"] += 1

    summary = {
        "schema_version": "1.0",
        "reviewer_configurations": len(REVIEWERS),
        "repeats_per_configuration": 2,
        "target_cases": len(targets),
        "calibration_cases": len(calibration),
        "panel_metadata": panel_metadata,
        "calibration": calibration_scores,
        "within_reviewer_agreement": within_reviewer,
        "pairwise_repeat_panel_agreement": pairwise,
        "krippendorff_alpha_nominal_all_repeat_panels": alpha,
        "consensus_rule": (
            "Collapse repeat disagreement to uncertain; require at least three of "
            "four reviewer configurations for yes/no, otherwise unresolved."
        ),
        "consensus_counts_all_targets": dict(sorted(consensus_counts.items())),
        "consensus_counts_functional_pass": dict(sorted(functional_consensus.items())),
        "functional_pass_denominator": len(functional_pass_ids),
        "oracle_consensus_confusion": dict(sorted(oracle_confusion.items())),
        "unresolved_case_ids": sorted(
            case_id for case_id, item in consensus.items() if item["decision"] == "unresolved"
        ),
        "consensus_by_case": consensus,
        "interpretation": (
            "Synthetic reviewer judgments are a robustness analysis, not independent "
            "human expert adjudication or a validated defect-rate estimate."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in (
        "target_cases",
        "calibration",
        "within_reviewer_agreement",
        "krippendorff_alpha_nominal_all_repeat_panels",
        "consensus_counts_all_targets",
        "consensus_counts_functional_pass",
        "oracle_consensus_confusion",
    )}, indent=2))
    return 0


def mapping_by_id(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["case_id"]: item for item in payload["cases"]}


def load_decisions(directory: Path) -> dict[str, str]:
    decisions = {}
    for path in directory.glob("*.json"):
        if path.name == "metadata.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        decisions[path.stem] = payload["decision"]
    return decisions


def agreement_record(
    label: str,
    left: dict[str, str],
    right: dict[str, str],
    case_ids: list[str],
) -> dict[str, object]:
    matches = sum(left[case_id] == right[case_id] for case_id in case_ids)
    observed = matches / len(case_ids)
    left_counts = Counter(left[case_id] for case_id in case_ids)
    right_counts = Counter(right[case_id] for case_id in case_ids)
    expected = sum(
        left_counts[label] * right_counts[label] for label in ("yes", "no", "uncertain")
    ) / (len(case_ids) ** 2)
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {
        "comparison": label,
        "agree": matches,
        "total": len(case_ids),
        "agreement": observed,
        "cohen_kappa_nominal": kappa,
    }


def krippendorff_alpha_nominal(rows: object) -> float | None:
    rows = [list(row) for row in rows]
    pair_total = 0
    disagreements = 0
    marginals: Counter[str] = Counter()
    for row in rows:
        marginals.update(row)
        for left, right in itertools.combinations(row, 2):
            pair_total += 1
            disagreements += left != right
    if pair_total == 0:
        return None
    observed = disagreements / pair_total
    total = sum(marginals.values())
    expected = 1 - sum(count * (count - 1) for count in marginals.values()) / (
        total * (total - 1)
    )
    return None if expected == 0 else 1 - observed / expected


def render_markdown(summary: dict[str, object]) -> str:
    calibration_rows = "\n".join(
        f"| {item['panel']} | {item['correct']}/{item['total']} | "
        f"{item['accuracy']:.3f} |"
        for item in summary["calibration"]
    )
    agreement_rows = "\n".join(
        f"| {item['comparison']} | {item['agree']}/{item['total']} | "
        f"{item['agreement']:.3f} | {format_stat(item['cohen_kappa_nominal'])} |"
        for item in summary["within_reviewer_agreement"]
    )
    all_counts = summary["consensus_counts_all_targets"]
    pass_counts = summary["consensus_counts_functional_pass"]
    pairwise_agreement = [
        item["agreement"] for item in summary["pairwise_repeat_panel_agreement"]
    ]
    pairwise_kappa = [
        item["cohen_kappa_nominal"]
        for item in summary["pairwise_repeat_panel_agreement"]
        if item["cohen_kappa_nominal"] is not None
    ]
    confusion_rows = "\n".join(
        f"- `{key}`: {value}"
        for key, value in summary["oracle_consensus_confusion"].items()
    )
    return f"""# Synthetic adjudication result

Run date: 2026-07-02

This robustness study used four blinded reviewer configurations with two
isolated repeats each over 72 target candidates and 12 hidden calibration
controls. It is synthetic review, not independent human CDC/RDC adjudication.

## Calibration

| Repeat panel | Correct | Accuracy |
|---|---:|---:|
{calibration_rows}

## Repeat stability

| Reviewer configuration | Exact agreement | Rate | Cohen kappa |
|---|---:|---:|---:|
{agreement_rows}

Nominal Krippendorff alpha across all eight repeat panels was `{format_stat(summary['krippendorff_alpha_nominal_all_repeat_panels'])}`.
Across the 28 pairwise repeat-panel comparisons, exact agreement ranged from
`{min(pairwise_agreement):.3f}` to `{max(pairwise_agreement):.3f}`, and nominal Cohen kappa ranged from
`{min(pairwise_kappa):.3f}` to `{max(pairwise_kappa):.3f}`.

## Conservative consensus

Repeat disagreement collapses a configuration vote to `uncertain`; at least
three of four configurations must agree for `yes` or `no`.

- All 72 targets: yes={all_counts.get('yes', 0)}, no={all_counts.get('no', 0)}, unresolved={all_counts.get('unresolved', 0)}.
- Among {summary['functional_pass_denominator']} functional passes:
  yes={pass_counts.get('yes', 0)}, no={pass_counts.get('no', 0)}, unresolved={pass_counts.get('unresolved', 0)}.

Reference-oracle comparison:

{confusion_rows}

## Interpretation boundary

These results test whether diverse model configurations can reproduce the
case-level structural distinction under blinding. They do not establish a
population prevalence, silicon-failure rate, model ranking, or human-validated
defect rate. Any unresolved cases remain unresolved rather than being forced
through post-hoc arbitration. The author-confirmed lower-bound claim and the
human-review requirement remain in force.
"""


def format_stat(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
