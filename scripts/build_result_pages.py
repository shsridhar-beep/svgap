#!/usr/bin/env python3
"""Build static, citable evidence-profile pages from the public registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "results/registry-v1.json"
INDEX = ROOT / "docs/results.md"
PROFILE_DIR = ROOT / "docs/result-profiles"


def render_index(registry: dict[str, object]) -> str:
    lines = [
        "# Evidence profiles",
        "",
        "SV-Gap publishes multidimensional evidence profiles, not a scalar",
        "leaderboard. Functional failures, structural failures, unknowns, and tool",
        "errors remain visible. Every profile is bounded by its taskpack, evaluator,",
        "and provenance level.",
        "",
        "## Frozen generation baseline",
        "",
        "| Configuration | Candidates | Functional pass | Functional-pass / structural-fail |",
        "|---|---:|---:|---:|",
    ]
    for entry in registry["generation"]:  # type: ignore[index]
        functional_pass = entry["functional_statuses"].get("pass", 0)
        lines.append(
            f"| `{entry['model']}` | {entry['candidate_reports']} | {functional_pass} | "
            f"{entry['functional_pass_structural_fail']} |"
        )
    for track in ("diagnosis", "repair"):
        lines.extend(
            [
                "",
                f"## Exploratory {track} profiles",
                "",
                "| Configuration | Overall | Passed checks | Total checks |",
                "|---|---|---:|---:|",
            ]
        )
        for entry in registry[track]:  # type: ignore[index]
            passed = sum(1 for item in entry["profile"] if item["pass"])
            lines.append(
                f"| `{entry['model']}` | `{entry['overall']}` | {passed} | "
                f"{len(entry['profile'])} |"
            )
    lines.extend(
        [
            "",
            "## Public evidence submissions",
            "",
            "The profiles below are maintainer-produced anchors; independent",
            "submissions are welcome and are listed with full attribution. Start",
            "with a",
            "[one-sentence production question](https://github.com/shsridhar-beep/svgap/issues/new?template=production_question.yml)",
            "or go straight to [submitting results](submitting-results.md).",
            "",
        ]
    )
    submissions = registry["submissions"]  # type: ignore[index]
    if submissions:
        lines.extend(
            [
                "| Submission | Track | Configuration | Provenance | Contributor |",
                "|---|---|---|---|---|",
            ]
        )
        for entry in submissions:
            identifier = entry["submission_id"]
            configuration = entry["configuration"]
            lines.append(
                f"| [{entry['title']}](result-profiles/{identifier}.md) | "
                f"`{entry['track']}` | `{configuration['label']}` | "
                f"`{configuration['provenance_level']}` | {entry['contributor']} |"
            )
    else:
        lines.extend(
            [
                "No public submission has been accepted yet. The first validated",
                "generation, diagnosis, repair, failure, or abstention profile is",
                "welcome; see [Submit a result](submitting-results.md).",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            registry["claim_boundary"],  # type: ignore[index]
            "",
        ]
    )
    return "\n".join(lines)


def render_profile(entry: dict[str, object]) -> str:
    configuration = entry["configuration"]
    summary = entry["summary"]
    identifier = entry["submission_id"]
    citation = (
        f"{entry['contributor']}. \"{entry['title']}.\" SV-Gap evidence profile "
        f"{identifier}, taskpack {entry['taskpack']['id']} "
        f"{entry['taskpack']['version']}."
    )
    lines = [
        f"# {entry['title']}",
        "",
        f"- **Submission:** `{identifier}`",
        f"- **Track:** `{entry['track']}`",
        f"- **Configuration:** `{configuration['label']}`",
        f"- **Provenance:** `{configuration['provenance_level']}`",
        f"- **Contributor:** {entry['contributor']}",
        f"- **Taskpack:** `{entry['taskpack']['id']}` `{entry['taskpack']['version']}`",
    ]
    if summary["kind"] == "generation_reports":
        lines.extend(
            [
                f"- **Reports:** {summary['report_count']}",
                f"- **Functional pass:** {summary['functional_pass']}",
                f"- **Structurally determinate functional pass:** "
                f"{summary['structurally_determinate_functional_pass']}",
                f"- **Functional-pass / structural-fail:** {summary['gap_members']}",
                "",
                "## Outcome profile",
                "",
                "| Functional | Structural | Gap member | Count |",
                "|---|---|---|---:|",
            ]
        )
        for outcome in summary["outcomes"]:
            lines.append(
                f"| `{outcome['functional']}` | `{outcome['structural']}` | "
                f"`{str(outcome['gap_member']).lower()}` | {outcome['count']} |"
            )
    else:
        lines.extend(
            [
                f"- **Results:** {summary['result_count']}",
                f"- **Passing results:** {summary['overall_statuses']['pass']}",
                f"- **Failing results:** {summary['overall_statuses']['fail']}",
                "",
                "## Check profile",
                "",
                "| Check | Pass | Fail |",
                "|---|---:|---:|",
            ]
        )
        for outcome in summary["checks"]:
            lines.append(
                f"| `{outcome['check']}` | {outcome['pass']} | {outcome['fail']} |"
            )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            entry["claim_boundary"],
            "",
            "## Suggested citation",
            "",
            f"> {citation}",
            "",
            f"[Source artifacts](https://github.com/shsridhar-beep/svgap/tree/main/{entry['source']})",
            "",
        ]
    )
    return "\n".join(lines)


def outputs(registry: dict[str, object]) -> dict[Path, str]:
    rendered = {INDEX: render_index(registry)}
    for entry in registry["submissions"]:  # type: ignore[index]
        rendered[PROFILE_DIR / f"{entry['submission_id']}.md"] = render_profile(entry)
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rendered = outputs(registry)
    existing_profiles = set(PROFILE_DIR.glob("*.md")) if PROFILE_DIR.is_dir() else set()
    expected_profiles = {path for path in rendered if path.parent == PROFILE_DIR}
    if args.check:
        stale = [
            path for path, text in rendered.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        stale.extend(sorted(existing_profiles - expected_profiles))
        if stale:
            raise SystemExit(
                "result pages are stale: run python scripts/sync_results.py and commit "
                "the output; stale: " + ", ".join(str(path) for path in stale)
            )
        print("result pages current")
        return 0
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for path in existing_profiles - expected_profiles:
        path.unlink()
    for path, text in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
