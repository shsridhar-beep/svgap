import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.study import summarize_reports


class StudyTests(TestCase):
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
