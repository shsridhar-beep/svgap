"""Run packaged diagnosis and repair challenges through a command harness."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from svgap.api import evaluate
from svgap.challenge import score_challenge
from svgap.pilot import materialize_candidate
from svgap.resources import challenge_root


class ChallengeRunError(ValueError):
    pass


def run_challenge(
    track: str, *, command: str, label: str, run_id: str, output: Path
) -> dict[str, object]:
    if track not in {"diagnosis", "repair"}:
        raise ChallengeRunError("challenge run supports diagnosis or repair")
    output = output.resolve()
    if output.exists():
        raise ChallengeRunError(f"refusing to overwrite output directory: {output}")
    output.mkdir(parents=True)
    if track == "diagnosis":
        _run_diagnosis(command, label, run_id, output)
    else:
        _run_repair(command, label, run_id, output)
    return json.loads((output / "result.json").read_text(encoding="utf-8"))


def _run_diagnosis(command: str, label: str, run_id: str, output: Path) -> None:
    root = challenge_root() / "diagnosis"
    raw = _run_model(command, (root / "prompt.md").read_text(encoding="utf-8"))
    (output / "raw-response.txt").write_text(raw, encoding="utf-8")
    payload = _extract_json(raw)
    responses = payload.get("responses")
    if not isinstance(responses, list):
        raise ChallengeRunError(
            "diagnosis response must be a JSON object with a responses array"
        )
    submission = {
        "schema_version": "1.0",
        "challenge_id": "frontier-model-handoff-v0.1",
        "task_id": "diagnose-production-evidence",
        "model": label,
        "run_id": run_id,
        "responses": responses,
    }
    _write_and_score(root / "task.json", submission, output)


def _run_repair(command: str, label: str, run_id: str, output: Path) -> None:
    root = challenge_root() / "repair"
    starter = root / "starter"
    prompt = (root / "prompt.md").read_text(encoding="utf-8")
    unsafe = (starter / "before.sv").read_text(encoding="utf-8")
    raw = _run_model(command, f"{prompt}\n\nUnsafe module:\n```systemverilog\n{unsafe}```\n")
    (output / "raw-response.txt").write_text(raw, encoding="utf-8")
    after_response = output / "after-response.txt"
    after_response.write_text(raw, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="svgap-repair-") as directory:
        work = Path(directory)
        before = _evaluate(starter, starter / "before.sv", "starter-input", "before", work)
        after = _evaluate(starter, after_response, label, "after", work)
        shutil.copy2(before, output / "before-report.json")
        shutil.copy2(after, output / "after-report.json")
    submission = {
        "schema_version": "1.0",
        "challenge_id": "frontier-model-handoff-v0.1",
        "task_id": "repair-reset-domain-finding",
        "model": label,
        "run_id": run_id,
        "artifacts": {
            "before_report": "before-report.json",
            "after_report": "after-report.json",
        },
    }
    _write_and_score(root / "task.json", submission, output)


def _run_model(command: str, prompt: str) -> str:
    completed = subprocess.run(
        command,
        shell=True,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if completed.returncode:
        raise subprocess.SubprocessError(completed.stderr[-4000:])
    if not completed.stdout.strip():
        raise subprocess.SubprocessError("model command produced empty stdout")
    return completed.stdout


def _extract_json(text: str) -> dict[str, object]:
    for candidate in [*re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S), text]:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ChallengeRunError("model response does not contain a JSON object")


def _evaluate(
    task: Path, response: Path, label: str, run_id: str, output: Path
) -> Path:
    manifest = materialize_candidate(task, response, label, output, run_id)
    evaluate(manifest, manifest_label=manifest.relative_to(output).as_posix())
    report = manifest.parent / "report.json"
    if not report.is_file():
        raise ChallengeRunError(f"evaluation report was not written: {report}")
    return report


def _write_and_score(
    task: Path, submission: dict[str, object], output: Path
) -> None:
    submission_path = output / "submission.json"
    submission_path.write_text(
        json.dumps(submission, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result = score_challenge(task, submission_path)
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
