#!/usr/bin/env python3
"""Run a small, explicit model-configuration pilot.

This is an experimental convenience wrapper, not part of the evaluator core.
It disables model tools and evaluates each final response through `svgap pilot`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_ROOT = ROOT / "taskpacks/pilot-v0.1/tasks"
DEFAULT_TASKS = (
    "level_crossing",
    "comb_crossing",
    "gray_counter",
    "reset_release",
    "mode_crossing",
    "alarm_crossing",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=("codex", "claude"))
    parser.add_argument("--model", help="provider model name; omit for provider default")
    parser.add_argument("--label", required=True, help="stable configuration label")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--tasks", nargs="+", default=list(DEFAULT_TASKS))
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/generated/pilot-v0.1"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if args.samples < 1:
        parser.error("--samples must be positive")
    task_root = args.task_root.resolve()
    interface_version = provider_version(args.provider)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="svgap-model-") as sandbox:
        for sample in range(1, args.samples + 1):
            for task_name in args.tasks:
                run_id = f"{args.label}--sample-{sample:02d}"
                response_dir = output / "_responses" / run_id
                response_dir.mkdir(parents=True, exist_ok=True)
                task_dir = task_root / task_name
                prompt = (task_dir / "prompt.md").read_text(encoding="utf-8")
                try:
                    response, command = generate(
                        args.provider, args.model, prompt, Path(sandbox)
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    print(
                        f"GENERATION_ERROR {args.label}/{task_name}: {exc}",
                        file=sys.stderr,
                    )
                    failures += 1
                    continue
                response_path = response_dir / f"{task_name}.txt"
                response_path.write_text(response, encoding="utf-8")
                metadata = {
                    "schema_version": "1.0",
                    "provider": args.provider,
                    "interface_version": interface_version,
                    "requested_model": args.model,
                    "configuration_label": args.label,
                    "sample": sample,
                    "task": task_name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "command": command,
                }
                metadata_payload = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
                response_path.with_suffix(".generation.json").write_text(
                    metadata_payload, encoding="utf-8"
                )
                evaluated = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "svgap",
                        "pilot",
                        str(task_dir),
                        str(response_path),
                        "--model",
                        args.model or args.label,
                        "--run-id",
                        run_id,
                        "--output",
                        str(output),
                    ],
                    cwd=ROOT,
                    check=False,
                    text=True,
                )
                if evaluated.returncode == 2:
                    failures += 1
                run_dir = output / run_id / task_name
                if run_dir.is_dir():
                    (run_dir / "generation.json").write_text(
                        metadata_payload, encoding="utf-8"
                    )
    return 2 if failures else 0


def generate(
    provider: str, model: str | None, prompt: str, sandbox: Path
) -> tuple[str, list[str]]:
    if provider == "codex":
        binary = require_executable("codex")
        output = sandbox / "last-message.txt"
        command = [
            binary,
            "--ask-for-approval",
            "never",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--cd",
            str(sandbox),
            "--output-last-message",
            str(output),
        ]
        if model:
            command.extend(["--model", model])
        command.append(prompt)
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=600, check=False
        )
        if completed.returncode:
            raise subprocess.SubprocessError(completed.stderr[-4000:])
        return output.read_text(encoding="utf-8"), redact_command(command)

    binary = require_executable("claude")
    command = [
        binary,
        "--print",
        "--bare",
        "--tools",
        "",
        "--no-session-persistence",
    ]
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    completed = subprocess.run(
        command,
        cwd=sandbox,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if completed.returncode:
        raise subprocess.SubprocessError(completed.stderr[-4000:])
    return completed.stdout, redact_command(command)


def redact_command(command: list[str]) -> list[str]:
    redacted = command.copy()
    if redacted:
        redacted[-1] = "<PROMPT_FROM_TASKPACK>"
    return redacted


def provider_version(provider: str) -> str:
    binary = require_executable("codex" if provider == "codex" else "claude")
    completed = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, timeout=30, check=False
    )
    return (completed.stdout.strip() or completed.stderr.strip() or "unknown").splitlines()[-1]


def require_executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise OSError(f"required provider CLI is not on PATH: {name}")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
