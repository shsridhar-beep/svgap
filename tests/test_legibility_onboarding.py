from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.cli import main
from svgap.legibility import explain_payload
from svgap.manifest import load_manifest
from svgap.onboarding import manifest_readiness


ROOT = Path(__file__).resolve().parents[1]


class LegibilityAndOnboardingTests(TestCase):
    def test_explanation_separates_failed_and_unanswered_questions(self) -> None:
        report_path = ROOT / "challenges/v0.1/repair/before-report.json"
        explanation = explain_payload(json.loads(report_path.read_text(encoding="utf-8")))
        self.assertTrue(explanation["answered"])
        self.assertTrue(explanation["failed"])
        self.assertIn("not silicon signoff", explanation["claim_boundary"])

    def test_mock_adjudication_explanation_preserves_claim_boundary(self) -> None:
        report = {
            "candidate_id": "fixture",
            "verdict": "no_divergence_observed",
            "semantics": {"name": "fixture", "version": "1"},
            "instrumenter": {"name": "fixture", "version": "1", "mode": "mock_prerecorded"},
            "seed_budget": 1,
            "seeds_completed": 1,
            "calibration": {"status": "pass", "suite_digest": "sha256:fixture"},
        }
        explanation = explain_payload(report)
        self.assertTrue(any("cannot support" in item for item in explanation["next_evidence"]))

    def test_init_refuses_to_infer_intent_and_validate_marks_incomplete(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "design.sv"
            source.write_text("module top(input logic clk); endmodule\n", encoding="utf-8")
            manifest_path = root / "manifest.toml"
            self.assertEqual(
                main(
                    [
                        "init",
                        str(source),
                        "--top",
                        "top",
                        "--candidate-id",
                        "fixture",
                        "--output",
                        str(manifest_path),
                    ]
                ),
                0,
            )
            draft = manifest_path.read_text(encoding="utf-8")
            self.assertIn("intent is deliberately not inferred", draft)
            self.assertEqual(manifest_readiness(load_manifest(manifest_path))["status"], "incomplete")
            self.assertEqual(main(["validate", str(manifest_path)]), 3)

    def test_explain_cli_returns_failure_for_failed_evidence(self) -> None:
        self.assertEqual(
            main(
                [
                    "explain",
                    str(ROOT / "challenges/v0.1/repair/before-report.json"),
                    "--json",
                ]
            ),
            1,
        )
