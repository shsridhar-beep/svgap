#!/usr/bin/env python3
"""Run the frozen ordinary-lint baseline over functional-pass RTL candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERILATOR_DIAGNOSTIC = re.compile(
    r"^%(?P<severity>Warning|Error)(?:-(?P<code>[A-Z0-9_]+))?:\s*(?P<message>.*)$"
)
VERIBLE_DIAGNOSTIC = re.compile(
    r"^(?P<location>.+?:\d+:\d+(?:-\d+)?):\s*(?P<message>.*?)(?:\s+\[(?P<code>[^\]]+)\])?$"
)
RDC_SPECIFIC = re.compile(
    r"(?:"
    r"\bRDC\b|"
    r"reset[- ]domain crossing|"
    r"raw (?:async|asynchronous) reset|"
    r"(?:async|asynchronous)[- ]reset (?:release|deassertion)|"
    r"reset (?:release|deassertion).*(?:synchron|unsafe)|"
    r"reset synchroni[sz](?:er|ation).*(?:bypass|missing|unsafe)|"
    r"bypass.*reset synchroni[sz]"
    r")",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/rdc-lint-baseline-v0.1"),
        help="output directory, relative to --repo unless absolute",
    )
    parser.add_argument("--verilator", default=shutil.which("verilator"))
    parser.add_argument("--verible", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def version(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return (completed.stdout + completed.stderr).strip()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def parse_diagnostics(tool: str, stdout: str, stderr: str) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for line in (stdout + "\n" + stderr).splitlines():
        if tool == "verilator":
            match = VERILATOR_DIAGNOSTIC.match(line)
            if not match:
                continue
            message = match.group("message")
            diagnostics.append(
                {
                    "severity": match.group("severity").lower(),
                    "code": match.group("code") or match.group("severity").upper(),
                    "message": message,
                    "rdc_specific": bool(RDC_SPECIFIC.search(message)),
                }
            )
        else:
            match = VERIBLE_DIAGNOSTIC.match(line)
            if not match:
                continue
            message = match.group("message")
            diagnostics.append(
                {
                    "severity": "lint",
                    "code": match.group("code") or "syntax-or-unclassified",
                    "location": match.group("location"),
                    "message": message,
                    "rdc_specific": bool(RDC_SPECIFIC.search(message)),
                }
            )
    return diagnostics


def summarize(records: list[dict[str, Any]], tool: str) -> dict[str, Any]:
    selected = [record for record in records if record["tool"] == tool]
    groups: dict[str, Any] = {}
    for group_name, is_gap in (("gap", True), ("control", False)):
        group = [record for record in selected if record["gap_member"] is is_gap]
        code_candidates: dict[str, set[str]] = defaultdict(set)
        total_codes: Counter[str] = Counter()
        for record in group:
            candidate_key = record["candidate_key"]
            for diagnostic in record["diagnostics"]:
                code = diagnostic["code"]
                total_codes[code] += 1
                code_candidates[code].add(candidate_key)
        groups[group_name] = {
            "candidates": len(group),
            "candidates_with_any_diagnostic": sum(
                bool(record["diagnostics"]) for record in group
            ),
            "candidates_with_rdc_specific_diagnostic": sum(
                any(item["rdc_specific"] for item in record["diagnostics"])
                for record in group
            ),
            "total_diagnostics": sum(len(record["diagnostics"]) for record in group),
            "diagnostic_counts": dict(sorted(total_codes.items())),
            "candidate_counts_by_diagnostic": {
                code: len(candidates)
                for code, candidates in sorted(code_candidates.items())
            },
            "nonzero_exit_candidates": sum(record["returncode"] != 0 for record in group),
        }
    return {"tool": tool, "groups": groups}


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not args.verilator:
        raise SystemExit("verilator not found; pass --verilator")
    tools = {
        "verilator": str(Path(args.verilator).resolve()),
        "verible": str(Path(args.verible).resolve()),
    }
    for name, executable in tools.items():
        if not Path(executable).is_file():
            raise SystemExit(f"{name} executable not found: {executable}")

    artifact = repo / "artifacts/reset-replication-v0.1"
    artifact_manifest_path = artifact / "manifest.json"
    artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
    candidates = [
        item for item in artifact_manifest["candidates"] if item["functional"] == "pass"
    ]
    gap_count = sum(item["structural"] == "fail" for item in candidates)
    control_count = sum(item["structural"] == "pass" for item in candidates)
    if (len(candidates), gap_count, control_count) != (57, 14, 43):
        raise SystemExit(
            "frozen population mismatch: "
            f"functional_pass={len(candidates)}, gaps={gap_count}, controls={control_count}"
        )

    tool_versions = {
        "verilator": version([tools["verilator"], "--version"]),
        "verible": version([tools["verible"], "--version"]),
    }
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        run_id = candidate["run_id"]
        task_id = candidate["task_id"]
        candidate_key = f"{run_id}/{task_id}"
        candidate_dir = artifact / "candidates" / run_id / task_id
        manifest_path = candidate_dir / "manifest.toml"
        report_path = candidate_dir / "report.json"
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        gap_member = candidate["structural"] == "fail"
        if report["functional"]["status"] != "pass":
            raise SystemExit(f"functional status mismatch: {candidate_key}")
        if bool(report["gap_member"]) is not gap_member:
            raise SystemExit(f"gap status mismatch: {candidate_key}")
        if gap_member:
            rules = {
                item["rule_id"]
                for item in report["structural"]["findings"]
                if item["severity"] == "error"
            }
            if rules != {"REF-RDC-001"}:
                raise SystemExit(f"unexpected gap rule set {rules}: {candidate_key}")

        top = manifest["design"]["top"]
        source_names = manifest["design"]["sources"]
        source_paths = [candidate_dir / name for name in source_names]
        source_hashes = {name: sha256(path) for name, path in zip(source_names, source_paths)}
        commands = {
            "verilator": [
                tools["verilator"],
                "--lint-only",
                "--Wall",
                "--Wno-fatal",
                "--top-module",
                top,
                *source_names,
            ],
            "verible": [tools["verible"], "--ruleset=default", *source_names],
        }
        slug = f"{run_id}--{task_id}"
        for tool, command in commands.items():
            completed = run(command, candidate_dir)
            stdout_name = f"{slug}.{tool}.stdout.txt"
            stderr_name = f"{slug}.{tool}.stderr.txt"
            (raw_dir / stdout_name).write_text(completed.stdout, encoding="utf-8")
            (raw_dir / stderr_name).write_text(completed.stderr, encoding="utf-8")
            records.append(
                {
                    "candidate_key": candidate_key,
                    "run_id": run_id,
                    "task_id": task_id,
                    "bundle_digest": candidate["bundle_digest"],
                    "gap_member": gap_member,
                    "frozen_structural_status": candidate["structural"],
                    "source_hashes": source_hashes,
                    "tool": tool,
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": f"raw/{stdout_name}",
                    "stderr": f"raw/{stderr_name}",
                    "diagnostics": parse_diagnostics(tool, completed.stdout, completed.stderr),
                }
            )

    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "study": "rdc-lint-baseline-v0.1",
        "protocol": "reports/rdc-lint-baseline-v0.1/protocol.md",
        "protocol_sha256": sha256(output / "protocol.md"),
        "runner": "scripts/run_rdc_lint_baseline.py",
        "runner_sha256": sha256(Path(__file__).resolve()),
        "artifact_manifest": str(artifact_manifest_path.relative_to(repo)),
        "artifact_manifest_sha256": sha256(artifact_manifest_path),
        "population": {
            "functional_pass": len(candidates),
            "gap_members": gap_count,
            "structural_pass_controls": control_count,
        },
        "tool_versions": tool_versions,
        "tool_sha256": {
            name: sha256(Path(executable)) for name, executable in tools.items()
        },
        "summaries": [summarize(records, tool) for tool in tools],
        "records": records,
    }
    (output / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"population": payload["population"], "summaries": payload["summaries"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
