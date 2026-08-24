from __future__ import annotations

import re
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
    schema_version = payload.get("schema_version")
    if schema_version == "2.0":
        return _validate_v2(payload)
    if schema_version != "1.0":
        raise ReportValidationError("unsupported report schema_version")

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
    if not isinstance(payload["candidate_id"], str) or not payload["candidate_id"]:
        raise ReportValidationError("candidate_id must be a nonempty string")
    if not isinstance(payload["manifest"], str) or not payload["manifest"]:
        raise ReportValidationError("manifest must be a nonempty string")
    if not isinstance(payload["generated_at"], str) or not payload["generated_at"]:
        raise ReportValidationError("generated_at must be a nonempty string")
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


def _validate_v2(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "candidate_id",
        "manifest",
        "functional",
        "oracle_results",
        "gap_member",
        "generated_at",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ReportValidationError("report is missing fields: " + ", ".join(missing))
    extras = sorted(payload.keys() - required)
    if extras:
        raise ReportValidationError("report has unsupported fields: " + ", ".join(extras))
    if not isinstance(payload["candidate_id"], str) or not payload["candidate_id"]:
        raise ReportValidationError("candidate_id must be a nonempty string")
    if not isinstance(payload["manifest"], str) or not payload["manifest"]:
        raise ReportValidationError("manifest must be a nonempty string")
    if not isinstance(payload["generated_at"], str) or not payload["generated_at"]:
        raise ReportValidationError("generated_at must be a nonempty string")
    functional = payload["functional"]
    if not isinstance(functional, dict) or functional.get("status") not in FUNCTIONAL_STATUSES:
        raise ReportValidationError("invalid functional result")
    allowed_functional = {
        "status",
        "commands",
        "returncodes",
        "stdout",
        "stderr",
        "tool_versions",
        "imported_from",
        "evidence",
    }
    if set(functional) - allowed_functional:
        raise ReportValidationError("functional result has unsupported fields")

    results = payload["oracle_results"]
    if not isinstance(results, list) or not results:
        raise ReportValidationError("oracle_results must be a nonempty array")
    ids: set[str] = set()
    for result in results:
        _validate_oracle_result(result)
        if result["oracle_id"] in ids:
            raise ReportValidationError("oracle result ids must be unique")
        ids.add(result["oracle_id"])
    if not any(result["contributes_to_gap"] for result in results):
        raise ReportValidationError("report requires at least one contributing oracle result")
    if not isinstance(payload["gap_member"], bool):
        raise ReportValidationError("gap_member must be boolean")
    expected_gap = functional["status"] == "pass" and any(
        result["contributes_to_gap"] and result["status"] == "fail"
        for result in results
    )
    if payload["gap_member"] != expected_gap:
        raise ReportValidationError("gap_member is inconsistent with oracle results")
    return payload


def _validate_oracle_result(result: Any) -> None:
    required = {
        "oracle_id",
        "oracle_class",
        "contributes_to_gap",
        "required",
        "status",
        "backend",
        "backend_version",
        "findings",
        "diagnostics",
        "tool_versions",
        "coverage",
    }
    if not isinstance(result, dict) or set(result) != required:
        raise ReportValidationError("oracle result fields do not match schema v2")
    if result["status"] not in STRUCTURAL_STATUSES:
        raise ReportValidationError("invalid oracle result status")
    if not isinstance(result["oracle_id"], str) or re.fullmatch(
        r"[a-z][a-z0-9_.-]*", result["oracle_id"]
    ) is None:
        raise ReportValidationError("invalid oracle_id")
    if not isinstance(result["oracle_class"], str) or re.fullmatch(
        r"[a-z][a-z0-9_.-]*", result["oracle_class"]
    ) is None:
        raise ReportValidationError("invalid oracle_class")
    if not isinstance(result["contributes_to_gap"], bool) or not isinstance(
        result["required"], bool
    ):
        raise ReportValidationError("oracle result flags must be booleans")
    if not isinstance(result["findings"], list):
        raise ReportValidationError("oracle findings must be an array")
    if not isinstance(result["backend"], str) or not result["backend"]:
        raise ReportValidationError("oracle backend must be a nonempty string")
    if not isinstance(result["backend_version"], str) or not result["backend_version"]:
        raise ReportValidationError("oracle backend_version must be a nonempty string")
    for finding in result["findings"]:
        if not isinstance(finding, dict) or set(finding) != {
            "rule_id",
            "severity",
            "message",
            "evidence",
        }:
            raise ReportValidationError("invalid oracle finding fields")
        if finding["severity"] not in {"error", "warning", "info"}:
            raise ReportValidationError("invalid finding severity")
        if not isinstance(finding["rule_id"], str) or re.fullmatch(
            r"[A-Z0-9][A-Z0-9_.-]*", finding["rule_id"]
        ) is None:
            raise ReportValidationError("invalid finding rule_id")
        if not isinstance(finding["message"], str) or not finding["message"]:
            raise ReportValidationError("finding message must be a nonempty string")
        if not isinstance(finding["evidence"], dict):
            raise ReportValidationError("finding evidence must be an object")
    if not isinstance(result["diagnostics"], list) or not isinstance(
        result["tool_versions"], dict
    ):
        raise ReportValidationError("invalid oracle diagnostics or tool versions")
    if not all(isinstance(item, str) for item in result["diagnostics"]):
        raise ReportValidationError("oracle diagnostics must contain strings")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in result["tool_versions"].items()
    ):
        raise ReportValidationError("oracle tool versions must contain strings")
    if not isinstance(result["coverage"], dict):
        raise ReportValidationError("oracle coverage must be an object")


def oracle_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a uniform oracle-result list for a validated v1 or v2 report."""

    validated = validate_report_payload(payload)
    if validated["schema_version"] == "2.0":
        return list(validated["oracle_results"])
    structural = dict(validated["structural"])
    structural.update(
        {
            "oracle_id": "structural",
            "oracle_class": "structural",
            "contributes_to_gap": True,
            "required": True,
            "coverage": {},
        }
    )
    return [structural]


def primary_structural_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the first structural oracle in a validated v1 or v2 report."""
    result = next(
        (
            item
            for item in oracle_results(payload)
            if item["oracle_class"] == "structural"
        ),
        None,
    )
    if result is None:
        raise ReportValidationError("report does not contain a structural oracle result")
    return result


def contributing_oracle_status(payload: dict[str, Any]) -> str:
    """Collapse contributing oracle results without hiding uncertainty."""
    results = [item for item in oracle_results(payload) if item["contributes_to_gap"]]
    statuses = {item["status"] for item in results}
    if "fail" in statuses:
        return "fail"
    if "tool_error" in statuses:
        return "tool_error"
    if "unknown" in statuses or not statuses:
        return "unknown"
    return "pass"
