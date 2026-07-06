"""Locate frozen taskpacks and challenges in a checkout or installed wheel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ResourceError(ValueError):
    pass


TASKPACKS: dict[str, dict[str, Any]] = {
    "reset-release-v0.2": {
        "directory": "reset-replication-v0.2",
        "version": "0.2",
        "smoke_task": "reset_counter",
        "full_samples": 3,
    }
}


def taskpack_root(identifier: str) -> Path:
    try:
        directory = TASKPACKS[identifier]["directory"]
    except KeyError as exc:
        raise ResourceError(
            f"unknown taskpack {identifier!r}; available: {', '.join(TASKPACKS)}"
        ) from exc
    candidates = (
        Path(__file__).resolve().parents[2] / "taskpacks" / directory,
        Path(__file__).resolve().parent / "resources/taskpacks" / directory,
    )
    for candidate in candidates:
        if (candidate / "freeze.json").is_file():
            return candidate
    raise ResourceError(
        f"taskpack {identifier!r} is missing from this installation; reinstall SV-Gap"
    )


def challenge_root(version: str = "v0.1") -> Path:
    candidates = (
        Path(__file__).resolve().parents[2] / "challenges" / version,
        Path(__file__).resolve().parent / "resources/challenges" / version,
    )
    for candidate in candidates:
        if (candidate / "diagnosis/task.json").is_file():
            return candidate
    raise ResourceError(
        f"challenge {version!r} is missing from this installation; reinstall SV-Gap"
    )


def taskpack_metadata(identifier: str) -> dict[str, Any]:
    root = taskpack_root(identifier)
    freeze = json.loads((root / "freeze.json").read_text(encoding="utf-8"))
    tasks = sorted(path.name for path in (root / "tasks").iterdir() if path.is_dir())
    return {
        "id": identifier,
        "version": TASKPACKS[identifier]["version"],
        "canonical_digest": freeze["canonical_digest"],
        "smoke_task": TASKPACKS[identifier]["smoke_task"],
        "full_samples": TASKPACKS[identifier]["full_samples"],
        "tasks": tasks,
        "path": str(root),
    }


def taskpack_prompt_digest(identifier: str, task: str) -> str:
    path = taskpack_root(identifier) / "tasks" / task / "prompt.md"
    if not path.is_file():
        raise ResourceError(f"task {task!r} is not in taskpack {identifier!r}")
    return hashlib.sha256(path.read_bytes()).hexdigest()
