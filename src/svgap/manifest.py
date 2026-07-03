from __future__ import annotations

import tomllib
import re
from pathlib import Path
from typing import Any

from svgap.model import ClockIntent, CrossingIntent, Manifest, ResetIntent


class ManifestError(ValueError):
    pass


def _required(table: dict[str, Any], key: str, context: str) -> Any:
    if key not in table:
        raise ManifestError(f"missing {context}.{key}")
    return table[key]


def load_manifest(path: str | Path) -> Manifest:
    manifest_path = Path(path).resolve()
    try:
        raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"cannot read {manifest_path}: {exc}") from exc

    base = manifest_path.parent
    design = _required(raw, "design", "manifest")
    functional = raw.get("functional", {})
    structural = _required(raw, "structural", "manifest")
    intent = _required(raw, "intent", "manifest")
    output = raw.get("output", {})
    schema_version = str(_required(raw, "schema_version", "manifest"))
    if schema_version != "1.0":
        raise ManifestError(f"unsupported schema_version: {schema_version!r}")

    source_values = [Path(item) for item in _required(design, "sources", "design")]
    if any(item.is_absolute() for item in source_values):
        raise ManifestError("design.sources must be relative to the manifest directory")
    sources = [(base / item).resolve() for item in source_values]
    if any(not item.is_relative_to(base.resolve()) for item in sources):
        raise ManifestError("design.sources must remain inside the manifest directory")
    missing = [str(item) for item in sources if not item.is_file()]
    if missing:
        raise ManifestError(f"source files do not exist: {', '.join(missing)}")

    commands = functional.get("commands", [])
    if not isinstance(commands, list) or any(
        not isinstance(command, list) or not all(isinstance(x, str) for x in command)
        for command in commands
    ):
        raise ManifestError("functional.commands must be an array of string arrays")

    clocks = [ClockIntent(**item) for item in intent.get("clocks", [])]
    resets = [ResetIntent(**item) for item in intent.get("resets", [])]
    crossings = [CrossingIntent(**item) for item in intent.get("crossings", [])]

    top = str(_required(design, "top", "design"))
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top) is None:
        raise ManifestError(f"design.top is not a supported Verilog identifier: {top!r}")

    report_value = Path(output.get("report", "build/report.json"))
    if report_value.is_absolute():
        raise ManifestError("output.report must be relative to the manifest directory")
    report_path = (base / report_value).resolve()
    if not report_path.is_relative_to(base.resolve()):
        raise ManifestError("output.report must remain inside the manifest directory")

    return Manifest(
        path=manifest_path,
        schema_version=schema_version,
        candidate_id=str(_required(raw, "candidate_id", "manifest")),
        top=top,
        sources=sources,
        functional_commands=commands,
        clocks=clocks,
        asynchronous_groups=[list(group) for group in intent.get("asynchronous_groups", [])],
        resets=resets,
        crossings=crossings,
        backend=str(structural.get("backend", "reference-yosys")),
        report_path=report_path,
    )
