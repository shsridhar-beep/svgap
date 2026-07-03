from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def canonical_file_set_digest(
    root: Path, paths: Iterable[Path], *, algorithm: str = "sha256"
) -> str:
    """Hash relative names and file bytes without depending on checkout location."""
    root = root.resolve()
    digest = hashlib.new(algorithm)
    normalized = sorted(
        ((path.resolve().relative_to(root).as_posix(), path.resolve()) for path in paths),
        key=lambda item: item[0],
    )
    for relative, path in normalized:
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        digest.update(b"\0")
    return f"{algorithm}:{digest.hexdigest()}"


def canonical_tree_digest(root: Path, *, exclude_names: set[str] | None = None) -> str:
    excluded = exclude_names or set()
    return canonical_file_set_digest(
        root,
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.name not in excluded
        ),
    )
