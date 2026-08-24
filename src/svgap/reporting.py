from __future__ import annotations

import html
import json
import re
from collections import Counter
from typing import Any, Iterable

from svgap.legibility import explain_evaluation_report
from svgap.validation import contributing_oracle_status, oracle_results


def build_sarif(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    reports = list(reports)
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    notifications: list[dict[str, Any]] = []
    for report in reports:
        for oracle in oracle_results(report):
            for finding in oracle["findings"]:
                rule_id = finding["rule_id"]
                rules.setdefault(
                    rule_id,
                    {
                        "id": rule_id,
                        "shortDescription": {"text": finding["message"]},
                        "defaultConfiguration": {
                            "level": sarif_level(finding["severity"])
                        },
                    },
                )
                result: dict[str, Any] = {
                    "ruleId": rule_id,
                    "level": sarif_level(finding["severity"]),
                    "message": {
                        "text": f"{report['candidate_id']}: {finding['message']}"
                    },
                    "properties": {
                        "candidate_id": report["candidate_id"],
                        "oracle_id": oracle["oracle_id"],
                        "oracle_class": oracle["oracle_class"],
                        "backend": oracle["backend"],
                        "backend_version": oracle["backend_version"],
                        "evidence": finding["evidence"],
                    },
                }
                location = finding["evidence"].get("source_location")
                parsed = (
                    parse_source_location(location)
                    if isinstance(location, str)
                    else None
                )
                if parsed:
                    uri, line, column = parsed
                    region: dict[str, int] = {"startLine": line}
                    if column is not None:
                        region["startColumn"] = column
                    result["locations"] = [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": uri},
                                "region": region,
                            }
                        }
                    ]
                results.append(result)
            for diagnostic in oracle.get("diagnostics", []):
                notifications.append(
                    {
                        "descriptor": {"id": f"SVGAP-{oracle['status'].upper()}"},
                        "message": {
                            "text": (
                                f"{report['candidate_id']} [{oracle['oracle_id']}]: "
                                f"{diagnostic}"
                            )
                        },
                        "level": (
                            "error" if oracle["status"] == "tool_error" else "warning"
                        ),
                    }
                )
    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "SV-Gap",
                "informationUri": "https://github.com/shsridhar-beep/svgap",
                "rules": [rules[key] for key in sorted(rules)],
            }
        },
        "results": results,
    }
    if notifications:
        run["invocations"] = [
            {
                "executionSuccessful": not any(
                    oracle["required"] and oracle["status"] == "tool_error"
                    for report in reports
                    for oracle in oracle_results(report)
                ),
                "toolExecutionNotifications": notifications,
            }
        ]
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "runs": [run]}


def build_html(reports: Iterable[dict[str, Any]]) -> str:
    reports = list(reports)
    outcomes = Counter(
        (report["functional"]["status"], contributing_oracle_status(report))
        for report in reports
    )
    gap_members = sum(bool(report["gap_member"]) for report in reports)
    rows = []
    explanations = []
    for report in sorted(reports, key=lambda item: item["candidate_id"]):
        profile_status = contributing_oracle_status(report)
        report_oracles = oracle_results(report)
        manifest_parts = str(report["manifest"]).replace("\\", "/").split("/")
        run = manifest_parts[-3] if len(manifest_parts) >= 3 else "unknown"
        findings = "".join(
            "<li><code>" + escape(finding["rule_id"]) + "</code> "
            + escape(finding["message"])
            + " <small>("
            + escape(oracle["oracle_id"])
            + ")</small></li>"
            for oracle in report_oracles
            for finding in oracle["findings"]
        ) or "<li>None</li>"
        rows.append(
            "<tr><td><code>" + escape(run) + "</code></td>"
            "<td><code>" + escape(report["candidate_id"]) + "</code></td>"
            "<td>" + escape(report["functional"]["status"]) + "</td>"
            "<td>" + escape(profile_status) + "</td>"
            "<td>" + ("yes" if report["gap_member"] else "no") + "</td>"
            "<td><ul>" + findings + "</ul></td></tr>"
        )
        explanation = explain_evaluation_report(report)
        explanations.append(_explanation_html(explanation, run))
    outcome_text = ", ".join(
        f"{functional}/{structural}: {count}"
        for (functional, structural), count in sorted(outcomes.items())
    )
    if gap_members:
        candidate_word = "candidate" if gap_members == 1 else "candidates"
        interpretation = (
            f"{gap_members} {candidate_word} passed the supplied functional oracle and "
            "failed a configured structural rule. Functional acceptance did not "
            "resolve every declared production question."
        )
    else:
        interpretation = (
            "No functional-pass/structural-fail candidate appears in this profile. "
            "Review unknowns and backend coverage before drawing a readiness conclusion."
        )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>SV-Gap evaluation summary</title>
<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17202a;line-height:1.45}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd1d1;padding:.55rem;text-align:left;vertical-align:top}th{background:#eef2f3}code{font-size:.9em}ul{margin:.35rem 0;padding-left:1.2rem}.summary,.meaning{padding:1rem;background:#f4f6f7;border-left:4px solid #2874a6}.meaning{margin:1rem 0;border-color:#7d3c98}.candidate{margin:1.5rem 0;padding:1rem;border:1px solid #d5d8dc;border-radius:.35rem}.boundary{color:#566573}</style>
</head><body><h1>SV-Gap evaluation summary</h1>
<div class="summary"><strong>Reports:</strong> """ + str(len(reports)) + " · <strong>Gap members:</strong> " + str(gap_members) + "<br>" + escape(outcome_text) + "</div>\n<h2>What this result means</h2><div class=\"meaning\">" + escape(interpretation) + "</div>\n<table><thead><tr><th>Run</th><th>Candidate</th><th>Functional</th><th>Contributing evidence</th><th>Gap member</th><th>Findings</th></tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table>\n<h2>Production questions and next evidence</h2>\n" + "\n".join(explanations) + "\n<p class=\"boundary\">Generated by SV-Gap. Results are conditional on supplied evidence and configured rules. A structural pass means no configured finding; it is not silicon signoff or a population-level defect estimate.</p></body></html>\n"


def _explanation_html(explanation: dict[str, Any], run: str) -> str:
    sections = []
    for heading, key in (
        ("Answered", "answered"),
        ("Failed", "failed"),
        ("Unanswered", "unanswered"),
    ):
        items = explanation[key]
        if not items:
            body = "<li>None</li>"
        else:
            body = "".join(
                "<li><strong>" + escape(item["question"]) + "</strong> - "
                + escape(item.get("answer") or item.get("reason", ""))
                + (
                    "<br><small>Evidence: "
                    + escape(item["evidence"])
                    + "</small>"
                    if item.get("evidence")
                    else ""
                )
                + "</li>"
                for item in items
            )
        sections.append(f"<h4>{heading}</h4><ul>{body}</ul>")
    next_items = "".join(
        "<li>" + escape(item) + "</li>" for item in explanation["next_evidence"]
    ) or "<li>None</li>"
    return (
        '<section class="candidate"><h3><code>'
        + escape(run)
        + "</code> / candidate <code>"
        + escape(explanation["candidate_id"])
        + "</code></h3>"
        + "".join(sections)
        + "<h4>What evidence to add next</h4><ul>"
        + next_items
        + '</ul><p class="boundary">'
        + escape(explanation["claim_boundary"])
        + "</p></section>"
    )


def sarif_level(severity: str) -> str:
    return {"error": "error", "warning": "warning", "info": "note"}.get(severity, "warning")


def parse_source_location(value: str) -> tuple[str, int, int | None] | None:
    match = re.match(r"^(.*?):(\d+)(?:\.(\d+))?(?:-.*)?$", value)
    if not match:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3)) if match.group(3) else None


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def dumps_sarif(reports: Iterable[dict[str, Any]]) -> str:
    return json.dumps(build_sarif(reports), indent=2, sort_keys=True) + "\n"
