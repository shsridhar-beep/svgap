from __future__ import annotations

import html
import json
import re
from collections import Counter
from typing import Any, Iterable


def build_sarif(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    reports = list(reports)
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    notifications: list[dict[str, Any]] = []
    for report in reports:
        structural = report["structural"]
        for finding in structural["findings"]:
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
                    "backend": structural["backend"],
                    "backend_version": structural["backend_version"],
                    "evidence": finding["evidence"],
                },
            }
            location = finding["evidence"].get("source_location")
            parsed = parse_source_location(location) if isinstance(location, str) else None
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
        for diagnostic in structural.get("diagnostics", []):
            notifications.append(
                {
                    "descriptor": {"id": f"SVGAP-{structural['status'].upper()}"},
                    "message": {"text": f"{report['candidate_id']}: {diagnostic}"},
                    "level": "error" if structural["status"] == "tool_error" else "warning",
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
                    report["structural"]["status"] == "tool_error" for report in reports
                ),
                "toolExecutionNotifications": notifications,
            }
        ]
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "runs": [run]}


def build_html(reports: Iterable[dict[str, Any]]) -> str:
    reports = list(reports)
    outcomes = Counter(
        (report["functional"]["status"], report["structural"]["status"])
        for report in reports
    )
    gap_members = sum(bool(report["gap_member"]) for report in reports)
    rows = []
    for report in sorted(reports, key=lambda item: item["candidate_id"]):
        manifest_parts = str(report["manifest"]).replace("\\", "/").split("/")
        run = manifest_parts[-3] if len(manifest_parts) >= 3 else "unknown"
        findings = "".join(
            "<li><code>" + escape(finding["rule_id"]) + "</code> "
            + escape(finding["message"]) + "</li>"
            for finding in report["structural"]["findings"]
        ) or "<li>None</li>"
        rows.append(
            "<tr><td><code>" + escape(run) + "</code></td>"
            "<td><code>" + escape(report["candidate_id"]) + "</code></td>"
            "<td>" + escape(report["functional"]["status"]) + "</td>"
            "<td>" + escape(report["structural"]["status"]) + "</td>"
            "<td>" + ("yes" if report["gap_member"] else "no") + "</td>"
            "<td><ul>" + findings + "</ul></td></tr>"
        )
    outcome_text = ", ".join(
        f"{functional}/{structural}: {count}"
        for (functional, structural), count in sorted(outcomes.items())
    )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SV-Gap evaluation summary</title>
<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17202a}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd1d1;padding:.55rem;text-align:left;vertical-align:top}th{background:#eef2f3}code{font-size:.9em}ul{margin:0;padding-left:1.2rem}.summary{padding:1rem;background:#f4f6f7;border-left:4px solid #2874a6}</style>
</head><body><h1>SV-Gap evaluation summary</h1>
<div class="summary"><strong>Reports:</strong> """ + str(len(reports)) + " · <strong>Gap members:</strong> " + str(gap_members) + "<br>" + escape(outcome_text) + "</div>\n<table><thead><tr><th>Run</th><th>Candidate</th><th>Functional</th><th>Structural</th><th>Gap member</th><th>Findings</th></tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table>\n<p>Generated by SV-Gap. A structural pass means no configured finding; it is not silicon signoff.</p></body></html>\n"


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
