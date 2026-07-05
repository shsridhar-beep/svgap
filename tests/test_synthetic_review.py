from unittest import TestCase

from scripts.run_synthetic_review import (
    codex_effort,
    normalize_result,
    parse_line_numbers,
)
from scripts.analyze_synthetic_review import krippendorff_alpha_nominal
from scripts.export_public_artifacts import make_portable_report


class SyntheticReviewTests(TestCase):
    def test_codex_effort_accounts_for_gpt_55_interface(self) -> None:
        self.assertEqual(codex_effort("gpt-5.5"), "xhigh")
        self.assertEqual(codex_effort("openai-frontier-b"), "max")

    def test_parse_line_numbers_expands_short_ranges(self) -> None:
        self.assertEqual(
            parse_line_numbers(["lines 3–5", 9, {"line": "12"}]),
            [3, 4, 5, 9, 12],
        )
        self.assertEqual(parse_line_numbers([0, "0-2", 4]), [4])

    def test_normalize_provider_aliases_to_locked_schema(self) -> None:
        result = normalize_result(
            {
                "verdict": "YES — raw reset reaches the counter",
                "key_lines": ["16-18", 22],
                "justification": "The operational count register uses arst_n.",
                "primary_elements": "count",
                "confidence": "HIGH",
                "unexpected_provider_field": "discarded",
            }
        )

        self.assertEqual(
            result,
            {
                "decision": "yes",
                "confidence": "high",
                "raw_reset_signal": "",
                "operational_state": ["count"],
                "reset_synchronizer_state": [],
                "evidence_lines": [16, 17, 18, 22],
                "reasoning_summary": "The operational count register uses arst_n.",
            },
        )

    def test_nominal_alpha_extremes(self) -> None:
        self.assertEqual(
            krippendorff_alpha_nominal([["yes", "yes"], ["no", "no"]]),
            1.0,
        )
        self.assertLess(
            krippendorff_alpha_nominal([["yes", "no"], ["yes", "no"]]),
            0.0,
        )

    def test_exported_report_has_stable_portable_identity(self) -> None:
        portable = make_portable_report(
            {
                "manifest": "/machine/local/run/manifest.toml",
                "generated_at": "new",
                "functional": {"status": "pass"},
            },
            {"generated_at": "frozen"},
        )
        self.assertEqual(portable["manifest"], "manifest.toml")
        self.assertEqual(portable["generated_at"], "frozen")
