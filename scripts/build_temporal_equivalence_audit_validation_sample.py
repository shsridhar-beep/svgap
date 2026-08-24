#!/usr/bin/env python3
"""Build a deterministic challenge sample for the contract-coverage audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "reports" / "audits"
OUTPUT = AUDITS / "temporal-equivalence-validation-sample-v0.1.csv"
SEED = "svgap-temporal-equivalence-audit-validation-v0.1"
NEGATIVE_TARGETS = {"verilog-eval": 20, "rtllm": 15, "cvdp": 15}


def rank(benchmark: str, task_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{benchmark}:{task_id}".encode()).hexdigest()


def main() -> int:
    rows: list[dict[str, object]] = []
    for benchmark, negative_target in NEGATIVE_TARGETS.items():
        payload = json.loads(
            (AUDITS / f"temporal-equivalence-{benchmark}.json").read_text(
                encoding="utf-8"
            )
        )
        positives = [task for task in payload["tasks"] if task["manual_review"]]
        negatives = sorted(
            (task for task in payload["tasks"] if not task["manual_review"]),
            key=lambda task: rank(benchmark, task["task_id"]),
        )[:negative_target]
        selected = [
            *(("detector-positive", task) for task in positives),
            *(("detector-negative-sample", task) for task in negatives),
        ]
        for stratum, task in selected:
            rows.append(
                {
                    "benchmark": benchmark,
                    "task_id": task["task_id"],
                    "specification": task["specification"],
                    "stratum": stratum,
                    "detector_temporal_contract": task["temporal_contract_explicit"],
                    "detector_protocol_contract": task["protocol_or_ordering_contract"],
                    "detector_native_temporal_property": task[
                        "native_temporal_assertion_scoring"
                    ],
                    "detector_formal_temporal": task["formal_temporal_scoring"],
                    "detector_synthesis_contract": task[
                        "synthesis_contract_explicit"
                    ],
                    "detector_synthesis_scoring": task["synthesis_scoring"],
                    "detector_equivalence_contract": task[
                        "equivalence_contract_explicit"
                    ],
                    "detector_formal_equivalence": task[
                        "formal_equivalence_scoring"
                    ],
                    "detector_post_synthesis_behavior": task[
                        "post_synthesis_behavior_scoring"
                    ],
                    "review_temporal_contract": "",
                    "review_protocol_contract": "",
                    "review_native_temporal_property": "",
                    "review_formal_temporal": "",
                    "review_synthesis_contract": "",
                    "review_synthesis_scoring": "",
                    "review_equivalence_contract": "",
                    "review_formal_equivalence": "",
                    "review_post_synthesis_behavior": "",
                    "reviewer": "",
                    "review_evidence": "",
                }
            )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows        {len(rows)}")
    print(f"seed        {SEED}")
    print(f"output      {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
