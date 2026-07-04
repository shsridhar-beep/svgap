from __future__ import annotations

import json
import re
from pathlib import Path

from svgap.model import Manifest


def render_manifest_draft(source: Path, top: str, candidate_id: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top) is None:
        raise ValueError("top must be a supported Verilog identifier")
    if not candidate_id.strip():
        raise ValueError("candidate_id must be nonempty")
    if source.is_absolute() or ".." in source.parts:
        raise ValueError("source must be a path inside the manifest directory")
    return f'''# SV-Gap draft: intent is deliberately not inferred.
# Add functional.commands or functional.import before interpreting functionality.
# Declare clocks, resets, and asynchronous groups before interpreting structure.
schema_version = "1.0"
candidate_id = {json.dumps(candidate_id)}

[design]
top = {json.dumps(top)}
sources = [{json.dumps(source.as_posix())}]

[functional]
commands = []

[structural]
backend = "reference-yosys"

[intent]
asynchronous_groups = []

[output]
report = "build/report.json"
'''


def manifest_readiness(manifest: Manifest) -> dict[str, object]:
    answered = []
    unanswered = []
    if manifest.functional_commands or manifest.functional_import is not None:
        answered.append("functional evidence source declared")
    else:
        unanswered.append("functional evidence source is not declared")
    if manifest.clocks:
        answered.append(f"{len(manifest.clocks)} clock declaration(s)")
    else:
        unanswered.append("clock intent is not declared")
    if manifest.resets:
        answered.append(f"{len(manifest.resets)} reset declaration(s)")
    if len(manifest.clocks) > 1 and not manifest.asynchronous_groups:
        unanswered.append("multiple clocks lack an explicit relationship")
    return {
        "candidate_id": manifest.candidate_id,
        "status": "ready" if not unanswered else "incomplete",
        "answered": answered,
        "unanswered": unanswered,
    }
