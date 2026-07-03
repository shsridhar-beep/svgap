import json
from pathlib import Path
from unittest import TestCase

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(TestCase):
    def test_all_controlled_reports_validate(self) -> None:
        schema = json.loads((ROOT / "schemas/report-v1.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        reports = sorted(ROOT.glob("examples/*/*/build/report.json"))
        self.assertEqual(len(reports), 8)
        for path in reports:
            with self.subTest(path=path):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))
