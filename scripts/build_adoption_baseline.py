#!/usr/bin/env python3
"""Build the checked-in, multidimensional SV-Gap adoption baseline registry."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from svgap.submission import SubmissionError, registry_entry


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "reset-replication-v0.1" / "candidates"
BASELINE = ROOT / "results" / "baselines" / "v0.1"
SUBMISSIONS = ROOT / "results" / "submissions"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generation_profile(model: str) -> dict[str, Any]:
    paths = sorted(ARTIFACT.glob(f"{model}--sample-*/*/report.json"))
    if not paths:
        raise ValueError(f"no reports found for {model}")

    functional: Counter[str] = Counter()
    structural: Counter[str] = Counter()
    findings: Counter[str] = Counter()
    gap_members = 0
    for path in paths:
        report = read_json(path)
        functional[report["functional"]["status"]] += 1
        structural[report["structural"]["status"]] += 1
        gap_members += int(report["gap_member"])
        findings.update(item["rule_id"] for item in report["structural"]["findings"])

    return {
        "model": model,
        "candidate_reports": len(paths),
        "functional_statuses": dict(sorted(functional.items())),
        "structural_statuses": dict(sorted(structural.items())),
        "functional_pass_structural_fail": gap_members,
        "finding_counts": dict(sorted(findings.items())),
        "source": "artifacts/reset-replication-v0.1/candidates",
    }


def challenge_profile(track: str, model: str) -> dict[str, Any]:
    root = BASELINE / track / model
    result = read_json(root / "result.json")
    provenance = read_json(root / "provenance.json")
    return {
        "model": result["model"],
        "run_id": result["run_id"],
        "overall": result["overall"],
        "profile": result["profile"],
        "result": (root / "result.json").relative_to(ROOT).as_posix(),
        "submission": (root / "submission.json").relative_to(ROOT).as_posix(),
        "provenance": (root / "provenance.json").relative_to(ROOT).as_posix(),
        "provider": provenance["provider"],
    }


def build_registry() -> dict[str, Any]:
    models = ("claude-opus-4-8", "claude-sonnet-5", "openai-frontier-a")
    challenge_models = ("gpt-5.4", "openai-frontier-a")
    return {
        "schema_version": "1.0",
        "registry_id": "svgap-public-results-v0.1",
        "generated_from": "checked-in immutable reports; regenerate with scripts/build_adoption_baseline.py",
        "claim_boundary": (
            "Profiles describe submitted digital RTL evidence under configured open-source "
            "checks. They are not silicon signoff, population estimates, or model rankings."
        ),
        "generation": [generation_profile(model) for model in models],
        "diagnosis": [challenge_profile("diagnosis", model) for model in challenge_models],
        "repair": [challenge_profile("repair", model) for model in challenge_models],
        "submissions": discover_submissions(),
    }


def discover_submissions() -> list[dict[str, Any]]:
    if not SUBMISSIONS.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for directory in sorted(path.parent for path in SUBMISSIONS.glob("*/submission.json")):
        try:
            entry = registry_entry(directory)
        except SubmissionError as exc:
            raise ValueError(f"invalid result submission {directory}: {exc}") from exc
        identifier = entry["submission_id"]
        if identifier in identifiers:
            raise ValueError(f"duplicate result submission id: {identifier}")
        identifiers.add(identifier)
        entry["source"] = directory.relative_to(ROOT).as_posix()
        entries.append(entry)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "registry-v1.json",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_registry(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "registry is stale: run python scripts/sync_results.py and commit the output"
            )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
