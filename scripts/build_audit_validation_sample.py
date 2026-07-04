#!/usr/bin/env python3
"""Build a deterministic public sample for challenging benchmark-audit recall."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITS = ROOT / "reports/audits"
DEFAULT_OUTPUT = AUDITS / "validation-sample-v0.2.csv"
SEED = "svgap-benchmark-audit-validation-v0.2"
NEGATIVE_TARGETS = {"verilog-eval": 20, "rtllm": 15, "cvdp": 15}


def rank(benchmark: str, task_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{benchmark}:{task_id}".encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = []
    for benchmark, negative_target in NEGATIVE_TARGETS.items():
        payload = json.loads((AUDITS / f"{benchmark}.json").read_text())
        tasks = payload["tasks"]
        positives = [task for task in tasks if task["manual_review"]]
        negatives = sorted(
            (task for task in tasks if not task["manual_review"]),
            key=lambda task: rank(benchmark, task["task_id"]),
        )[:negative_target]
        for stratum, task in [*(('detector-positive', item) for item in positives), *(("detector-negative-sample", item) for item in negatives)]:
            rows.append(
                {
                    "benchmark": benchmark,
                    "task_id": task["task_id"],
                    "specification": task["specification"],
                    "stratum": stratum,
                    "detector_multi_clock": task["multi_clock"],
                    "detector_intent_sufficient": task["intent_sufficient_for_reference_audit"],
                    "detector_native_scoring": task["natively_structurally_scored"],
                    "review_multi_clock": "",
                    "review_intent_sufficient": "",
                    "review_native_scoring": "",
                    "reviewer": "",
                    "evidence": "",
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows        {len(rows)}")
    print(f"seed        {SEED}")
    print(f"output      {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
