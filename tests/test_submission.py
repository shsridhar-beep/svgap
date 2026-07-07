import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.submission import (
    SubmissionError,
    bundle_submission,
    initialize_submission,
    initialize_submission_from_harbor,
    validate_submission,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "challenges/v0.1/generation/report.json"
DIAGNOSIS_RESULT = ROOT / "results/baselines/v0.1/diagnosis/gpt-5.4/result.json"


class SubmissionTests(TestCase):
    def initialize(self, root: Path, **overrides: object) -> Path:
        values = {
            "submission_id": "example-generation-01",
            "title": "Example generation profile",
            "track": "generation",
            "configuration_label": "frontier-lab-a",
            "provenance_level": "attested_alias",
            "taskpack_id": "frontier-model-handoff-v0.1",
            "taskpack_version": "0.1",
            "contributor": "Example Researcher",
            "attestor": "Example Researcher",
            "attestation": "Exact configuration retained privately by the submitter.",
        }
        values.update(overrides)
        output = root / "submission"
        initialize_submission([REPORT], output, **values)
        return output

    def test_initialize_validate_and_bundle(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            submission = self.initialize(root)
            manifest, artifacts = validate_submission(submission)
            self.assertEqual(manifest["configuration"]["provenance_level"], "attested_alias")
            self.assertEqual(len(artifacts), 2)
            first = bundle_submission(submission, root / "submission-1.tar.gz")
            second = bundle_submission(submission, root / "submission-2.tar.gz")
            self.assertEqual(first, second)
            self.assertEqual(
                (root / "submission-1.tar.gz").read_bytes(),
                (root / "submission-2.tar.gz").read_bytes(),
            )

    def test_public_provenance_requires_model_id(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(SubmissionError):
                self.initialize(
                    Path(directory),
                    provenance_level="public",
                    attestor=None,
                    attestation=None,
                )

    def test_digest_tampering_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            submission = self.initialize(Path(directory))
            summary = submission / "summary.json"
            summary.write_text(summary.read_text() + " ", encoding="utf-8")
            with self.assertRaisesRegex(SubmissionError, "digest mismatch"):
                validate_submission(submission)

    def test_private_denylist_blocks_withheld_identifier(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            submission = self.initialize(root)
            report = next((submission / "evidence").glob("*.json"))
            payload = json.loads(report.read_text())
            payload["functional"]["stdout"] = "PRIVATE-CHECKPOINT-123"
            report.write_text(json.dumps(payload), encoding="utf-8")
            manifest_path = submission / "submission.json"
            manifest = json.loads(manifest_path.read_text())
            import hashlib

            relative = report.relative_to(submission).as_posix()
            manifest["digests"][relative] = hashlib.sha256(report.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            denylist = root / "denylist.txt"
            denylist.write_text("PRIVATE-CHECKPOINT-[0-9]+\n", encoding="utf-8")
            with self.assertRaisesRegex(SubmissionError, "private denylist"):
                validate_submission(submission, denylist=denylist)

    def test_diagnosis_result_is_preserved_as_challenge_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "diagnosis"
            initialize_submission(
                [DIAGNOSIS_RESULT],
                output,
                submission_id="example-diagnosis-01",
                title="Example diagnosis profile",
                track="diagnosis",
                configuration_label="gpt-5.4",
                provenance_level="public",
                model_id="gpt-5.4",
                taskpack_id="frontier-model-handoff-v0.1",
                taskpack_version="0.1",
                contributor="Example Researcher",
            )
            validate_submission(output)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["kind"], "challenge_results")
            self.assertEqual(summary["result_count"], 1)
            self.assertEqual(summary["overall_statuses"], {"fail": 1, "pass": 0})

    def test_challenge_result_must_match_configuration_label(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SubmissionError, "configuration label"):
                initialize_submission(
                    [DIAGNOSIS_RESULT],
                    Path(directory) / "diagnosis",
                    submission_id="example-diagnosis-01",
                    title="Example diagnosis profile",
                    track="diagnosis",
                    configuration_label="different-model",
                    provenance_level="public",
                    model_id="different-model",
                    taskpack_id="frontier-model-handoff-v0.1",
                    taskpack_version="0.1",
                    contributor="Example Researcher",
                )

    def test_from_harbor_validates_and_initializes_submission(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job, dataset = self.harbor_fixture(root)
            output = root / "submission"
            manifest = initialize_submission_from_harbor(
                job,
                dataset,
                output,
                submission_id="harbor-generation-01",
                title="Harbor generation profile",
                provenance_level="public",
                contributor="Example Researcher",
                provider="openai",
            )
            validate_submission(output)
            self.assertEqual(manifest["source"]["kind"], "harbor_job")
            self.assertEqual(manifest["source"]["agent"], "codex")
            self.assertEqual(manifest["configuration"]["model_id"], "gpt-test")

    def test_from_harbor_rejects_reward_disagreement(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job, dataset = self.harbor_fixture(root)
            result_path = next(job.glob("trial-*/result.json"))
            result = json.loads(result_path.read_text())
            result["verifier_result"]["rewards"]["structural_accept"] = 0
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(SubmissionError, "reward/report mismatch"):
                initialize_submission_from_harbor(
                    job,
                    dataset,
                    root / "submission",
                    submission_id="harbor-generation-01",
                    title="Harbor generation profile",
                    provenance_level="public",
                    contributor="Example Researcher",
                )

    def test_from_harbor_rejects_unpinned_task_image(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job, dataset = self.harbor_fixture(root)
            dockerfile = dataset / "example" / "environment" / "Dockerfile"
            dockerfile.write_text("FROM example.invalid/svgap:latest\n")
            with self.assertRaisesRegex(SubmissionError, "evaluator image mismatch"):
                initialize_submission_from_harbor(
                    job,
                    dataset,
                    root / "submission",
                    submission_id="harbor-generation-01",
                    title="Harbor generation profile",
                    provenance_level="public",
                    contributor="Example Researcher",
                )

    def test_from_harbor_rejects_oracle_as_model_submission(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job, dataset = self.harbor_fixture(root)
            result_path = next(job.glob("trial-*/result.json"))
            result = json.loads(result_path.read_text())
            result["agent_info"]["name"] = "oracle"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(SubmissionError, "Oracle jobs"):
                initialize_submission_from_harbor(
                    job,
                    dataset,
                    root / "submission",
                    submission_id="harbor-generation-01",
                    title="Harbor generation profile",
                    provenance_level="public",
                    contributor="Example Researcher",
                )

    def test_from_harbor_accepts_pinned_public_dataset_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job = self.harbor_public_job_fixture(root)
            output = root / "submission"
            manifest = initialize_submission_from_harbor(
                job,
                "svgap/svgap-reset-release@0.2",
                output,
                submission_id="harbor-public-generation-01",
                title="Harbor public generation profile",
                provenance_level="public",
                contributor="Example Researcher",
            )
            validate_submission(output)
            self.assertEqual(
                manifest["source"]["dataset"], "svgap/svgap-reset-release"
            )
            self.assertEqual(len(manifest["source"]["task_digests"]), 8)
            self.assertEqual(len(manifest["artifacts"]["evidence"]), 8)

    def test_from_harbor_public_reference_rejects_task_drift(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job = self.harbor_public_job_fixture(root)
            lock_path = next(job.glob("trial-*/lock.json"))
            lock = json.loads(lock_path.read_text())
            lock["task"]["digest"] = "sha256:" + "f" * 64
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaisesRegex(SubmissionError, "task digest mismatch"):
                initialize_submission_from_harbor(
                    job,
                    "svgap/svgap-reset-release@0.2",
                    root / "submission",
                    submission_id="harbor-public-generation-01",
                    title="Harbor public generation profile",
                    provenance_level="public",
                    contributor="Example Researcher",
                )

    def test_from_harbor_rejects_unpinned_public_dataset_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            job = root / "job"
            job.mkdir()
            (job / "result.json").write_text(json.dumps({"id": "job-1"}))
            with self.assertRaisesRegex(SubmissionError, "pinned published"):
                initialize_submission_from_harbor(
                    job,
                    "svgap/svgap-reset-release",
                    root / "submission",
                    submission_id="harbor-public-generation-01",
                    title="Harbor public generation profile",
                    provenance_level="public",
                    contributor="Example Researcher",
                )

    def harbor_fixture(self, root: Path) -> tuple[Path, Path]:
        digest = "sha256:" + "a" * 64
        image = "example.invalid/svgap@sha256:" + "b" * 64
        dataset = root / "dataset"
        task = dataset / "example"
        (task / "environment").mkdir(parents=True)
        (task / "task.toml").write_text(
            'schema_version = "1.3"\n'
            '[task]\nname = "svgap/example"\n'
            '[metadata]\nsource_taskpack = "reset-replication-v0.2"\n'
            'svgap_version = "0.3.0a6"\n',
            encoding="utf-8",
        )
        (task / "environment" / "Dockerfile").write_text(
            f"FROM {image}\n", encoding="utf-8"
        )
        (dataset / "dataset.toml").write_text(
            '[dataset]\nname = "svgap/test"\n'
            f'[[tasks]]\nname = "svgap/example"\ndigest = "{digest}"\n',
            encoding="utf-8",
        )
        (dataset / "provenance.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "dataset": "svgap/test",
                    "source_taskpack": {
                        "id": "reset-replication",
                        "version": "0.2",
                        "canonical_digest": "sha256:" + "c" * 64,
                    },
                    "svgap_version": "0.3.0a6",
                    "release_tag": "v0.3.0-alpha.6",
                    "evaluator_image": image,
                }
            ),
            encoding="utf-8",
        )

        job = root / "job"
        job.mkdir()
        (job / "result.json").write_text(json.dumps({"id": "job-1"}))
        self.write_harbor_trial(job, "svgap/example", digest, "example")
        return job, dataset

    def harbor_public_job_fixture(self, root: Path) -> Path:
        profile = json.loads(
            (ROOT / "src/svgap/harbor_profiles/svgap-reset-release-0.2.json")
            .read_text(encoding="utf-8")
        )
        job = root / "job"
        job.mkdir()
        (job / "result.json").write_text(json.dumps({"id": "job-public-1"}))
        for index, task in enumerate(profile["tasks"], start=1):
            self.write_harbor_trial(
                job, task["name"], task["digest"], f"{index:02d}"
            )
        return job

    def write_harbor_trial(
        self, job: Path, task_name: str, digest: str, suffix: str
    ) -> None:
        trial = job / f"trial-{suffix}"
        artifacts = trial / "artifacts" / "logs" / "artifacts"
        artifacts.mkdir(parents=True)
        (trial / "lock.json").write_text(
            json.dumps({"task": {"digest": digest}}), encoding="utf-8"
        )
        rewards = {
            "reward": 1,
            "functional_accept": 1,
            "structural_accept": 1,
            "gap_member": 0,
            "unknown": 0,
            "tool_error": 0,
        }
        (trial / "result.json").write_text(
            json.dumps(
                {
                    "task_name": task_name,
                    "exception_info": None,
                    "agent_info": {
                        "name": "codex",
                        "model_info": {"name": "gpt-test"},
                    },
                    "verifier_result": {"rewards": rewards},
                }
            ),
            encoding="utf-8",
        )
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        (artifacts / "svgap-report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        (artifacts / "harbor-verdict.json").write_text(
            json.dumps(
                {
                    "functional_status": "pass",
                    "structural_status": "pass",
                    "gap_member": False,
                    "unknown": False,
                    "tool_error": False,
                    "primary_reward": 1,
                }
            ),
            encoding="utf-8",
        )
