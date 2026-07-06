#!/usr/bin/env python3
"""Regenerate the checked-in result registry and static evidence profiles."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for script in ("build_adoption_baseline.py", "build_result_pages.py"):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode:
            return completed.returncode
    print("result registry and evidence pages synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
