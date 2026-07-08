#!/usr/bin/env python3
"""Build a deterministic challenge sample for the power-on benchmark audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "reports" / "audits"
OUTPUT = AUDITS / "power-on-validation-sample-v0.1.csv"
SEED = "svgap-power-on-audit-validation-v0.1"
NEGATIVE_TARGETS = {"verilog-eval": 20, "rtllm": 15, "cvdp": 15}


def rank(benchmark: str, task_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{benchmark}:{task_id}".encode()).hexdigest()


def main() -> int:
    rows = []
    for benchmark, negative_target in NEGATIVE_TARGETS.items():
        payload = json.loads(
            (AUDITS / f"power-on-{benchmark}.json").read_text(encoding="utf-8")
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
                    "detector_comprehensive_intent": task[
                        "intent_sufficient_for_ref_xprop_001"
                    ],
                    "detector_native_unknown_scoring": task[
                        "native_unknown_initial_state_scoring"
                    ],
                    "review_comprehensive_intent": "",
                    "review_native_unknown_scoring": "",
                    "reviewer": "",
                    "evidence": "",
                }
            )
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows        {len(rows)}")
    print(f"seed        {SEED}")
    print(f"output      {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
