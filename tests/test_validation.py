from unittest import TestCase

from svgap.validation import ReportValidationError, validate_report_payload


class ValidationTests(TestCase):
    def test_v2_gap_uses_only_contributing_oracles(self) -> None:
        report = {
            "schema_version": "2.0",
            "candidate_id": "candidate",
            "manifest": "manifest.toml",
            "functional": {"status": "pass"},
            "oracle_results": [
                {
                    "oracle_id": "structure",
                    "oracle_class": "structural",
                    "contributes_to_gap": True,
                    "required": True,
                    "status": "pass",
                    "backend": "test-structure",
                    "backend_version": "1",
                    "findings": [],
                    "diagnostics": [],
                    "tool_versions": {},
                    "coverage": {},
                },
                {
                    "oracle_id": "lint",
                    "oracle_class": "lint",
                    "contributes_to_gap": False,
                    "required": False,
                    "status": "fail",
                    "backend": "test-lint",
                    "backend_version": "1",
                    "findings": [],
                    "diagnostics": [],
                    "tool_versions": {},
                    "coverage": {},
                },
            ],
            "gap_member": False,
            "generated_at": "2026-08-19T00:00:00Z",
        }
        self.assertIs(validate_report_payload(report), report)

    def test_v2_duplicate_oracle_ids_are_rejected(self) -> None:
        oracle = {
            "oracle_id": "duplicate",
            "oracle_class": "structural",
            "contributes_to_gap": True,
            "required": True,
            "status": "pass",
            "backend": "test",
            "backend_version": "1",
            "findings": [],
            "diagnostics": [],
            "tool_versions": {},
            "coverage": {},
        }
        report = {
            "schema_version": "2.0",
            "candidate_id": "candidate",
            "manifest": "manifest.toml",
            "functional": {"status": "pass"},
            "oracle_results": [dict(oracle), dict(oracle)],
            "gap_member": False,
            "generated_at": "2026-08-19T00:00:00Z",
        }
        with self.assertRaisesRegex(ReportValidationError, "unique"):
            validate_report_payload(report)

    def test_inconsistent_gap_membership_is_rejected(self) -> None:
        report = {
            "schema_version": "1.0",
            "candidate_id": "candidate",
            "manifest": "manifest.toml",
            "functional": {"status": "pass"},
            "structural": {
                "status": "fail",
                "backend": "test",
                "backend_version": "1",
                "findings": [],
                "diagnostics": [],
                "tool_versions": {},
            },
            "gap_member": False,
            "generated_at": "2026-07-04T00:00:00Z",
        }
        with self.assertRaisesRegex(ReportValidationError, "inconsistent"):
            validate_report_payload(report)

    def test_unknown_extension_is_rejected(self) -> None:
        report = {
            "schema_version": "1.0",
            "candidate_id": "candidate",
            "manifest": "manifest.toml",
            "functional": {"status": "pass"},
            "structural": {
                "status": "pass",
                "backend": "test",
                "backend_version": "1",
                "findings": [],
                "diagnostics": [],
                "tool_versions": {},
            },
            "gap_member": False,
            "generated_at": "2026-07-04T00:00:00Z",
            "extension": True,
        }
        with self.assertRaisesRegex(ReportValidationError, "unsupported"):
            validate_report_payload(report)
