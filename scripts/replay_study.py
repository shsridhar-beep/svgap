#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("study_root", type=Path)
    args = parser.parse_args()
    manifests = sorted(args.study_root.resolve().glob("*/*/manifest.toml"))
    if not manifests:
        parser.error("no candidate manifests found")
    statuses: Counter[tuple[str, str, bool]] = Counter()
    for index, manifest in enumerate(manifests, 1):
        completed = subprocess.run(
            [sys.executable, "-m", "svgap", "check", str(manifest)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        report_path = manifest.parent / "report.json"
        if not report_path.is_file():
            print(f"missing report after replay: {manifest}", file=sys.stderr)
            return 2
        report = json.loads(report_path.read_text(encoding="utf-8"))
        statuses[
            (
                report["functional"]["status"],
                report["structural"]["status"],
                bool(report["gap_member"]),
            )
        ] += 1
        print(f"[{index:03d}/{len(manifests):03d}] {manifest.parent.parent.name}/{manifest.parent.name}")
        if completed.returncode not in (0, 1, 2, 3):
            print(completed.stderr, file=sys.stderr)
            return 2
    print("outcomes")
    for key, count in sorted(statuses.items()):
        print(f"  functional={key[0]} structural={key[1]} gap={key[2]}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
