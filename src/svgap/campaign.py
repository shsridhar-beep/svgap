"""Resumable, replayable generation and repair campaigns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from typing import Any

from svgap.api import evaluate
from svgap.pilot import load_task, materialize_candidate, resolve_prompt
from svgap.resources import TASKPACKS, ResourceError, taskpack_root
from svgap.validation import (
    configured_contract_status as derive_contract_status,
    oracle_results as normalized_oracle_results,
)


class CampaignError(ValueError):
    pass


@dataclass(frozen=True)
class CampaignSpec:
    path: Path
    campaign_id: str
    taskpack: str
    taskpack_root: Path
    tasks: tuple[str, ...]
    samples: int
    prompt_level: str | None
    command: str
    label: str
    interface_label: str
    timeout_seconds: int
    base_seed: int
    repair_enabled: bool
    max_attempts: int
    feedback: str
    max_model_calls: int | None
    wall_seconds: int | None


def load_campaign(path: Path) -> CampaignSpec:
    path = path.resolve()
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CampaignError(f"cannot read campaign manifest: {exc}") from exc
    allowed = {
        "schema_version",
        "id",
        "taskpack",
        "tasks",
        "samples",
        "prompt_level",
        "generator",
        "execution",
        "repair",
        "budget",
    }
    extras = sorted(set(payload) - allowed)
    if extras:
        raise CampaignError(f"unsupported campaign fields: {', '.join(extras)}")
    if payload.get("schema_version") != "1.0":
        raise CampaignError('campaign schema_version must be "1.0"')
    campaign_id = payload.get("id")
    if not isinstance(campaign_id, str) or re.fullmatch(
        r"[a-z][a-z0-9_.-]*", campaign_id
    ) is None:
        raise CampaignError("campaign id must be a lowercase stable identifier")
    taskpack = payload.get("taskpack")
    if not isinstance(taskpack, str) or not taskpack:
        raise CampaignError("campaign taskpack must be a nonempty string")
    pack_root = _resolve_taskpack(path, taskpack)
    available = sorted(
        item.name for item in (pack_root / "tasks").iterdir() if item.is_dir()
    )
    if not available:
        raise CampaignError(f"taskpack has no tasks: {pack_root}")
    raw_tasks = payload.get("tasks")
    if raw_tasks is None:
        if taskpack in TASKPACKS:
            raw_tasks = [TASKPACKS[taskpack]["smoke_task"]]
        else:
            raw_tasks = [available[0]]
    if not isinstance(raw_tasks, list) or not raw_tasks or not all(
        isinstance(item, str) and item for item in raw_tasks
    ):
        raise CampaignError("campaign tasks must be a nonempty string array")
    if len(raw_tasks) != len(set(raw_tasks)):
        raise CampaignError("campaign tasks must be unique")
    unknown = sorted(set(raw_tasks) - set(available))
    if unknown:
        raise CampaignError(f"unknown campaign tasks: {', '.join(unknown)}")
    samples = _positive_int(payload.get("samples", 1), "samples")
    prompt_level = payload.get("prompt_level")
    if prompt_level is not None and not isinstance(prompt_level, str):
        raise CampaignError("prompt_level must be a string")
    for task_name in raw_tasks:
        task_dir = pack_root / "tasks" / task_name
        try:
            resolve_prompt(task_dir, load_task(task_dir), prompt_level)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            raise CampaignError(f"invalid campaign task {task_name!r}: {exc}") from exc

    generator = _table(payload, "generator", required=True)
    _only_fields(generator, "generator", {"command", "label", "interface_label"})
    command = generator.get("command")
    label = generator.get("label")
    if not isinstance(command, str) or not command.strip():
        raise CampaignError("generator.command must be a nonempty string")
    if not isinstance(label, str) or not label.strip():
        raise CampaignError("generator.label must be a nonempty string")
    interface_label = generator.get("interface_label", "custom-command")
    if not isinstance(interface_label, str) or not interface_label:
        raise CampaignError("generator.interface_label must be a nonempty string")

    execution = _table(payload, "execution")
    _only_fields(execution, "execution", {"timeout_seconds", "seed"})
    timeout_seconds = _bounded_int(
        execution.get("timeout_seconds", 600), "execution.timeout_seconds", 1, 3600
    )
    base_seed = _bounded_int(
        execution.get("seed", 0), "execution.seed", 0, 2_147_483_647
    )
    repair = _table(payload, "repair")
    _only_fields(repair, "repair", {"enabled", "max_attempts", "feedback"})
    repair_enabled = repair.get("enabled", False)
    if not isinstance(repair_enabled, bool):
        raise CampaignError("repair.enabled must be boolean")
    max_attempts = _bounded_int(
        repair.get("max_attempts", 3 if repair_enabled else 1),
        "repair.max_attempts",
        1,
        20,
    )
    if not repair_enabled and max_attempts != 1:
        raise CampaignError("repair.max_attempts must be 1 when repair is disabled")
    feedback = repair.get("feedback", "finding")
    if feedback not in {"finding", "diagnostic", "full"}:
        raise CampaignError("repair.feedback must be finding, diagnostic, or full")

    budget = _table(payload, "budget")
    _only_fields(budget, "budget", {"max_model_calls", "wall_seconds"})
    max_model_calls = _optional_positive_int(
        budget.get("max_model_calls"), "budget.max_model_calls"
    )
    wall_seconds = _optional_positive_int(
        budget.get("wall_seconds"), "budget.wall_seconds"
    )
    return CampaignSpec(
        path=path,
        campaign_id=campaign_id,
        taskpack=taskpack,
        taskpack_root=pack_root,
        tasks=tuple(raw_tasks),
        samples=samples,
        prompt_level=prompt_level,
        command=command,
        label=label,
        interface_label=interface_label,
        timeout_seconds=timeout_seconds,
        base_seed=base_seed,
        repair_enabled=repair_enabled,
        max_attempts=max_attempts,
        feedback=feedback,
        max_model_calls=max_model_calls,
        wall_seconds=wall_seconds,
    )


def plan_campaign(path: Path) -> dict[str, Any]:
    spec = load_campaign(path)
    cells = _cells(spec)
    return {
        "schema_version": "1.0",
        "campaign_id": spec.campaign_id,
        "taskpack": spec.taskpack,
        "taskpack_path": str(spec.taskpack_root),
        "cells": cells,
        "cell_count": len(cells),
        "initial_model_calls": len(cells),
        "maximum_model_calls": len(cells) * spec.max_attempts,
        "configured_model_call_budget": spec.max_model_calls,
        "configured_wall_seconds": spec.wall_seconds,
        "base_seed": spec.base_seed,
        "repair": {
            "enabled": spec.repair_enabled,
            "max_attempts": spec.max_attempts,
            "feedback": spec.feedback,
        },
    }


def run_campaign(path: Path, output: Path) -> dict[str, Any]:
    spec = load_campaign(path)
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise CampaignError(f"refusing to overwrite nonempty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(spec.path, output / "campaign.toml")
    plan = plan_campaign(spec.path)
    _write_json(output / "campaign-plan.json", plan)
    _append_event(
        output,
        {
            "event": "campaign_started",
            "campaign_id": spec.campaign_id,
            "manifest_sha256": _digest(output / "campaign.toml"),
            "cell_count": plan["cell_count"],
        },
    )
    return _execute(spec, output)


def resume_campaign(output: Path) -> dict[str, Any]:
    output = output.resolve()
    manifest = output / "campaign.toml"
    if not manifest.is_file():
        raise CampaignError(f"campaign snapshot does not exist: {manifest}")
    spec = load_campaign(manifest)
    events = _read_ledger(output)
    started = next(
        (item for item in events if item.get("event") == "campaign_started"), None
    )
    if started is None or started.get("manifest_sha256") != _digest(manifest):
        raise CampaignError("campaign snapshot does not match its ledger")
    _append_event(output, {"event": "campaign_resumed"})
    return _execute(spec, output)


def replay_campaign(
    output: Path, *, cell: str, attempt: int | None = None
) -> dict[str, Any]:
    output = output.resolve()
    spec = load_campaign(output / "campaign.toml")
    candidates = [
        item
        for item in _read_ledger(output)
        if item.get("event") == "attempt_completed" and item.get("cell") == cell
    ]
    if attempt is not None:
        candidates = [item for item in candidates if item.get("attempt") == attempt]
    if not candidates:
        suffix = f" attempt {attempt}" if attempt is not None else ""
        raise CampaignError(f"no completed record for cell {cell!r}{suffix}")
    source = max(candidates, key=lambda item: int(item["attempt"]))
    response = _inside(output, str(source["response_path"]))
    prompt_path = _inside(output, str(source["prompt_path"]))
    prompt = prompt_path.read_text(encoding="utf-8")
    if _digest(response) != source["response_sha256"]:
        raise CampaignError("saved response digest does not match the ledger")
    if _digest(prompt_path) != source["prompt_sha256"]:
        raise CampaignError("saved prompt digest does not match the ledger")
    original_report_path = _inside(output, str(source["report_path"]))
    if _digest(original_report_path) != source["report_sha256"]:
        raise CampaignError("saved report digest does not match the ledger")
    task = str(source["task"])
    replay_index = 1
    replay_base = output / "replays" / _safe_cell(cell) / f"attempt-{source['attempt']:02d}"
    while (replay_base / f"replay-{replay_index:02d}").exists():
        replay_index += 1
    replay_root = replay_base / f"replay-{replay_index:02d}"
    manifest = materialize_candidate(
        spec.taskpack_root / "tasks" / task,
        response,
        spec.label,
        replay_root,
        "exact-replay",
        prompt_level=spec.prompt_level,
        prompt_override=prompt,
    )
    if _digest(manifest.parent / "design.sv") != source["design_sha256"]:
        raise CampaignError("replayed response did not reproduce the saved design digest")
    report = evaluate(
        manifest,
        manifest_label=manifest.relative_to(output).as_posix(),
    ).to_dict()
    original = json.loads(original_report_path.read_text(encoding="utf-8"))
    matches = _result_signature(report) == _result_signature(original)
    result = {
        "schema_version": "1.0",
        "campaign_id": spec.campaign_id,
        "cell": cell,
        "attempt": source["attempt"],
        "response_sha256": source["response_sha256"],
        "result_matches": matches,
        "original_signature": _result_signature(original),
        "replay_signature": _result_signature(report),
        "report_path": manifest.parent.joinpath("report.json").relative_to(output).as_posix(),
    }
    _write_json(replay_root / "replay-result.json", result)
    _append_event(output, {"event": "replay_completed", **result})
    return result


def _execute(spec: CampaignSpec, output: Path) -> dict[str, Any]:
    events = _read_ledger(output)
    completed = {
        str(item["cell"])
        for item in events
        if item.get("event") == "cell_completed"
    }
    calls = sum(item.get("event") == "attempt_started" for item in events)
    elapsed = sum(
        float(item.get("duration_seconds", 0))
        for item in events
        if item.get("event") in {"attempt_completed", "attempt_failed"}
    )
    stopped_reason: str | None = None
    with tempfile.TemporaryDirectory(prefix="svgap-campaign-") as directory:
        sandbox = Path(directory)
        for cell in _cells(spec):
            cell_id = str(cell["cell"])
            if cell_id in completed:
                continue
            cell_events = [
                item
                for item in events
                if item.get("event") == "attempt_completed"
                and item.get("cell") == cell_id
            ]
            previous = max(cell_events, key=lambda item: int(item["attempt"]), default=None)
            started_attempts = {
                int(item["attempt"])
                for item in events
                if item.get("event") == "attempt_started"
                and item.get("cell") == cell_id
            }
            settled_attempts = {
                int(item["attempt"])
                for item in events
                if item.get("event")
                in {"attempt_completed", "attempt_failed", "attempt_abandoned"}
                and item.get("cell") == cell_id
            }
            for abandoned in sorted(started_attempts - settled_attempts):
                event = {
                    "event": "attempt_abandoned",
                    "cell": cell_id,
                    "task": cell["task"],
                    "sample": cell["sample"],
                    "attempt": abandoned,
                    "error": "attempt was interrupted before a terminal ledger record",
                }
                _append_event(output, event)
                events.append(event)
            attempt = max(started_attempts, default=0) + 1
            if previous and previous.get("contract_status") == "closed":
                _complete_cell(output, cell_id, "closed", int(previous["attempt"]))
                completed.add(cell_id)
                continue
            if attempt > spec.max_attempts:
                _complete_cell(output, cell_id, "attempts_exhausted", attempt - 1)
                completed.add(cell_id)
                continue
            while attempt <= spec.max_attempts:
                if spec.max_model_calls is not None and calls >= spec.max_model_calls:
                    stopped_reason = "model_call_budget"
                    break
                if spec.wall_seconds is not None and elapsed >= spec.wall_seconds:
                    stopped_reason = "wall_time_budget"
                    break
                task_dir = spec.taskpack_root / "tasks" / str(cell["task"])
                original_path, resolved_level = resolve_prompt(
                    task_dir, load_task(task_dir), spec.prompt_level
                )
                original_prompt = original_path.read_text(encoding="utf-8")
                prompt = (
                    original_prompt
                    if previous is None
                    else _repair_prompt(
                        original_prompt,
                        _inside(output, str(previous["design_path"])).read_text(
                            encoding="utf-8"
                        ),
                        json.loads(
                            _inside(output, str(previous["report_path"])).read_text(
                                encoding="utf-8"
                            )
                        ),
                        spec.feedback,
                    )
                )
                phase = "initial" if previous is None else "repair"
                seed = _attempt_seed(spec, cell_id, attempt)
                response_path, prompt_path = _prepare_generation(
                    output, cell_id, attempt, prompt
                )
                _append_event(
                    output,
                    {
                        "event": "attempt_started",
                        "cell": cell_id,
                        "task": cell["task"],
                        "sample": cell["sample"],
                        "attempt": attempt,
                        "phase": phase,
                        "feedback": None if previous is None else spec.feedback,
                        "seed": seed,
                        "prompt_path": prompt_path.relative_to(output).as_posix(),
                        "prompt_sha256": _digest(prompt_path),
                    },
                )
                calls += 1
                started = time.monotonic()
                try:
                    response_text = _run_generator(
                        spec.command,
                        prompt,
                        sandbox,
                        spec.timeout_seconds,
                        {
                            "SVGAP_CAMPAIGN_ID": spec.campaign_id,
                            "SVGAP_CAMPAIGN_CELL": cell_id,
                            "SVGAP_CAMPAIGN_ATTEMPT": str(attempt),
                            "SVGAP_CAMPAIGN_SEED": str(seed),
                        },
                    )
                    response_path.write_text(response_text, encoding="utf-8")
                    run_id = f"{spec.label}--sample-{int(cell['sample']):02d}"
                    attempt_root = output / "attempts" / f"attempt-{attempt:02d}"
                    manifest = materialize_candidate(
                        task_dir,
                        response_path,
                        spec.label,
                        attempt_root,
                        run_id,
                        prompt_level=resolved_level,
                        prompt_override=prompt,
                    )
                    report = evaluate(
                        manifest,
                        manifest_label=manifest.relative_to(output).as_posix(),
                    ).to_dict()
                    contract_status = report.get(
                        "contract_status"
                    ) or derive_contract_status(report)
                    generation_metadata = {
                        "schema_version": "1.0",
                        "campaign_id": spec.campaign_id,
                        "provider": "command",
                        "interface_version": spec.interface_label,
                        "configuration_label": spec.label,
                        "command": [spec.command],
                        "cell": cell_id,
                        "sample": cell["sample"],
                        "task": cell["task"],
                        "attempt": attempt,
                        "phase": phase,
                        "feedback": None if previous is None else spec.feedback,
                        "seed": seed,
                    }
                    _write_json(manifest.parent / "generation.json", generation_metadata)
                    report_path = manifest.parent / "report.json"
                    duration = time.monotonic() - started
                    event = {
                        "event": "attempt_completed",
                        "cell": cell_id,
                        "task": cell["task"],
                        "sample": cell["sample"],
                        "attempt": attempt,
                        "phase": phase,
                        "feedback": None if previous is None else spec.feedback,
                        "seed": seed,
                        "duration_seconds": round(duration, 6),
                        "prompt_path": prompt_path.relative_to(output).as_posix(),
                        "prompt_sha256": _digest(prompt_path),
                        "response_path": response_path.relative_to(output).as_posix(),
                        "response_sha256": _digest(response_path),
                        "manifest_path": manifest.relative_to(output).as_posix(),
                        "design_path": manifest.parent.joinpath("design.sv")
                        .relative_to(output)
                        .as_posix(),
                        "design_sha256": _digest(manifest.parent / "design.sv"),
                        "report_path": report_path.relative_to(output).as_posix(),
                        "report_sha256": _digest(report_path),
                        "functional_status": report["functional"]["status"],
                        "contract_status": contract_status,
                        "gap_member": report["gap_member"],
                    }
                    _append_event(output, event)
                    events.append(event)
                    previous = event
                    elapsed += duration
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    duration = time.monotonic() - started
                    failed = {
                        "event": "attempt_failed",
                        "cell": cell_id,
                        "task": cell["task"],
                        "sample": cell["sample"],
                        "attempt": attempt,
                        "phase": phase,
                        "feedback": None if previous is None else spec.feedback,
                        "seed": seed,
                        "duration_seconds": round(duration, 6),
                        "error": str(exc),
                    }
                    _append_event(output, failed)
                    events.append(failed)
                    elapsed += duration
                    _complete_cell(output, cell_id, "generation_error", attempt)
                    completed.add(cell_id)
                    break
                if previous["contract_status"] == "closed":
                    _complete_cell(output, cell_id, "closed", attempt)
                    completed.add(cell_id)
                    break
                if not spec.repair_enabled or attempt >= spec.max_attempts:
                    _complete_cell(output, cell_id, "attempts_exhausted", attempt)
                    completed.add(cell_id)
                    break
                attempt += 1
            if stopped_reason:
                break
    if stopped_reason:
        _append_event(output, {"event": "campaign_stopped", "reason": stopped_reason})
    elif len(completed) == len(_cells(spec)) and not any(
        item.get("event") == "campaign_completed" for item in events
    ):
        _append_event(output, {"event": "campaign_completed"})
    return _write_summary(output, spec, stopped_reason)


def _repair_prompt(
    original: str, candidate: str, report: dict[str, Any], feedback: str
) -> str:
    findings = [
        {
            "oracle_id": oracle["oracle_id"],
            "rule_id": finding["rule_id"],
            "message": finding["message"],
        }
        for oracle in normalized_oracle_results(report)
        for finding in oracle.get("findings", [])
    ]
    payload: dict[str, Any] = {
        "functional_status": report["functional"]["status"],
        "contract_status": report.get("contract_status")
        or derive_contract_status(report),
        "findings": findings,
    }
    if feedback in {"diagnostic", "full"}:
        payload["functional_stderr"] = report["functional"].get("stderr", "")[-4000:]
        payload["oracles"] = [
            {
                "oracle_id": item["oracle_id"],
                "status": item["status"],
                "diagnostics": item.get("diagnostics", []),
                "observed_coverage": item.get("coverage", {}).get("observed", {}),
            }
            for item in normalized_oracle_results(report)
        ]
    if feedback == "full":
        payload["report"] = report
    return (
        original.rstrip()
        + "\n\nRepair the candidate below using only the evaluation feedback. "
        "Return one complete SystemVerilog module and no explanation.\n\n"
        + "Candidate:\n```systemverilog\n"
        + candidate.rstrip()
        + "\n```\n\nEvaluation feedback:\n```json\n"
        + json.dumps(payload, indent=2, sort_keys=True)
        + "\n```\n"
    )


def _run_generator(
    command: str,
    prompt: str,
    sandbox: Path,
    timeout: int,
    environment: dict[str, str],
) -> str:
    process_environment = os.environ.copy()
    process_environment.update(environment)
    completed = subprocess.run(
        command,
        shell=True,
        input=prompt,
        cwd=sandbox,
        env=process_environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        raise subprocess.SubprocessError(
            completed.stderr[-4000:].strip()
            or f"generation command exited {completed.returncode} with no stderr"
        )
    if not completed.stdout.strip():
        raise subprocess.SubprocessError("generation command produced empty stdout")
    return completed.stdout


def _prepare_generation(
    output: Path, cell: str, attempt: int, prompt: str
) -> tuple[Path, Path]:
    root = output / "generations" / _safe_cell(cell) / f"attempt-{attempt:02d}"
    root.mkdir(parents=True, exist_ok=True)
    response_path = root / "response.txt"
    prompt_path = root / "prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return response_path, prompt_path


def _write_summary(
    output: Path, spec: CampaignSpec, stopped_reason: str | None
) -> dict[str, Any]:
    events = _read_ledger(output)
    attempts = [item for item in events if item.get("event") == "attempt_completed"]
    cells = [item for item in events if item.get("event") == "cell_completed"]
    statuses = Counter(str(item.get("contract_status")) for item in attempts)
    summary = {
        "schema_version": "1.0",
        "campaign_id": spec.campaign_id,
        "cell_count": len(_cells(spec)),
        "completed_cells": len({item["cell"] for item in cells}),
        "model_calls": sum(item.get("event") == "attempt_started" for item in events),
        "elapsed_seconds": round(
            sum(
                float(item.get("duration_seconds", 0))
                for item in events
                if item.get("event") in {"attempt_completed", "attempt_failed"}
            ),
            6,
        ),
        "successful_attempts": len(attempts),
        "repair_attempts": sum(item.get("phase") == "repair" for item in attempts),
        "contract_statuses": dict(sorted(statuses.items())),
        "closed_cells": sum(item.get("reason") == "closed" for item in cells),
        "stopped_reason": stopped_reason,
        "ledger": str(output / "campaign-ledger.jsonl"),
    }
    _write_json(output / "campaign-summary.json", summary)
    return summary


def _complete_cell(output: Path, cell: str, reason: str, attempt: int) -> None:
    _append_event(
        output,
        {"event": "cell_completed", "cell": cell, "reason": reason, "attempt": attempt},
    )


def _cells(spec: CampaignSpec) -> list[dict[str, Any]]:
    return [
        {"cell": f"sample-{sample:02d}/{task}", "sample": sample, "task": task}
        for sample in range(1, spec.samples + 1)
        for task in spec.tasks
    ]


def _attempt_seed(spec: CampaignSpec, cell: str, attempt: int) -> int:
    material = f"{spec.base_seed}:{spec.campaign_id}:{cell}:{attempt}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big") & 0x7FFFFFFF


def _append_event(output: Path, fields: dict[str, Any]) -> None:
    path = output / "campaign-ledger.jsonl"
    records = _read_ledger(output)
    event = {
        "schema_version": "1.0",
        "sequence": len(records) + 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "previous_record_sha256": (
            records[-1]["record_sha256"] if records else None
        ),
        **fields,
    }
    event["record_sha256"] = _object_digest(event)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_ledger(output: Path) -> list[dict[str, Any]]:
    path = output / "campaign-ledger.jsonl"
    if not path.is_file():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CampaignError(f"invalid campaign ledger line {number}: {exc}") from exc
        if item.get("sequence") != number:
            raise CampaignError(f"campaign ledger sequence mismatch on line {number}")
        claimed = item.get("record_sha256")
        unsigned = dict(item)
        unsigned.pop("record_sha256", None)
        if claimed != _object_digest(unsigned):
            raise CampaignError(f"campaign ledger digest mismatch on line {number}")
        previous = records[-1]["record_sha256"] if records else None
        if item.get("previous_record_sha256") != previous:
            raise CampaignError(f"campaign ledger chain mismatch on line {number}")
        records.append(item)
    return records


def _result_signature(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "functional": report.get("functional", {}).get("status"),
        "gap_member": report.get("gap_member"),
        "contract_status": report.get("contract_status"),
        "oracles": [
            {
                "id": item.get("oracle_id"),
                "status": item.get("status"),
                "findings": [
                    (finding.get("rule_id"), finding.get("severity"), finding.get("message"))
                    for finding in item.get("findings", [])
                ],
                "observed_coverage": item.get("coverage", {}).get("observed", {}),
            }
            for item in report.get("oracle_results", [])
        ],
    }


def _resolve_taskpack(manifest: Path, value: str) -> Path:
    if value in TASKPACKS:
        try:
            return taskpack_root(value)
        except ResourceError as exc:
            raise CampaignError(str(exc)) from exc
    relative = Path(value)
    if relative.is_absolute():
        candidate = relative.resolve()
    else:
        candidate = (manifest.parent / relative).resolve()
    if not (candidate / "tasks").is_dir() or not (candidate / "freeze.json").is_file():
        plan_path = manifest.parent / "campaign-plan.json"
        if plan_path.is_file():
            try:
                planned = Path(
                    json.loads(plan_path.read_text(encoding="utf-8"))["taskpack_path"]
                ).resolve()
            except (OSError, KeyError, TypeError, json.JSONDecodeError):
                planned = candidate
            if (planned / "tasks").is_dir() and (planned / "freeze.json").is_file():
                return planned
        raise CampaignError(
            f"taskpack must name a packaged id or a path containing freeze.json and tasks/: {value}"
        )
    return candidate


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise CampaignError(f"ledger path escapes campaign output: {relative}")
    return path


def _safe_cell(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "--", value).strip("-") or "cell"


def _table(payload: dict[str, Any], key: str, *, required: bool = False) -> dict[str, Any]:
    value = payload.get(key)
    if value is None and not required:
        return {}
    if not isinstance(value, dict):
        raise CampaignError(f"campaign {key} must be a table")
    return value


def _only_fields(value: dict[str, Any], table: str, allowed: set[str]) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise CampaignError(f"unsupported {table} fields: {', '.join(extras)}")


def _positive_int(value: Any, field: str) -> int:
    return _bounded_int(value, field, 1, 1_000_000)


def _optional_positive_int(value: Any, field: str) -> int | None:
    return None if value is None else _positive_int(value, field)


def _bounded_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise CampaignError(f"{field} must be an integer from {minimum} through {maximum}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
