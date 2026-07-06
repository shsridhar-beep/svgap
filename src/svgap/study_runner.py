"""Provider-neutral generation studies over packaged frozen taskpacks."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Iterable

from svgap.api import evaluate
from svgap.pilot import materialize_candidate
from svgap.reporting import build_html
from svgap.resources import ResourceError, taskpack_metadata, taskpack_root
from svgap.study import summarize_reports
from svgap.validation import validate_report_payload


class StudyError(ValueError):
    pass


def select_study_shape(
    taskpack: str,
    *,
    full: bool = False,
    tasks: Iterable[str] | None = None,
    samples: int | None = None,
) -> tuple[list[str], int, str]:
    metadata = taskpack_metadata(taskpack)
    available = metadata["tasks"]
    selected = list(tasks or ([] if full else [metadata["smoke_task"]]))
    if full and not selected:
        selected = list(available)
    if not selected:
        selected = [metadata["smoke_task"]]
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise StudyError(f"unknown task(s): {', '.join(unknown)}")
    count = samples if samples is not None else (metadata["full_samples"] if full else 1)
    if count < 1:
        raise StudyError("samples must be positive")
    return selected, count, "full" if full else "smoke"


def run_study(
    taskpack: str,
    *,
    command: str,
    label: str,
    interface_label: str,
    output: Path,
    full: bool = False,
    tasks: Iterable[str] | None = None,
    samples: int | None = None,
    generate_only: bool = False,
    generation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected, sample_count, mode = select_study_shape(
        taskpack, full=full, tasks=tasks, samples=samples
    )
    output = _new_output(output)
    pack = taskpack_root(taskpack)
    pack_metadata = taskpack_metadata(taskpack)
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="svgap-generate-") as directory:
        sandbox = Path(directory)
        for sample in range(1, sample_count + 1):
            run_id = f"{label}--sample-{sample:02d}"
            response_dir = output / "_responses" / run_id
            response_dir.mkdir(parents=True, exist_ok=True)
            for task in selected:
                task_dir = pack / "tasks" / task
                prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
                try:
                    response = _run_command(command, prompt, sandbox)
                except (OSError, subprocess.SubprocessError) as exc:
                    failures.append(f"{run_id}/{task}: {exc}")
                    continue
                response_path = response_dir / f"{task}.txt"
                response_path.write_text(response, encoding="utf-8")
                generation = _generation_metadata(
                    taskpack=pack_metadata,
                    task=task,
                    label=label,
                    interface_label=interface_label,
                    command=command,
                    sample=sample,
                    mode=mode,
                    generation_config=generation_config or {},
                )
                metadata_path = response_path.with_suffix(".generation.json")
                metadata_path.write_text(
                    json.dumps(generation, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                if generate_only:
                    continue
                try:
                    _evaluate_response(
                        task_dir, response_path, label, run_id, output, metadata_path
                    )
                except (OSError, ValueError) as exc:
                    failures.append(f"{run_id}/{task}: {exc}")
    if failures:
        (output / "failures.json").write_text(
            json.dumps({"failures": failures}, indent=2) + "\n", encoding="utf-8"
        )
    if generate_only:
        result = {
            "mode": mode,
            "responses": sample_count * len(selected) - len(failures),
            "failures": failures,
            "output": str(output),
        }
    else:
        result = write_study_profile(output)
        result.update({"mode": mode, "failures": failures})
    return result


def evaluate_saved_responses(
    taskpack: str, *, responses: Path, output: Path
) -> dict[str, Any]:
    output = _new_output(output)
    pack = taskpack_root(taskpack)
    paths = sorted(responses.resolve().glob("*/*.txt"))
    if not paths:
        raise StudyError(f"no <run>/<task>.txt responses found under {responses}")
    failures: list[str] = []
    for response in paths:
        run_id, task = response.parent.name, response.stem
        metadata_path = response.with_suffix(".generation.json")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            label = str(metadata["configuration_label"])
            _evaluate_response(
                pack / "tasks" / task,
                response,
                label,
                run_id,
                output,
                metadata_path,
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            failures.append(f"{run_id}/{task}: {exc}")
    result = write_study_profile(output)
    result["failures"] = failures
    if failures:
        (output / "failures.json").write_text(
            json.dumps({"failures": failures}, indent=2) + "\n", encoding="utf-8"
        )
    return result


def write_study_profile(output: Path) -> dict[str, Any]:
    reports = sorted(output.glob("*/*/report.json"))
    if not reports:
        raise StudyError("study produced no evaluation reports")
    summary = summarize_reports(reports)
    summary_path = output / "study-summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    payloads = [
        validate_report_payload(json.loads(path.read_text(encoding="utf-8")))
        for path in reports
    ]
    profile_path = output / "evidence-profile.html"
    profile_path.write_text(build_html(payloads), encoding="utf-8")
    evidence_path = output / "evidence-files.txt"
    evidence_path.write_text(
        "".join(f"{path.relative_to(output).as_posix()}\n" for path in reports),
        encoding="utf-8",
    )
    return {
        "report_count": summary["report_count"],
        "functional_pass": summary["functional_pass"],
        "gap_members": summary["gap_members"],
        "summary": str(summary_path),
        "profile": str(profile_path),
        "evidence": str(evidence_path),
    }


def _new_output(output: Path) -> Path:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise StudyError(f"refusing to overwrite nonempty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    return output


def _run_command(command: str, prompt: str, sandbox: Path) -> str:
    completed = subprocess.run(
        command,
        shell=True,
        input=prompt,
        cwd=sandbox,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if completed.returncode:
        raise subprocess.SubprocessError(completed.stderr[-4000:])
    if not completed.stdout.strip():
        raise subprocess.SubprocessError("generation command produced empty stdout")
    return completed.stdout


def _evaluate_response(
    task_dir: Path,
    response_path: Path,
    label: str,
    run_id: str,
    output: Path,
    metadata_path: Path,
) -> None:
    manifest = materialize_candidate(task_dir, response_path, label, output, run_id)
    relative_manifest = manifest.relative_to(output).as_posix()
    evaluate(manifest, manifest_label=relative_manifest)
    shutil.copy2(metadata_path, manifest.parent / "generation.json")


def _generation_metadata(
    *,
    taskpack: dict[str, Any],
    task: str,
    label: str,
    interface_label: str,
    command: str,
    sample: int,
    mode: str,
    generation_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "provider": "command",
        "interface_version": interface_label,
        "configuration_label": label,
        "sample": sample,
        "task": task,
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": [command],
        "generation_config": generation_config,
        "taskpack": {
            "id": taskpack["id"],
            "version": taskpack["version"],
            "canonical_digest": taskpack["canonical_digest"],
        },
    }
