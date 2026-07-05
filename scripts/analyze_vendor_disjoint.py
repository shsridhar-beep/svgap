#!/usr/bin/env python3
"""Vendor-disjoint sensitivity analysis of the synthetic reset adjudication.

Each candidate is judged only by reviewer configurations whose vendor differs
from the vendor of the model that generated the candidate. This removes any
same-vendor (and same-family) reviewer/generator pairing from the consensus.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/generated/synthetic-review-v0.1"
DEFAULT_OUTPUT = ROOT / "reports/generated/synthetic-review-v0.1-vendor-disjoint.json"
TARGET_MAPPING = ROOT / "reports/generated/reset-replication-v0.3-review-mapping.json"
REVIEWERS = (
    "openai-frontier-b",
    "gpt-5.5",
    "claude-fable-5",
    "claude-haiku-4-5",
)


def vendor(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith(("gpt", "openai")):
        return "openai"
    raise ValueError(f"unrecognized vendor for model {model!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = json.loads(TARGET_MAPPING.read_text(encoding="utf-8"))
    targets = {item["case_id"]: item for item in payload["cases"]}

    panels: dict[str, dict[str, str]] = {}
    for reviewer in REVIEWERS:
        for repeat in (1, 2):
            directory = args.input / reviewer / f"repeat-{repeat:02d}"
            decisions = {}
            for path in directory.glob("*.json"):
                if path.name == "metadata.json":
                    continue
                decisions[path.stem] = json.loads(path.read_text(encoding="utf-8"))[
                    "decision"
                ]
            panels[f"{reviewer}/repeat-{repeat:02d}"] = decisions

    collapsed: dict[str, dict[str, str]] = {}
    for reviewer in REVIEWERS:
        first = panels[f"{reviewer}/repeat-01"]
        second = panels[f"{reviewer}/repeat-02"]
        collapsed[reviewer] = {
            case_id: first[case_id] if first[case_id] == second[case_id] else "uncertain"
            for case_id in targets
        }

    consensus: dict[str, dict[str, object]] = {}
    slice_counts: dict[str, Counter] = {}
    for case_id, item in targets.items():
        generator_vendor = vendor(item["model"])
        eligible = [r for r in REVIEWERS if vendor(r) != generator_vendor]
        if len(eligible) != 2:
            raise SystemExit(f"expected two disjoint reviewers for {case_id}")
        votes = [collapsed[r][case_id] for r in eligible]
        if votes[0] == votes[1] and votes[0] in ("yes", "no"):
            decision = votes[0]
        else:
            decision = "unresolved"
        consensus[case_id] = {
            "decision": decision,
            "eligible_reviewers": eligible,
            "votes": votes,
        }
        slice_counts.setdefault(f"generated_by_{generator_vendor}", Counter())[
            decision
        ] += 1

    consensus_counts = Counter(item["decision"] for item in consensus.values())
    functional_pass_ids = {
        case_id
        for case_id, item in targets.items()
        if item["functional_status"] == "pass"
    }
    functional_consensus = Counter(
        consensus[case_id]["decision"] for case_id in functional_pass_ids
    )
    oracle_confusion = Counter()
    for case_id, item in targets.items():
        oracle = "yes" if item["structural_status"] == "fail" else "no"
        oracle_confusion[
            f"oracle_{oracle}__consensus_{consensus[case_id]['decision']}"
        ] += 1

    summary = {
        "schema_version": "1.0",
        "rule": (
            "Per candidate, use only the two reviewer configurations whose vendor "
            "differs from the candidate's generator vendor. Collapse repeat "
            "disagreement to uncertain; require both eligible configurations to "
            "agree for yes/no, otherwise unresolved."
        ),
        "target_cases": len(targets),
        "consensus_counts_all_targets": dict(sorted(consensus_counts.items())),
        "consensus_counts_functional_pass": dict(sorted(functional_consensus.items())),
        "functional_pass_denominator": len(functional_pass_ids),
        "oracle_consensus_confusion": dict(sorted(oracle_confusion.items())),
        "counts_by_generator_vendor": {
            key: dict(sorted(value.items())) for key, value in sorted(slice_counts.items())
        },
        "unresolved_case_ids": sorted(
            case_id
            for case_id, item in consensus.items()
            if item["decision"] == "unresolved"
        ),
        "consensus_by_case": consensus,
        "interpretation": (
            "Vendor-disjoint synthetic consensus is a sensitivity analysis for "
            "vendor-correlated blind spots. It is not independent human expert "
            "adjudication or a validated defect-rate estimate."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "target_cases",
                    "consensus_counts_all_targets",
                    "consensus_counts_functional_pass",
                    "oracle_consensus_confusion",
                    "counts_by_generator_vendor",
                    "unresolved_case_ids",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
