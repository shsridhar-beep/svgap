from __future__ import annotations

from typing import Any


class ReportValidationError(ValueError):
    pass


FUNCTIONAL_STATUSES = {
    "pass",
    "fail",
    "compile_error",
    "unknown",
    "tool_error",
    "not_run",
}
STRUCTURAL_STATUSES = {"pass", "fail", "unknown", "tool_error"}


def validate_report_payload(payload: Any) -> dict[str, Any]:
    """Validate the stable fields used when importing an evaluation report.

    The published JSON Schema is the full interchange contract. This dependency-
    free validator protects CLI aggregation and plugin boundaries in minimal
    installations.
    """

    if not isinstance(payload, dict):
        raise ReportValidationError("report must be a JSON object")
    required = {
        "schema_version",
        "candidate_id",
        "manifest",
        "functional",
        "structural",
        "gap_member",
        "generated_at",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ReportValidationError("report is missing fields: " + ", ".join(missing))
    extras = sorted(payload.keys() - required)
    if extras:
        raise ReportValidationError("report has unsupported fields: " + ", ".join(extras))
    if payload["schema_version"] != "1.0":
        raise ReportValidationError("unsupported report schema_version")
    if not isinstance(payload["candidate_id"], str) or not payload["candidate_id"]:
        raise ReportValidationError("candidate_id must be a nonempty string")
    functional = payload["functional"]
    structural = payload["structural"]
    if not isinstance(functional, dict) or functional.get("status") not in FUNCTIONAL_STATUSES:
        raise ReportValidationError("invalid functional result")
    functional_allowed = {
        "status",
        "commands",
        "returncodes",
        "stdout",
        "stderr",
        "tool_versions",
        "imported_from",
        "evidence",
    }
    if set(functional) - functional_allowed:
        raise ReportValidationError("functional result has unsupported fields")
    if not isinstance(structural, dict) or structural.get("status") not in STRUCTURAL_STATUSES:
        raise ReportValidationError("invalid structural result")
    structural_required = {
        "status",
        "backend",
        "backend_version",
        "findings",
        "diagnostics",
        "tool_versions",
    }
    if not structural_required.issubset(structural) or set(structural) != structural_required:
        raise ReportValidationError("structural result fields do not match schema v1")
    if not isinstance(structural.get("findings"), list):
        raise ReportValidationError("structural findings must be an array")
    for finding in structural["findings"]:
        if not isinstance(finding, dict) or set(finding) != {
            "rule_id",
            "severity",
            "message",
            "evidence",
        }:
            raise ReportValidationError("invalid structural finding fields")
        if finding["severity"] not in {"error", "warning", "info"}:
            raise ReportValidationError("invalid finding severity")
        if not isinstance(finding["evidence"], dict):
            raise ReportValidationError("finding evidence must be an object")
    if not isinstance(payload["gap_member"], bool):
        raise ReportValidationError("gap_member must be boolean")
    expected_gap = functional["status"] == "pass" and structural["status"] == "fail"
    if payload["gap_member"] != expected_gap:
        raise ReportValidationError("gap_member is inconsistent with result statuses")
    return payload
