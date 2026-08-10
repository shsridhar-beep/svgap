import importlib.util
import json
from pathlib import Path
from unittest import TestCase

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = ROOT / "scripts" / "build_adoption_baseline.py"
    spec = importlib.util.spec_from_file_location("build_adoption_baseline", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ResultRegistryTests(TestCase):
    def test_registry_is_deterministic_and_current(self) -> None:
        module = _load_builder()
        first = module.build_registry()
        second = module.build_registry()
        self.assertEqual(first, second)
        self.assertIn("submissions", first)
        self.assertEqual(
            sum(item["candidate_reports"] for item in first["generation"]), 72
        )
        self.assertEqual(
            {item["overall"] for item in first["diagnosis"]}, {"pass", "fail"}
        )
        self.assertEqual(
            {item["overall"] for item in first["repair"]}, {"pass", "fail"}
        )


def _minimal_challenge_entry() -> dict:
    return {
        "model": "example-model",
        "run_id": "2026-01-01-01",
        "overall": "pass",
        "profile": [{"check": "example-check", "evidence": "present", "pass": True}],
        "result": "results/example/result.json",
        "submission": "results/example/submission.json",
        "provenance": "results/example/provenance.json",
        "provider": "Example",
    }


def _minimal_generation_entry() -> dict:
    return {
        "model": "example-model",
        "candidate_reports": 1,
        "functional_statuses": {"pass": 1},
        "structural_statuses": {"pass": 1},
        "functional_pass_structural_fail": 0,
        "finding_counts": {},
        "source": "artifacts/example/candidates",
    }


def _minimal_submission_entry() -> dict:
    return {
        "submission_id": "example-submission-01",
        "title": "Example submission",
        "track": "generation",
        "configuration": {"model_id": "example-model"},
        "taskpack": {},
        "contributor": "Example Contributor",
        "created_at": "2026-01-01T00:00:00+00:00",
        "claim_boundary": "Example claim boundary.",
        "summary": {},
        "source": "results/submissions/example-submission-01",
    }


def _minimal_registry() -> dict:
    return {
        "schema_version": "1.0",
        "registry_id": "example-registry",
        "generated_from": "artifacts/example",
        "claim_boundary": "Example claim boundary.",
        "generation": [_minimal_generation_entry()],
        "diagnosis": [_minimal_challenge_entry()],
        "repair": [_minimal_challenge_entry()],
        "submissions": [_minimal_submission_entry()],
    }


class ResultRegistrySchemaFixtureTests(TestCase):
    # Small in-memory documents, independent of results/registry-v1.json,
    # so each failure mode is isolated from production data.
    @classmethod
    def setUpClass(cls) -> None:
        schema = json.loads((ROOT / "schemas/result-registry-v1.json").read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def test_valid_minimal_entry_passes(self) -> None:
        self.validator.validate(_minimal_registry())

    def test_challenge_entry_missing_provenance_fails(self) -> None:
        registry = _minimal_registry()
        del registry["diagnosis"][0]["provenance"]
        with self.assertRaises(ValidationError):
            self.validator.validate(registry)

    def test_challenge_entry_rejects_unsupported_overall_status(self) -> None:
        registry = _minimal_registry()
        registry["repair"][0]["overall"] = "inconclusive"
        with self.assertRaises(ValidationError):
            self.validator.validate(registry)

    def test_generation_entry_missing_source_fails(self) -> None:
        registry = _minimal_registry()
        del registry["generation"][0]["source"]
        with self.assertRaises(ValidationError):
            self.validator.validate(registry)
