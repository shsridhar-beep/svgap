#!/usr/bin/env python3
"""Audit frozen public AI RTL benchmarks for temporal and equivalence coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from svgap.contract_audit import (  # noqa: E402
    audit_cvdp,
    audit_rtllm,
    audit_verilog_eval,
    write_combined_contract_summary,
    write_contract_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verilog-eval", type=Path, required=True)
    parser.add_argument("--rtllm", type=Path, required=True)
    parser.add_argument("--cvdp", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "audits")
    args = parser.parse_args()
    audits = (
        audit_verilog_eval(args.verilog_eval),
        audit_rtllm(args.rtllm),
        audit_cvdp(args.cvdp),
    )
    for audit in audits:
        write_contract_audit(audit, args.output)
        print(json.dumps(audit.summary(), sort_keys=True))
    combined_path = write_combined_contract_summary(audits, args.output)
    print(json.dumps({"combined_summary": str(combined_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
