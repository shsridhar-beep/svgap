#!/usr/bin/env python3
"""Build a model-blinded expert review packet for the reset replication."""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import secrets
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "reports/generated/reset-replication-v0.1"
DEFAULT_OUTPUT = ROOT / "review_packets/reset-replication-v0.3"
FREEZE = ROOT / "taskpacks/reset-replication-v0.1/freeze.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--mapping",
        type=Path,
        default=ROOT / "reports/generated/reset-replication-v0.3-review-mapping.json",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing packet: {output}")

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    blinding_key = secrets.token_bytes(32)
    records = collect_records(source, blinding_key)
    if len(records) != 72:
        raise SystemExit(f"expected 72 complete candidates, found {len(records)}")

    cases = output / "cases"
    cases.mkdir(parents=True)
    write_readme(output / "README.md")
    write_review_sheet(output / "review.csv", records)
    public_manifest = []
    private_mapping = []
    for record in records:
        case_path = cases / f'{record["case_id"]}.md'
        case_path.write_text(render_case(record), encoding="utf-8")
        public_manifest.append(
            {
                "case_id": record["case_id"],
                "task_id": record["task_id"],
                "prompt_sha256": record["prompt_sha256"],
                "design_sha256": record["design_sha256"],
            }
        )
        private_mapping.append(
            {
                "case_id": record["case_id"],
                "run_id": record["run_id"],
                "task_id": record["task_id"],
                "model": record["model"],
                "functional_status": record["functional_status"],
                "structural_status": record["structural_status"],
                "automated_gap_member": record["gap_member"],
            }
        )

    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskpack_digest": freeze["canonical_digest"],
                "blinding": "model, run, functional result, and automated structural result hidden",
                "case_count": len(records),
                "cases": public_manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    args.mapping.parent.mkdir(parents=True, exist_ok=True)
    args.mapping.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "blinding_key_hex": blinding_key.hex(),
                "cases": private_mapping,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    archive = shutil.make_archive(str(output), "zip", root_dir=output)
    archive_hash = sha256(Path(archive))
    print(f"cases       {len(records)}")
    print(f"packet      {output}")
    print(f"archive     {archive}")
    print(f"sha256      {archive_hash}")
    print(f"mapping     {args.mapping.resolve()} (keep blinded from reviewers)")
    return 0


def collect_records(source: Path, blinding_key: bytes) -> list[dict[str, object]]:
    records = []
    for report_path in sorted(source.glob("*/*/report.json")):
        run_dir = report_path.parent
        report = json.loads(report_path.read_text(encoding="utf-8"))
        provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
        generation = json.loads((run_dir / "generation.json").read_text(encoding="utf-8"))
        design_path = run_dir / "design.sv"
        design_hash = sha256(design_path)
        identity = (
            f'{provenance["run_id"]}:{report["candidate_id"]}:{design_hash}'.encode()
        )
        case_id = "CASE-" + hmac.new(
            blinding_key, identity, hashlib.sha256
        ).hexdigest()[:16].upper()
        task_dir = ROOT / "taskpacks/reset-replication-v0.1/tasks" / report["candidate_id"]
        prompt_path = task_dir / "prompt.md"
        records.append(
            {
                "case_id": case_id,
                "task_id": report["candidate_id"],
                "run_id": provenance["run_id"],
                "model": generation["requested_model"],
                "prompt": prompt_path.read_text(encoding="utf-8"),
                "prompt_sha256": sha256(prompt_path),
                "design": design_path.read_text(encoding="utf-8"),
                "design_sha256": design_hash,
                "functional_status": report["functional"]["status"],
                "structural_status": report["structural"]["status"],
                "gap_member": report["gap_member"],
            }
        )
    return sorted(records, key=lambda item: str(item["case_id"]))


def write_readme(path: Path) -> None:
    path.write_text(
        """# Blinded reset-release adjudication

This packet contains all 72 candidates. Model identity, sample identity,
functional outcome, and the automated structural verdict are hidden.

For every case, answer the primary question independently:

> Does any operational state element—not a reset-synchronizer stage itself—use
> the external raw asynchronous reset on its asynchronous reset input, allowing
> reset removal to reach that state without first passing through the declared
> synchronized-release path?

Record `yes`, `no`, or `uncertain`, plus confidence (`high`, `medium`, `low`) and
short evidence in `review.csv`. A reset synchronizer's own flops are expected to
use the raw reset and are exempt. Judge the submitted RTL, not whether a redesign
would be preferable. Do not consult model outputs or automated reports outside
this packet.

Please also flag malformed or ambiguous cases in `notes`. The timer task leaves
the reset value of `expired` underspecified; this affects functional-oracle
interpretation, not the structural question above.
""",
        encoding="utf-8",
    )


def write_review_sheet(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "decision", "confidence", "evidence", "notes"])
        for record in records:
            writer.writerow([record["case_id"], "", "", "", ""])


def render_case(record: dict[str, object]) -> str:
    return (
        f'# {record["case_id"]}\n\n'
        f'Prompt SHA-256: `{record["prompt_sha256"]}`  \n'
        f'Design SHA-256: `{record["design_sha256"]}`\n\n'
        f'## Task specification\n\n{record["prompt"]}\n\n'
        f'## Candidate RTL\n\n```systemverilog\n{record["design"]}```\n'
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
