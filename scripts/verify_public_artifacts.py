#!/usr/bin/env python3
"""Verify hashes and normalized outcomes in the public reset artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from svgap.provenance import canonical_file_set_digest
from svgap.validation import validate_report_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "artifacts/reset-replication-v0.1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", nargs="?", type=Path, default=DEFAULT_ARTIFACT)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    candidates = manifest["candidates"]
    if manifest["candidate_count"] != len(candidates):
        raise SystemExit("manifest candidate_count does not match index length")
    indexed = {(item["run_id"], item["task_id"]) for item in candidates}
    actual = {
        (path.parent.parent.name, path.parent.name)
        for path in (artifact / "candidates").glob("*/*/report.json")
    }
    if indexed != actual:
        raise SystemExit(
            f"artifact candidate directories differ from index: missing={sorted(indexed - actual)} "
            f"extra={sorted(actual - indexed)}"
        )

    for item in candidates:
        directory = artifact / "candidates" / item["run_id"] / item["task_id"]
        provenance = json.loads(
            (directory / "provenance.json").read_text(encoding="utf-8")
        )
        files = [directory / name for name in provenance["files"]]
        expected_names = {
            "design.sv",
            "prompt.md",
            "task.toml",
            "tb.sv",
            "manifest.toml",
            "report.json",
            "generation.json",
        }
        if set(provenance["files"]) != expected_names:
            raise SystemExit(f"unexpected provenance file set: {directory}")
        actual_names = {path.name for path in directory.iterdir() if path.is_file()}
        if actual_names != expected_names | {"provenance.json"}:
            raise SystemExit(f"unexpected candidate file set: {directory}")
        for path in files:
            if not path.is_file():
                raise SystemExit(f"missing artifact file: {path}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != provenance["files"][path.name]:
                raise SystemExit(f"hash mismatch: {path}")
        bundle = canonical_file_set_digest(directory, files)
        if bundle != provenance["candidate_bundle_digest"]:
            raise SystemExit(f"candidate bundle mismatch: {directory}")
        if bundle != item["bundle_digest"]:
            raise SystemExit(f"index bundle mismatch: {directory}")
        report = validate_report_payload(
            json.loads((directory / "report.json").read_text(encoding="utf-8"))
        )
        if report["functional"]["status"] != item["functional"]:
            raise SystemExit(f"functional status mismatch: {directory}")
        if report["structural"]["status"] != item["structural"]:
            raise SystemExit(f"structural status mismatch: {directory}")

    print(f"verified     {len(candidates)} candidates")
    print(f"artifact     {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
