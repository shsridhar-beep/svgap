#!/usr/bin/env python3
"""Build a portable, content-addressed release candidate from local study runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from svgap.provenance import canonical_file_set_digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/generated/reset-replication-v0.1"
TASKS = ROOT / "taskpacks/reset-replication-v0.1/tasks"
DEFAULT_OUTPUT = ROOT / "release_staging/reset-replication-v0.1-r3"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite release staging directory: {output}")
    candidates = output / "candidates"
    candidates.mkdir(parents=True)
    evaluator_files = sorted((ROOT / "src/svgap").rglob("*.py"))
    evaluator_digest = canonical_file_set_digest(ROOT, evaluator_files)
    index: list[dict[str, object]] = []
    manifests = sorted(args.source.resolve().glob("*/*/manifest.toml"))
    if len(manifests) != 72:
        raise SystemExit(f"expected 72 candidates, found {len(manifests)}")
    for manifest_path in manifests:
        source_dir = manifest_path.parent
        run_id = source_dir.parent.name
        task_id = source_dir.name
        target = candidates / run_id / task_id
        target.mkdir(parents=True)
        task_dir = TASKS / task_id
        for source_name, target_name in (
            (source_dir / "design.sv", "design.sv"),
            (task_dir / "prompt.md", "prompt.md"),
            (task_dir / "task.toml", "task.toml"),
            (task_dir / "tb.sv", "tb.sv"),
        ):
            shutil.copy2(source_name, target / target_name)
        original_testbench = str((task_dir / "tb.sv").resolve())
        portable_manifest = manifest_path.read_text(encoding="utf-8").replace(
            original_testbench, "tb.sv"
        )
        (target / "manifest.toml").write_text(portable_manifest, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "svgap", "check", str(target / "manifest.toml")],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode not in (0, 1, 2, 3) or not (target / "report.json").is_file():
            raise SystemExit(f"replay failed for {run_id}/{task_id}: {completed.stderr}")
        generation = json.loads((source_dir / "generation.json").read_text(encoding="utf-8"))
        generation.pop("command", None)
        generation["interface_version"] = (
            "codex-cli 0.143.0-alpha.31"
            if generation["provider"] == "codex"
            else "Claude Code 2.1.198"
        )
        (target / "generation.json").write_text(
            json.dumps(generation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        artifact_files = [
            target / name
            for name in (
                "design.sv",
                "prompt.md",
                "task.toml",
                "tb.sv",
                "manifest.toml",
                "report.json",
                "generation.json",
            )
        ]
        provenance = {
            "schema_version": "2.0",
            "run_id": run_id,
            "task_id": task_id,
            "evaluator_source_digest": evaluator_digest,
            "files": {path.name: sha256(path) for path in artifact_files},
            "candidate_bundle_digest": canonical_file_set_digest(target, artifact_files),
        }
        (target / "provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        index.append(
            {
                "run_id": run_id,
                "task_id": task_id,
                "bundle_digest": provenance["candidate_bundle_digest"],
                "functional": json.loads((target / "report.json").read_text())["functional"]["status"],
                "structural": json.loads((target / "report.json").read_text())["structural"]["status"],
            }
        )
    (output / "LICENSE.generated-rtl").write_text(
        """Generated RTL artifact license

To the extent the generated RTL and accompanying artifact metadata are subject
to copyright owned or controlled by the project author, they are licensed under
the Apache License, Version 2.0, included in the SV-Gap repository. Model names
identify generation provenance and do not imply provider endorsement.
""",
        encoding="utf-8",
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "candidate_count": len(index),
                "evaluator_source_digest": evaluator_digest,
                "candidates": index,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"candidates   {len(index)}")
    print(f"output       {output}")
    print(f"manifest     {sha256(output / 'manifest.json')}")
    return 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
