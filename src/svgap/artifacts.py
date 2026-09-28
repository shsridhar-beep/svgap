from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def artifact_record(path: Path, root: Path, *, kind: str) -> dict[str, Any]:
    """Describe an emitted artifact without embedding machine-specific paths."""

    content = path.read_bytes()
    try:
        portable = str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        portable = str(path.resolve())
    return {
        "path": portable,
        "kind": kind,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def existing_artifacts(
    root: Path, **paths: tuple[Path, str]
) -> dict[str, dict[str, Any]]:
    return {
        name: artifact_record(path, root, kind=kind)
        for name, (path, kind) in paths.items()
        if path.is_file()
    }
