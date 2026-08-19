import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.study import summarize_reports


class StudyTests(TestCase):
    def test_v2_noncontributing_lint_does_not_change_gap_summary(self) -> None:
        def oracle(
            oracle_id: str,
            oracle_class: str,
            status: str,
            contributes: bool,
            rule_id: str | None = None,
        ) -> dict:
            findings = (
                [
                    {
                        "rule_id": rule_id,
                        "severity": "error",
                        "message": "fixture",
                        "evidence": {},
                    }
                ]
                if rule_id
                else []
            )
            return {
                "oracle_id": oracle_id,
                "oracle_class": oracle_class,
                "contributes_to_gap": contributes,
                "required": True,
                "status": status,
                "backend": oracle_id,
                "backend_version": "1",
                "findings": findings,
                "diagnostics": [],
                "tool_versions": {},
                "coverage": {},
            }

        with TemporaryDirectory() as directory:
            path = Path(directory) / "model--sample-01" / "task" / "report.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0",
                        "candidate_id": "task",
                        "manifest": "manifest.toml",
                        "functional": {"status": "pass"},
                        "oracle_results": [
                            oracle("structure", "structural", "pass", True),
                            oracle("lint", "lint", "fail", False, "LINT-TEST"),
                        ],
                        "gap_member": False,
                        "generated_at": "2026-08-19T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            summary = summarize_reports([path])
        self.assertEqual(summary["structurally_determinate_functional_pass"], 1)
        self.assertEqual(summary["gap_members"], 0)
        self.assertNotIn("LINT-TEST", summary["rules"])

    def test_gap_denominator_excludes_tool_errors(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, (functional, structural) in enumerate(
                (("pass", "pass"), ("pass", "fail"), ("pass", "tool_error"))
            ):
                path = root / f"model--sample-0{index + 1}" / "task" / "report.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": "1.0",
                            "candidate_id": "task",
                            "manifest": "manifest.toml",
                            "functional": {"status": functional},
                            "structural": {
                                "status": structural,
                                "backend": "test",
                                "backend_version": "1",
                                "findings": [],
                                "diagnostics": [],
                                "tool_versions": {},
                            },
                            "gap_member": functional == "pass" and structural == "fail",
                            "generated_at": "2026-07-02T00:00:00+00:00",
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
            summary = summarize_reports(paths)
        self.assertEqual(summary["functional_pass"], 3)
        self.assertEqual(summary["structurally_determinate_functional_pass"], 2)
        self.assertEqual(summary["gap_members"], 1)
        self.assertEqual(summary["detected_gap_fraction"], 0.5)
