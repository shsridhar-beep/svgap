from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
from unittest import TestCase, skipUnless

from jsonschema import Draft202012Validator, FormatChecker

from svgap.cli import check


ROOT = Path(__file__).resolve().parents[1]
HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class SchemaTests(TestCase):
    def test_all_controlled_reports_validate(self) -> None:
        schema = json.loads((ROOT / "schemas/report-v1.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifests = sorted(ROOT.glob("examples/*/*/manifest.toml"))
        self.assertEqual(len(manifests), 10)
        for path in manifests:
            with self.subTest(manifest=path):
                with redirect_stdout(io.StringIO()):
                    exit_code = check(path, False, False)
                self.assertIn(exit_code, (0, 1))
        reports = sorted(ROOT.glob("examples/*/*/build/report.json"))
        self.assertEqual(len(reports), 10)
        for path in reports:
            with self.subTest(path=path):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_all_public_artifact_reports_validate(self) -> None:
        schema = json.loads((ROOT / "schemas/report-v1.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        reports = sorted(
            ROOT.glob("artifacts/reset-replication-v0.1/candidates/*/*/report.json")
        )
        self.assertEqual(len(reports), 72)
        for path in reports:
            with self.subTest(path=path):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_report_schema_rejects_unknown_top_level_fields(self) -> None:
        schema = json.loads((ROOT / "schemas/report-v1.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        report_path = next(
            ROOT.glob("artifacts/reset-replication-v0.1/candidates/*/*/report.json")
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["silent_extension"] = True
        self.assertTrue(list(validator.iter_errors(report)))


class ContractSchemaTests(TestCase):
    def test_public_submission_contract_validates_initialized_submission(self) -> None:
        schema = json.loads((ROOT / "schemas/submission-v1.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifests = sorted(ROOT.glob("results/submissions/*/submission.json"))
        self.assertGreaterEqual(len(manifests), 1)
        for path in manifests:
            with self.subTest(path=path):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_adjudication_fixture_contracts_validate(self) -> None:
        trace_schema = json.loads((ROOT / "schemas/trace-v1.json").read_text())
        trace_validator = Draft202012Validator(trace_schema)
        for path in sorted((ROOT / "examples/adjudication_calibration").glob("*.json")):
            if path.name != "suite.json":
                trace_validator.validate(json.loads(path.read_text(encoding="utf-8")))
        suite_schema = json.loads((ROOT / "schemas/calibration-suite-v1.json").read_text())
        Draft202012Validator(suite_schema).validate(
            json.loads((ROOT / "examples/adjudication_calibration/suite.json").read_text())
        )

    def test_frontier_challenge_contracts_validate(self) -> None:
        task_schema = json.loads((ROOT / "schemas/challenge-task-v1.json").read_text())
        submission_schema = json.loads(
            (ROOT / "schemas/challenge-submission-v1.json").read_text()
        )
        task_validator = Draft202012Validator(task_schema)
        submission_validator = Draft202012Validator(submission_schema)
        for track in ("generation", "diagnosis", "repair"):
            task_validator.validate(
                json.loads((ROOT / f"challenges/v0.1/{track}/task.json").read_text())
            )
            submission_validator.validate(
                json.loads(
                    (ROOT / f"challenges/v0.1/{track}/example-submission.json").read_text()
                )
            )
