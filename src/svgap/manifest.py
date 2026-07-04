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

    if not isinstance(design, dict) or not isinstance(functional, dict):
        raise ManifestError("design and functional sections must be tables")
    if not isinstance(structural, dict) or not isinstance(intent, dict):
        raise ManifestError("structural and intent sections must be tables")
    if not isinstance(output, dict):
        raise ManifestError("output section must be a table")

    source_items = _required(design, "sources", "design")
    if not isinstance(source_items, list) or not source_items or not all(
        isinstance(item, str) and item for item in source_items
    ):
        raise ManifestError("design.sources must be a nonempty array of relative paths")
    source_values = [Path(item) for item in source_items]
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

    import_value = functional.get("import")
    if import_value is not None and not isinstance(import_value, str):
        raise ManifestError("functional.import must be a relative path string")
    if commands and import_value is not None:
        raise ManifestError("functional.commands and functional.import are mutually exclusive")
    functional_import = None
    if import_value is not None:
        import_path = Path(import_value)
        if import_path.is_absolute():
            raise ManifestError("functional.import must be relative to the manifest directory")
        functional_import = (base / import_path).resolve()
        if not functional_import.is_relative_to(base.resolve()):
            raise ManifestError("functional.import must remain inside the manifest directory")
        if not functional_import.is_file():
            raise ManifestError(f"functional import does not exist: {functional_import}")

    clocks_raw = _table_array(intent, "clocks")
    resets_raw = _table_array(intent, "resets")
    crossings_raw = _table_array(intent, "crossings")
    try:
        clocks = [ClockIntent(**item) for item in clocks_raw]
        resets = [ResetIntent(**item) for item in resets_raw]
        crossings = [CrossingIntent(**item) for item in crossings_raw]
    except TypeError as exc:
        raise ManifestError(f"invalid intent record: {exc}") from exc
    if len({clock.name for clock in clocks}) != len(clocks):
        raise ManifestError("intent clock names must be unique")
    if len({reset.name for reset in resets}) != len(resets):
        raise ManifestError("intent reset names must be unique")
    if any(reset.active not in ("high", "low") for reset in resets):
        raise ManifestError("intent reset active must be 'high' or 'low'")
    if any(reset.assertion not in ("async", "sync") for reset in resets):
        raise ManifestError("intent reset assertion must be 'async' or 'sync'")
    if any(reset.deassertion not in ("async", "sync") for reset in resets):
        raise ManifestError("intent reset deassertion must be 'async' or 'sync'")
    if any(
        crossing.protocol not in ("single_bit", "gray", "handshake", "unspecified")
        for crossing in crossings
    ):
        raise ManifestError("intent crossing protocol is unsupported")
    groups = intent.get("asynchronous_groups", [])
    if not isinstance(groups, list) or any(
        not isinstance(group, list)
        or not group
        or not all(isinstance(name, str) and name for name in group)
        for group in groups
    ):
        raise ManifestError("intent.asynchronous_groups must be an array of nonempty string arrays")

    top = str(_required(design, "top", "design"))
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top) is None:
        raise ManifestError(f"design.top is not a supported Verilog identifier: {top!r}")

    report_value = Path(output.get("report", "build/report.json"))
    if report_value.is_absolute():
        raise ManifestError("output.report must be relative to the manifest directory")
    report_path = (base / report_value).resolve()
    if not report_path.is_relative_to(base.resolve()):
        raise ManifestError("output.report must remain inside the manifest directory")

    candidate_id = str(_required(raw, "candidate_id", "manifest"))
    if not candidate_id.strip():
        raise ManifestError("candidate_id must be nonempty")

    return Manifest(
        path=manifest_path,
        schema_version=schema_version,
        candidate_id=candidate_id,
        top=top,
        sources=sources,
        functional_commands=commands,
        functional_import=functional_import,
        clocks=clocks,
        asynchronous_groups=[list(group) for group in groups],
        resets=resets,
        crossings=crossings,
        backend=str(structural.get("backend", "reference-yosys")),
        report_path=report_path,
    )


def _table_array(table: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = table.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ManifestError(f"intent.{key} must be an array of tables")
    return value
