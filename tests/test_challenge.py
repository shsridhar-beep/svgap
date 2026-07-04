from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.challenge import ChallengeError, score_challenge


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "challenges/v0.1"


class ChallengeTests(TestCase):
    def test_example_profiles_pass(self) -> None:
        for track in ("generation", "diagnosis", "repair"):
            with self.subTest(track=track):
                result = score_challenge(
                    PACK / track / "task.json",
                    PACK / track / "example-submission.json",
                )
                self.assertEqual(result["track"], track)
                self.assertEqual(result["overall"], "pass")
                self.assertTrue(all(item["pass"] for item in result["profile"]))

    def test_diagnosis_requires_exact_question_set(self) -> None:
        with TemporaryDirectory() as directory:
            submission = json.loads(
                (PACK / "diagnosis/example-submission.json").read_text(encoding="utf-8")
            )
            submission["responses"].pop()
            path = Path(directory) / "submission.json"
            path.write_text(json.dumps(submission), encoding="utf-8")
            with self.assertRaisesRegex(ChallengeError, "exactly"):
                score_challenge(PACK / "diagnosis/task.json", path)

    def test_artifacts_cannot_escape_submission_directory(self) -> None:
        with TemporaryDirectory() as directory:
            submission = json.loads(
                (PACK / "generation/example-submission.json").read_text(encoding="utf-8")
            )
            submission["artifacts"]["report"] = "../report.json"
            path = Path(directory) / "submission.json"
            path.write_text(json.dumps(submission), encoding="utf-8")
            with self.assertRaisesRegex(ChallengeError, "remain inside"):
                score_challenge(PACK / "generation/task.json", path)

    def test_generation_profile_exposes_structural_failure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            submission = json.loads(
                (PACK / "generation/example-submission.json").read_text(encoding="utf-8")
            )
            report = json.loads(
                (PACK / "repair/before-report.json").read_text(encoding="utf-8")
            )
            (root / "submission.json").write_text(json.dumps(submission), encoding="utf-8")
            (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
            result = score_challenge(
                PACK / "generation/task.json", root / "submission.json"
            )
            checks = {item["check"]: item["pass"] for item in result["profile"]}
            self.assertFalse(checks["structural_pass"])
            self.assertTrue(checks["structural_determinate"])
            self.assertEqual(result["overall"], "fail")

    def test_repair_profile_rejects_candidate_substitution(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("example-submission.json", "before-report.json", "after-report.json"):
                (root / name).write_text(
                    (PACK / "repair" / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            after = json.loads((root / "after-report.json").read_text(encoding="utf-8"))
            after["candidate_id"] = "substituted-candidate"
            (root / "after-report.json").write_text(json.dumps(after), encoding="utf-8")
            result = score_challenge(PACK / "repair/task.json", root / "example-submission.json")
            checks = {item["check"]: item["pass"] for item in result["profile"]}
            self.assertFalse(checks["same_candidate_id"])
            self.assertEqual(result["overall"], "fail")
