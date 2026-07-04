from unittest import TestCase

from svgap.validation import ReportValidationError, validate_report_payload


class ValidationTests(TestCase):
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
