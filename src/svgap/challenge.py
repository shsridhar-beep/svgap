from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from svgap.validation import ReportValidationError, validate_report_payload


class ChallengeError(ValueError):
    pass


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChallengeError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChallengeError(f"{label} must be a JSON object")
    return payload


def load_challenge_task(path: Path) -> dict[str, Any]:
    task = _load_object(path, "challenge task")
    common = {"schema_version", "challenge_id", "task_id", "track", "title"}
    if task.get("schema_version") != "1.0":
        raise ChallengeError("unsupported challenge task schema_version")
    if task.get("track") == "diagnosis":
        allowed = common | {"questions"}
        if set(task) != allowed or not isinstance(task.get("questions"), list):
            raise ChallengeError("diagnosis task fields do not match schema v1")
        if not task["questions"]:
            raise ChallengeError("diagnosis task requires questions")
        identifiers: set[str] = set()
        for question in task["questions"]:
            if not isinstance(question, dict) or set(question) != {
                "question_id",
                "prompt",
                "expected_status",
            }:
                raise ChallengeError("diagnosis question fields do not match schema v1")
            if question["expected_status"] not in {"answered", "failed", "unanswered"}:
                raise ChallengeError("diagnosis expected_status is unsupported")
            identifier = question["question_id"]
            if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                raise ChallengeError("diagnosis question_id values must be unique and nonempty")
            identifiers.add(identifier)
    elif task.get("track") == "generation":
        if set(task) != common:
            raise ChallengeError("generation task fields do not match schema v1")
    elif task.get("track") == "repair":
        if set(task) != common | {"target_rule"}:
            raise ChallengeError("repair task fields do not match schema v1")
        if not isinstance(task.get("target_rule"), str) or not task["target_rule"]:
            raise ChallengeError("repair target_rule must be nonempty")
    else:
        raise ChallengeError("challenge track must be generation, diagnosis, or repair")
    for key in ("challenge_id", "task_id", "title"):
        if not isinstance(task.get(key), str) or not task[key].strip():
            raise ChallengeError(f"challenge task {key} must be nonempty")
    return task


def load_challenge_submission(path: Path, task: dict[str, Any]) -> dict[str, Any]:
    submission = _load_object(path, "challenge submission")
    common = {
        "schema_version",
        "challenge_id",
        "task_id",
        "model",
        "run_id",
    }
    if submission.get("schema_version") != "1.0":
        raise ChallengeError("unsupported challenge submission schema_version")
    for key in ("challenge_id", "task_id", "model", "run_id"):
        if not isinstance(submission.get(key), str) or not submission[key].strip():
            raise ChallengeError(f"challenge submission {key} must be nonempty")
    if submission["challenge_id"] != task["challenge_id"] or submission["task_id"] != task["task_id"]:
        raise ChallengeError("submission challenge_id and task_id must match the task")
    if task["track"] == "diagnosis":
        if set(submission) != common | {"responses"}:
            raise ChallengeError("diagnosis submission fields do not match schema v1")
        responses = submission["responses"]
        if not isinstance(responses, list):
            raise ChallengeError("diagnosis responses must be an array")
        for response in responses:
            if not isinstance(response, dict) or set(response) != {
                "question_id",
                "status",
                "evidence",
                "next_evidence",
            }:
                raise ChallengeError("diagnosis response fields do not match schema v1")
            if response["status"] not in {"answered", "failed", "unanswered"}:
                raise ChallengeError("diagnosis response status is unsupported")
            for key in ("question_id", "evidence", "next_evidence"):
                if not isinstance(response[key], str):
                    raise ChallengeError(f"diagnosis response {key} must be a string")
    else:
        if set(submission) != common | {"artifacts"}:
            raise ChallengeError(f"{task['track']} submission fields do not match schema v1")
        artifacts = submission["artifacts"]
        expected = {"report"} if task["track"] == "generation" else {"before_report", "after_report"}
        if not isinstance(artifacts, dict) or set(artifacts) != expected:
            raise ChallengeError(f"{task['track']} artifacts do not match schema v1")
        if not all(isinstance(value, str) and value for value in artifacts.values()):
            raise ChallengeError("challenge artifact paths must be nonempty strings")
    return submission


def _report_from_submission(submission_path: Path, relative: str) -> dict[str, Any]:
    base = submission_path.resolve().parent
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ChallengeError("challenge artifact paths must remain inside the submission directory")
    try:
        return validate_report_payload(_load_object(path, "evaluation report"))
    except ReportValidationError as exc:
        raise ChallengeError(f"invalid evaluation report {path}: {exc}") from exc


def score_challenge(task_path: Path, submission_path: Path) -> dict[str, Any]:
    task = load_challenge_task(task_path)
    submission = load_challenge_submission(submission_path, task)
    if task["track"] == "generation":
        profile = _score_generation(
            _report_from_submission(submission_path, submission["artifacts"]["report"])
        )
    elif task["track"] == "diagnosis":
        profile = _score_diagnosis(task, submission)
    else:
        profile = _score_repair(
            task,
            _report_from_submission(submission_path, submission["artifacts"]["before_report"]),
            _report_from_submission(submission_path, submission["artifacts"]["after_report"]),
        )
    return {
        "schema_version": "1.0",
        "challenge_id": task["challenge_id"],
        "task_id": task["task_id"],
        "track": task["track"],
        "model": submission["model"],
        "run_id": submission["run_id"],
        "overall": "pass" if all(item["pass"] for item in profile) else "fail",
        "profile": profile,
        "claim_boundary": (
            "This profile describes submitted digital RTL evidence under the configured "
            "functional and structural checks; it is not silicon signoff."
        ),
    }


def _check(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"check": name, "pass": passed, "evidence": evidence}


def _score_generation(report: dict[str, Any]) -> list[dict[str, Any]]:
    functional = report["functional"]
    structural = report["structural"]
    functional_provenance = bool(
        functional.get("commands") or functional.get("imported_from")
    )
    return [
        _check("functional_pass", functional["status"] == "pass", functional["status"]),
        _check(
            "structural_determinate",
            structural["status"] in {"pass", "fail"},
            structural["status"],
        ),
        _check("structural_pass", structural["status"] == "pass", structural["status"]),
        _check(
            "functional_provenance_declared",
            functional_provenance,
            "commands or imported_from present" if functional_provenance else "missing",
        ),
        _check(
            "tool_clean",
            functional["status"] != "tool_error" and structural["status"] != "tool_error",
            f"functional={functional['status']} structural={structural['status']}",
        ),
    ]


def _score_diagnosis(
    task: dict[str, Any], submission: dict[str, Any]
) -> list[dict[str, Any]]:
    responses = {item["question_id"]: item for item in submission["responses"]}
    if len(responses) != len(submission["responses"]):
        raise ChallengeError("diagnosis response question_id values must be unique")
    expected_ids = {item["question_id"] for item in task["questions"]}
    if set(responses) != expected_ids:
        raise ChallengeError("diagnosis responses must answer exactly the task questions")
    profile = []
    for question in task["questions"]:
        response = responses[question["question_id"]]
        status_match = response["status"] == question["expected_status"]
        evidence_present = bool(response["evidence"].strip())
        resolution_present = response["status"] != "unanswered" or bool(
            response["next_evidence"].strip()
        )
        profile.extend(
            [
                _check(
                    f"{question['question_id']}:status",
                    status_match,
                    f"expected={question['expected_status']} actual={response['status']}",
                ),
                _check(
                    f"{question['question_id']}:evidence",
                    evidence_present,
                    "present" if evidence_present else "missing",
                ),
                _check(
                    f"{question['question_id']}:resolution",
                    resolution_present,
                    "present or not required" if resolution_present else "missing next evidence",
                ),
            ]
        )
    return profile


def _score_repair(
    task: dict[str, Any], before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    target = task["target_rule"]
    before_rules = {item["rule_id"] for item in before["structural"]["findings"]}
    after_rules = {item["rule_id"] for item in after["structural"]["findings"]}
    new_rules = sorted(after_rules - before_rules)
    return [
        _check(
            "same_candidate_id",
            before["candidate_id"] == after["candidate_id"],
            f"before={before['candidate_id']} after={after['candidate_id']}",
        ),
        _check(
            "same_structural_backend",
            before["structural"]["backend"] == after["structural"]["backend"],
            f"before={before['structural']['backend']} after={after['structural']['backend']}",
        ),
        _check("target_present_before", target in before_rules, ", ".join(sorted(before_rules)) or "none"),
        _check("target_removed_after", target not in after_rules, ", ".join(sorted(after_rules)) or "none"),
        _check("functional_pass_after", after["functional"]["status"] == "pass", after["functional"]["status"]),
        _check("structural_pass_after", after["structural"]["status"] == "pass", after["structural"]["status"]),
        _check("no_new_rule_regression", not new_rules, ", ".join(new_rules) or "none"),
    ]
