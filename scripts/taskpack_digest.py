#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from svgap.provenance import canonical_tree_digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    print(canonical_tree_digest(args.root, exclude_names=set(args.exclude)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
