import json
from unittest import TestCase

from svgap.reporting import build_html, build_sarif, dumps_sarif


class ReportingTests(TestCase):
    def setUp(self) -> None:
        self.report = {
            "schema_version": "1.0",
            "candidate_id": "candidate-1",
            "manifest": "manifest.toml",
            "functional": {"status": "pass"},
            "structural": {
                "status": "fail",
                "backend": "test",
                "backend_version": "1",
                "findings": [
                    {
                        "rule_id": "TEST-001",
                        "severity": "error",
                        "message": "unsafe <script>alert(1)</script>",
                        "evidence": {"source_location": "design.sv:12.4-15.1"},
                    }
                ],
                "diagnostics": [],
                "tool_versions": {},
            },
            "gap_member": True,
            "generated_at": "2026-07-02T00:00:00+00:00",
        }

    def test_sarif_contains_rule_and_location(self) -> None:
        sarif = build_sarif([self.report])
        result = sarif["runs"][0]["results"][0]
        self.assertEqual(result["ruleId"], "TEST-001")
        region = result["locations"][0]["physicalLocation"]["region"]
        self.assertEqual(region, {"startLine": 12, "startColumn": 4})
        self.assertEqual(json.loads(dumps_sarif([self.report])), sarif)

    def test_html_escapes_untrusted_evidence(self) -> None:
        output = build_html([self.report])
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("candidate-1", output)
