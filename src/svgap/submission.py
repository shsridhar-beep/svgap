from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
import shutil
import tarfile
import tomllib
from typing import Any, Iterable

from svgap.study import summarize_reports
from svgap.validation import ReportValidationError, validate_report_payload


class SubmissionError(ValueError):
    pass


PROVENANCE_LEVELS = {"public", "attested_alias", "anonymous_case_study"}
TRACKS = {"generation", "diagnosis", "repair"}
CLAIM_BOUNDARY = (
    "This profile describes submitted digital RTL evidence under configured "
    "functional and structural checks. It is not silicon signoff, a population "
    "estimate, or a general model ranking."
)

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_BUILTIN_DENY_PATTERNS = (
    ("credential-like token", re.compile(r"(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}")),
    (
        "credential assignment",
        re.compile(
            r"(?i)(?:api[_-]?key|access[_-]?token|authorization)\s*[=:]\s*"
            r"[\"']?[A-Za-z0-9._-]{8,}"
        ),
    ),
    ("user home path", re.compile(r"/(?:Users|home)/[^/\s\"']+/")),
    (
        "internal endpoint",
        re.compile(
            r"(?i)https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+|"
            r"[^/\s]+\.(?:corp|internal))(?:[/:\s]|$)"
        ),
    ),
)


def initialize_submission(
    evidence_paths: Iterable[Path],
    output: Path,
    *,
    submission_id: str,
    title: str,
    track: str,
    configuration_label: str,
    provenance_level: str,
    taskpack_id: str,
    taskpack_version: str,
    contributor: str,
    provider: str | None = None,
    model_id: str | None = None,
    attestor: str | None = None,
    attestation: str | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_slug(submission_id, "submission_id")
    if track not in TRACKS:
        raise SubmissionError(f"unsupported track: {track}")
    if provenance_level not in PROVENANCE_LEVELS:
        raise SubmissionError(f"unsupported provenance level: {provenance_level}")
    _validate_provenance(
        provenance_level,
        model_id=model_id,
        attestor=attestor,
        attestation=attestation,
    )
    output = output.resolve()
    if output.exists():
        raise SubmissionError(f"refusing to overwrite submission directory: {output}")
    evidence = [Path(path).resolve() for path in evidence_paths]
    if not evidence:
        raise SubmissionError("at least one evidence file is required")
    validated: list[tuple[Path, dict[str, Any]]] = []
    for path in evidence:
        payload = _load_evidence(path, track, configuration_label)
        validated.append((path, payload))

    evidence_dir = output / "evidence"
    evidence_dir.mkdir(parents=True)
    copied: list[Path] = []
    for index, (evidence_source, payload) in enumerate(validated, start=1):
        identity = (
            payload["candidate_id"]
            if track == "generation"
            else f"{payload['task_id']}-{payload['run_id']}"
        )
        target = evidence_dir / f"{index:03d}-{_filename_slug(identity)}.json"
        shutil.copyfile(evidence_source, target)
        copied.append(target)

    summary = _summarize_evidence(track, copied)
    summary_path = output / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    relative_evidence = [path.relative_to(output).as_posix() for path in copied]
    artifacts = ["summary.json", *relative_evidence]
    configuration: dict[str, Any] = {
        "label": configuration_label,
        "provenance_level": provenance_level,
        "comparative_eligible": provenance_level != "anonymous_case_study",
    }
    if provider:
        configuration["provider"] = provider
    if model_id:
        configuration["model_id"] = model_id
    if provenance_level == "attested_alias":
        configuration["attestation"] = {
            "attestor": attestor,
            "statement": attestation,
            "private_mapping_retained": True,
        }
    manifest = {
        "schema_version": "1.0",
        "submission_id": submission_id,
        "title": title,
        "track": track,
        "configuration": configuration,
        "taskpack": {"id": taskpack_id, "version": taskpack_version},
        "contributor": contributor,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": CLAIM_BOUNDARY,
        "license": "Apache-2.0",
        "artifacts": {"summary": "summary.json", "evidence": relative_evidence},
        "digests": {relative: _sha256(output / relative) for relative in artifacts},
    }
    if source is not None:
        _validate_harbor_source(source)
        manifest["source"] = source
    (output / "submission.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def validate_submission(
    root: Path, *, denylist: Path | None = None
) -> tuple[dict[str, Any], list[str]]:
    root = root.resolve()
    try:
        manifest = json.loads((root / "submission.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"cannot read submission.json: {exc}") from exc
    required = {
        "schema_version",
        "submission_id",
        "title",
        "track",
        "configuration",
        "taskpack",
        "contributor",
        "created_at",
        "claim_boundary",
        "license",
        "artifacts",
        "digests",
    }
    allowed = required | {"source"}
    if not required.issubset(manifest) or not set(manifest).issubset(allowed):
        raise SubmissionError(
            "submission fields do not match schema: "
            f"missing={sorted(required - set(manifest))} "
            f"extra={sorted(set(manifest) - allowed)}"
        )
    if manifest["schema_version"] != "1.0":
        raise SubmissionError("unsupported submission schema_version")
    _validate_slug(manifest["submission_id"], "submission_id")
    if manifest["track"] not in TRACKS:
        raise SubmissionError("invalid submission track")
    configuration = manifest["configuration"]
    if not isinstance(configuration, dict):
        raise SubmissionError("configuration must be an object")
    level = configuration.get("provenance_level")
    if level not in PROVENANCE_LEVELS:
        raise SubmissionError("invalid provenance level")
    _validate_provenance(
        level,
        model_id=configuration.get("model_id"),
        attestor=(configuration.get("attestation") or {}).get("attestor"),
        attestation=(configuration.get("attestation") or {}).get("statement"),
    )
    expected_comparative = level != "anonymous_case_study"
    if configuration.get("comparative_eligible") is not expected_comparative:
        raise SubmissionError("comparative_eligible is inconsistent with provenance level")
    if "source" in manifest:
        _validate_harbor_source(manifest["source"])

    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != {"summary", "evidence"}:
        raise SubmissionError("artifacts must contain summary and evidence")
    relative_paths = [artifacts["summary"], *artifacts["evidence"]]
    if not artifacts["evidence"]:
        raise SubmissionError("submission must contain at least one evidence file")
    if set(manifest["digests"]) != set(relative_paths):
        raise SubmissionError("artifact digest set does not match artifact paths")
    evidence_paths: list[Path] = []
    for relative in relative_paths:
        path = _inside(root, relative)
        if not path.is_file():
            raise SubmissionError(f"missing artifact: {relative}")
        if _sha256(path) != manifest["digests"][relative]:
            raise SubmissionError(f"artifact digest mismatch: {relative}")
        if relative in artifacts["evidence"]:
            evidence_paths.append(path)
    try:
        for path in evidence_paths:
            _load_evidence(path, manifest["track"], configuration["label"])
        expected_summary = _summarize_evidence(manifest["track"], evidence_paths)
        actual_summary = json.loads(_inside(root, artifacts["summary"]).read_text())
    except (OSError, json.JSONDecodeError, ReportValidationError) as exc:
        raise SubmissionError(f"cannot validate submission evidence: {exc}") from exc
    if actual_summary != expected_summary:
        raise SubmissionError("summary.json is not the deterministic report aggregate")
    findings = scan_publication(root, denylist=denylist)
    if findings:
        raise SubmissionError("publication-safety scan failed: " + "; ".join(findings))
    return manifest, relative_paths


def initialize_submission_from_harbor(
    job_dir: Path,
    dataset: Path | str,
    output: Path,
    *,
    submission_id: str,
    title: str,
    provenance_level: str,
    contributor: str,
    configuration_label: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    attestor: str | None = None,
    attestation: str | None = None,
) -> dict[str, Any]:
    job_dir = job_dir.resolve()
    job = _load_json(job_dir / "result.json", "Harbor job result")
    dataset_name, expected_digests, release, dataset_root = (
        _resolve_harbor_dataset(dataset)
    )

    trial_dirs = sorted(
        path
        for path in job_dir.iterdir()
        if path.is_dir() and (path / "result.json").is_file()
    )
    if len(trial_dirs) != len(expected_digests):
        raise SubmissionError(
            "Harbor job must contain exactly one trial for every dataset task"
        )

    reports: list[Path] = []
    seen: set[str] = set()
    agent_identity: tuple[str, str] | None = None
    task_digests: dict[str, str] = {}
    for trial_dir in trial_dirs:
        trial = _load_json(trial_dir / "result.json", "Harbor trial result")
        task_name = trial.get("task_name")
        if task_name not in expected_digests or task_name in seen:
            raise SubmissionError(f"unexpected or duplicate Harbor task: {task_name}")
        seen.add(task_name)
        if trial.get("exception_info") is not None:
            raise SubmissionError(f"Harbor trial has an exception: {task_name}")

        lock = _load_json(trial_dir / "lock.json", "Harbor trial lock")
        locked_digest = (lock.get("task") or {}).get("digest")
        if locked_digest != expected_digests[task_name]:
            raise SubmissionError(f"Harbor task digest mismatch: {task_name}")
        task_digests[task_name] = locked_digest

        if dataset_root is not None:
            task_slug = task_name.split("/", 1)[-1]
            task_root = dataset_root / task_slug
            _validate_harbor_task(task_root, task_name, release)

        report_path = _single_artifact(trial_dir, "svgap-report.json")
        verdict_path = _single_artifact(trial_dir, "harbor-verdict.json")
        report = _load_json(report_path, "SV-Gap report")
        try:
            report = validate_report_payload(report)
        except ReportValidationError as exc:
            raise SubmissionError(f"invalid Harbor SV-Gap report: {exc}") from exc
        verdict = _load_json(verdict_path, "Harbor verdict")
        _validate_harbor_agreement(task_name, trial, report, verdict)
        reports.append(report_path)

        info = trial.get("agent_info") or {}
        model = info.get("model_info") or {}
        identity = (info.get("name"), model.get("name"))
        if not all(isinstance(value, str) and value for value in identity):
            raise SubmissionError(f"Harbor agent identity is incomplete: {task_name}")
        if agent_identity is None:
            agent_identity = identity
        elif identity != agent_identity:
            raise SubmissionError("Harbor job mixes agent or model configurations")

    if seen != set(expected_digests):
        raise SubmissionError("Harbor job is missing dataset tasks")
    assert agent_identity is not None
    agent_name, inferred_model = agent_identity
    if agent_name == "oracle":
        raise SubmissionError("Harbor Oracle jobs cannot become model submissions")
    label = configuration_label or inferred_model
    exact_model = model_id
    if provenance_level == "public" and exact_model is None:
        exact_model = inferred_model
    source = {
        "kind": "harbor_job",
        "job_id": job.get("id"),
        "agent": agent_name,
        "model": inferred_model,
        "dataset": dataset_name,
        "task_digests": dict(sorted(task_digests.items())),
        "taskpack_digest": release["source_taskpack"]["canonical_digest"],
        "svgap_version": release["svgap_version"],
        "release_tag": release["release_tag"],
        "evaluator_image": release["evaluator_image"],
    }
    return initialize_submission(
        reports,
        output,
        submission_id=submission_id,
        title=title,
        track="generation",
        configuration_label=label,
        provenance_level=provenance_level,
        taskpack_id=release["source_taskpack"]["id"],
        taskpack_version=release["source_taskpack"]["version"],
        contributor=contributor,
        provider=provider,
        model_id=exact_model,
        attestor=attestor,
        attestation=attestation,
        source=source,
    )


def _resolve_harbor_dataset(
    dataset: Path | str,
) -> tuple[str, dict[str, str], dict[str, Any], Path | None]:
    candidate = Path(dataset)
    if candidate.exists() or isinstance(dataset, Path):
        dataset_root = candidate.resolve()
        if dataset_root.is_file():
            dataset_manifest_path = dataset_root
            dataset_root = dataset_root.parent
        else:
            dataset_manifest_path = dataset_root / "dataset.toml"
        dataset_manifest = _load_toml(
            dataset_manifest_path, "Harbor dataset manifest"
        )
        release = _load_json(dataset_root / "provenance.json", "Harbor provenance")
        dataset_info = dataset_manifest.get("dataset")
        entries = dataset_manifest.get("tasks")
    else:
        reference = str(dataset)
        profiles = {
            "svgap/svgap-reset-release@0.2": "svgap-reset-release-0.2.json",
        }
        profile_name = profiles.get(reference)
        if profile_name is None:
            raise SubmissionError(
                "unsupported Harbor dataset reference; use a pinned published "
                "reference such as svgap/svgap-reset-release@0.2 or a local "
                "dataset path"
            )
        try:
            profile_text = (
                resources.files("svgap")
                .joinpath("harbor_profiles", profile_name)
                .read_text(encoding="utf-8")
            )
            profile = json.loads(profile_text)
        except (OSError, json.JSONDecodeError) as exc:
            raise SubmissionError(
                f"cannot read trusted Harbor dataset profile: {exc}"
            ) from exc
        if profile.get("schema_version") != "1.0":
            raise SubmissionError("unsupported trusted Harbor dataset profile")
        if profile.get("registry_reference") != reference:
            raise SubmissionError("trusted Harbor dataset profile identity mismatch")
        dataset_info = profile.get("dataset")
        entries = profile.get("tasks")
        release = profile.get("provenance")
        dataset_root = None

    if not isinstance(release, dict):
        raise SubmissionError("invalid Harbor release provenance")
    _validate_harbor_provenance(release)
    if not isinstance(dataset_info, dict) or not isinstance(entries, list):
        raise SubmissionError("invalid Harbor dataset manifest")
    dataset_name = dataset_info.get("name")
    if dataset_name != release["dataset"]:
        raise SubmissionError("Harbor dataset and release provenance disagree")
    expected_digests = {
        entry.get("name"): entry.get("digest")
        for entry in entries
        if isinstance(entry, dict)
    }
    if not expected_digests or not all(
        isinstance(name, str)
        and isinstance(digest, str)
        and re.fullmatch(r"sha256:[a-f0-9]{64}", digest) is not None
        for name, digest in expected_digests.items()
    ):
        raise SubmissionError("Harbor dataset task entries are invalid")
    return dataset_name, expected_digests, release, dataset_root


def bundle_submission(root: Path, output: Path, *, denylist: Path | None = None) -> str:
    root = root.resolve()
    manifest, relative_paths = validate_submission(root, denylist=denylist)
    members = [root / "submission.json", *[root / path for path in relative_paths]]
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(
        filename="", fileobj=raw, mode="wb", mtime=0
    ) as compressed, tarfile.open(
        fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
    ) as archive:
        for path in sorted(members, key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root)
            info = archive.gettarinfo(
                str(path), arcname=f"{manifest['submission_id']}/{relative}"
            )
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as handle:
                archive.addfile(info, handle)
    return _sha256(output)


def registry_entry(root: Path) -> dict[str, Any]:
    manifest, _ = validate_submission(root)
    summary = json.loads((root / manifest["artifacts"]["summary"]).read_text())
    return {
        "submission_id": manifest["submission_id"],
        "title": manifest["title"],
        "track": manifest["track"],
        "configuration": manifest["configuration"],
        "taskpack": manifest["taskpack"],
        "contributor": manifest["contributor"],
        "created_at": manifest["created_at"],
        "claim_boundary": manifest["claim_boundary"],
        "summary": summary,
        "source": root.as_posix(),
    }


def scan_publication(root: Path, *, denylist: Path | None = None) -> list[str]:
    custom: list[tuple[str, re.Pattern[str]]] = []
    if denylist:
        try:
            lines = denylist.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise SubmissionError(f"cannot read private denylist: {exc}") from exc
        for index, line in enumerate(lines, start=1):
            pattern = line.strip()
            if not pattern or pattern.startswith("#"):
                continue
            try:
                custom.append((f"private denylist line {index}", re.compile(pattern, re.I)))
            except re.error as exc:
                raise SubmissionError(f"invalid denylist regex on line {index}: {exc}") from exc
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {
            ".json",
            ".md",
            ".txt",
            ".toml",
            ".sv",
            ".v",
            ".csv",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(root).as_posix()
        for label, pattern in (*_BUILTIN_DENY_PATTERNS, *custom):
            if pattern.search(text):
                findings.append(f"{relative}: {label}")
    return findings


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"cannot read {label} at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SubmissionError(f"{label} must be a JSON object: {path}")
    return payload


def _load_toml(path: Path, label: str) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SubmissionError(f"cannot read {label} at {path}: {exc}") from exc


def _single_artifact(trial_dir: Path, name: str) -> Path:
    matches = sorted((trial_dir / "artifacts").glob(f"**/{name}"))
    if len(matches) != 1:
        raise SubmissionError(
            f"Harbor trial must contain exactly one {name}: {trial_dir.name}"
        )
    return matches[0]


def _validate_harbor_provenance(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset",
        "source_taskpack",
        "svgap_version",
        "release_tag",
        "evaluator_image",
    }
    if set(payload) != required or payload.get("schema_version") != "1.0":
        raise SubmissionError("invalid Harbor provenance fields or schema")
    taskpack = payload.get("source_taskpack")
    if not isinstance(taskpack, dict) or set(taskpack) != {
        "id",
        "version",
        "canonical_digest",
    }:
        raise SubmissionError("invalid Harbor source taskpack provenance")
    strings = [
        payload.get("dataset"),
        payload.get("svgap_version"),
        payload.get("release_tag"),
        payload.get("evaluator_image"),
        *taskpack.values(),
    ]
    if not all(isinstance(value, str) and value for value in strings):
        raise SubmissionError("Harbor provenance values must be nonempty strings")
    if "@sha256:" not in payload["evaluator_image"]:
        raise SubmissionError("Harbor evaluator image must be digest-pinned")


def _validate_harbor_task(
    task_root: Path, task_name: str, release: dict[str, Any]
) -> None:
    config = _load_toml(task_root / "task.toml", "Harbor task configuration")
    if (config.get("task") or {}).get("name") != task_name:
        raise SubmissionError(f"Harbor task identity mismatch: {task_name}")
    metadata = config.get("metadata") or {}
    expected_taskpack = (
        f'{release["source_taskpack"]["id"]}-v'
        f'{release["source_taskpack"]["version"]}'
    )
    if metadata.get("source_taskpack") != expected_taskpack:
        raise SubmissionError(f"Harbor taskpack metadata mismatch: {task_name}")
    if metadata.get("svgap_version") != release["svgap_version"]:
        raise SubmissionError(f"Harbor SV-Gap version mismatch: {task_name}")
    try:
        first = next(
            line.strip()
            for line in (task_root / "environment" / "Dockerfile")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    except (OSError, StopIteration) as exc:
        raise SubmissionError(f"cannot read Harbor task image: {task_name}") from exc
    if first != f'FROM {release["evaluator_image"]}':
        raise SubmissionError(f"Harbor evaluator image mismatch: {task_name}")


def _harbor_rewards(report: dict[str, Any]) -> dict[str, int]:
    functional = report["functional"]["status"]
    structural = report["structural"]["status"]
    functional_accept = int(functional == "pass")
    structural_accept = int(structural == "pass")
    return {
        "reward": int(functional_accept == 1 and structural_accept == 1),
        "functional_accept": functional_accept,
        "structural_accept": structural_accept,
        "gap_member": int(bool(report["gap_member"])),
        "unknown": int(
            functional in {"unknown", "not_run"}
            or structural in {"unknown", "not_run"}
        ),
        "tool_error": int("tool_error" in {functional, structural}),
    }


def _validate_harbor_agreement(
    task_name: str,
    trial: dict[str, Any],
    report: dict[str, Any],
    verdict: dict[str, Any],
) -> None:
    expected = _harbor_rewards(report)
    actual = (trial.get("verifier_result") or {}).get("rewards")
    if not isinstance(actual, dict):
        raise SubmissionError(f"Harbor rewards are missing: {task_name}")
    for key, value in expected.items():
        if actual.get(key) != value:
            raise SubmissionError(f"Harbor reward/report mismatch for {task_name}: {key}")
    expected_verdict = {
        "functional_status": report["functional"]["status"],
        "structural_status": report["structural"]["status"],
        "gap_member": bool(expected["gap_member"]),
        "unknown": bool(expected["unknown"]),
        "tool_error": bool(expected["tool_error"]),
        "primary_reward": expected["reward"],
    }
    for key, value in expected_verdict.items():
        if verdict.get(key) != value:
            raise SubmissionError(f"Harbor verdict/report mismatch for {task_name}: {key}")


def _validate_harbor_source(source: Any) -> None:
    required = {
        "kind",
        "job_id",
        "agent",
        "model",
        "dataset",
        "task_digests",
        "taskpack_digest",
        "svgap_version",
        "release_tag",
        "evaluator_image",
    }
    if not isinstance(source, dict) or set(source) != required:
        raise SubmissionError("invalid Harbor submission source")
    if source.get("kind") != "harbor_job":
        raise SubmissionError("unsupported submission source kind")
    values = [source[key] for key in required - {"task_digests"}]
    if not all(isinstance(value, str) and value for value in values):
        raise SubmissionError("Harbor submission source values must be nonempty strings")
    digests = source["task_digests"]
    if not isinstance(digests, dict) or not digests:
        raise SubmissionError("Harbor submission source task digests are missing")
    if not all(
        isinstance(name, str)
        and isinstance(digest, str)
        and re.fullmatch(r"sha256:[a-f0-9]{64}", digest) is not None
        for name, digest in digests.items()
    ):
        raise SubmissionError("Harbor submission source task digests are invalid")
    if re.fullmatch(r"sha256:[a-f0-9]{64}", source["taskpack_digest"]) is None:
        raise SubmissionError("Harbor submission source taskpack digest is invalid")
    if (
        re.fullmatch(r".+@sha256:[a-f0-9]{64}", source["evaluator_image"])
        is None
    ):
        raise SubmissionError("Harbor submission source evaluator image is invalid")


def _validate_provenance(
    level: str,
    *,
    model_id: str | None,
    attestor: str | None,
    attestation: str | None,
) -> None:
    if level == "public" and not model_id:
        raise SubmissionError("public provenance requires an exact model_id")
    if level == "attested_alias" and (not attestor or not attestation):
        raise SubmissionError("attested_alias provenance requires attestor and attestation")
    if level != "public" and model_id:
        raise SubmissionError("exact model_id is allowed only for public provenance")


def _validate_slug(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise SubmissionError(f"{field} must match {_SLUG.pattern}")


def _filename_slug(value: str) -> str:
    rendered = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-.")
    return rendered or "candidate"


def _load_evidence(path: Path, track: str, configuration_label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"invalid evidence {path}: {exc}") from exc
    if track == "generation":
        try:
            return validate_report_payload(payload)
        except ReportValidationError as exc:
            raise SubmissionError(f"invalid generation report {path}: {exc}") from exc
    required = {
        "schema_version", "challenge_id", "task_id", "track", "model", "run_id",
        "overall", "profile", "claim_boundary",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise SubmissionError(f"challenge result fields do not match schema v1: {path}")
    if payload["schema_version"] != "1.0" or payload["track"] != track:
        raise SubmissionError(f"challenge result track/schema mismatch: {path}")
    if payload["model"] != configuration_label:
        raise SubmissionError(
            f"challenge result model must match configuration label: {path}"
        )
    if payload["overall"] not in {"pass", "fail"} or not isinstance(payload["profile"], list):
        raise SubmissionError(f"invalid challenge result outcome/profile: {path}")
    if not payload["profile"]:
        raise SubmissionError(f"challenge result profile is empty: {path}")
    for item in payload["profile"]:
        if not isinstance(item, dict) or set(item) != {"check", "pass", "evidence"}:
            raise SubmissionError(f"invalid challenge result check: {path}")
        if not isinstance(item["check"], str) or not item["check"]:
            raise SubmissionError(f"challenge result check name is empty: {path}")
        if not isinstance(item["pass"], bool) or not isinstance(item["evidence"], str):
            raise SubmissionError(f"invalid challenge result check values: {path}")
    expected_overall = "pass" if all(item["pass"] for item in payload["profile"]) else "fail"
    if payload["overall"] != expected_overall:
        raise SubmissionError(f"challenge result overall is inconsistent: {path}")
    return payload


def _summarize_evidence(track: str, paths: Iterable[Path]) -> dict[str, Any]:
    paths = list(paths)
    if track == "generation":
        summary = summarize_reports(paths)
        return {"kind": "generation_reports", **summary}
    results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    checks: dict[str, dict[str, int]] = {}
    outcomes = {"pass": 0, "fail": 0}
    runs = []
    for result in results:
        outcomes[result["overall"]] += 1
        runs.append(
            {
                "challenge_id": result["challenge_id"],
                "task_id": result["task_id"],
                "run_id": result["run_id"],
                "overall": result["overall"],
            }
        )
        for item in result["profile"]:
            counts = checks.setdefault(item["check"], {"pass": 0, "fail": 0})
            counts["pass" if item["pass"] else "fail"] += 1
    return {
        "kind": "challenge_results",
        "result_count": len(results),
        "overall_statuses": outcomes,
        "checks": [{"check": name, **checks[name]} for name in sorted(checks)],
        "runs": sorted(runs, key=lambda item: (item["task_id"], item["run_id"])),
    }


def _inside(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise SubmissionError("artifact paths must be nonempty strings")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SubmissionError(f"artifact escapes submission directory: {relative}") from exc
    return candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
