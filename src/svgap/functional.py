from __future__ import annotations

import os
import hashlib
import json
import subprocess
from pathlib import Path

from svgap.model import FunctionalResult, Manifest
from svgap.provenance import canonical_file_set_digest


def run_functional(manifest: Manifest) -> FunctionalResult:
    if manifest.functional_import is not None:
        return import_functional_result(manifest)
    versions = {
        "iverilog": command_version(["iverilog", "-V"]),
        "vvp": command_version(["vvp", "-V"]),
    }
    if not manifest.functional_commands:
        return FunctionalResult(
            status="unknown",
            stderr="no functional commands declared",
            tool_versions=versions,
        )

    build = manifest.path.parent / "build"
    build.mkdir(parents=True, exist_ok=True)
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    returncodes: list[int] = []
    allowed_environment = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT")
    env = {key: os.environ[key] for key in allowed_environment if key in os.environ}
    env["SVGAP_BUILD"] = str(build)

    for command in manifest.functional_commands:
        expanded = [item.replace("${SVGAP_BUILD}", str(build)) for item in command]
        try:
            completed = subprocess.run(
                expanded,
                cwd=manifest.path.parent,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FunctionalResult(
                status="tool_error",
                commands=manifest.functional_commands,
                returncodes=returncodes,
                stdout="\n".join(stdout_parts),
                stderr="\n".join([*stderr_parts, str(exc)]),
                tool_versions=versions,
            )
        returncodes.append(completed.returncode)
        stdout_parts.append(completed.stdout)
        stderr_parts.append(completed.stderr)
        if completed.returncode != 0:
            executable = Path(expanded[0]).name.lower()
            status = (
                "compile_error"
                if executable in ("iverilog", "verilator", "slang", "verible-verilog-syntax")
                else "fail"
            )
            return FunctionalResult(
                status=status,
                commands=manifest.functional_commands,
                returncodes=returncodes,
                stdout="\n".join(stdout_parts),
                stderr="\n".join(stderr_parts),
                tool_versions=versions,
            )

    return FunctionalResult(
        status="pass",
        commands=manifest.functional_commands,
        returncodes=returncodes,
        stdout="\n".join(stdout_parts),
        stderr="\n".join(stderr_parts),
        tool_versions=versions,
    )


def import_functional_result(manifest: Manifest) -> FunctionalResult:
    path = manifest.functional_import
    if path is None:
        raise ValueError("manifest does not declare a functional import")
    base = manifest.path.parent
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return FunctionalResult(
            status="tool_error",
            stderr=f"cannot import functional result: {exc}",
            imported_from=str(path.relative_to(base)),
        )
    allowed = {"pass", "fail", "compile_error", "unknown", "tool_error"}
    status = payload.get("status")
    if payload.get("schema_version") != "1.0" or status not in allowed:
        return FunctionalResult(
            status="tool_error",
            stderr="imported functional result has an unsupported schema or status",
            imported_from=str(path.relative_to(base)),
        )
    producer = payload.get("producer")
    candidate_digest = payload.get("candidate_digest")
    expected_digest = canonical_file_set_digest(base, manifest.sources)
    if not isinstance(producer, str) or not producer.strip():
        return FunctionalResult(
            status="tool_error",
            stderr="imported functional result must identify its producer",
            imported_from=str(path.relative_to(base)),
        )
    if candidate_digest != expected_digest:
        return FunctionalResult(
            status="tool_error",
            stderr=(
                "imported functional result candidate_digest does not match "
                f"the manifest sources (expected {expected_digest})"
            ),
            imported_from=str(path.relative_to(base)),
        )
    tool_versions = payload.get("tool_versions", {})
    evidence = payload.get("evidence", {})
    if not isinstance(tool_versions, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in tool_versions.items()
    ):
        return FunctionalResult(
            status="tool_error",
            stderr="imported functional result tool_versions must map strings to strings",
            imported_from=str(path.relative_to(base)),
        )
    if not isinstance(evidence, dict):
        return FunctionalResult(
            status="tool_error",
            stderr="imported functional result evidence must be an object",
            imported_from=str(path.relative_to(base)),
        )
    evidence = dict(evidence)
    evidence["import_sha256"] = hashlib.sha256(raw).hexdigest()
    for key in ("producer", "observed_at", "candidate_digest"):
        if key in payload:
            evidence[key] = payload[key]
    return FunctionalResult(
        status=status,
        stdout=str(payload.get("summary", "")),
        tool_versions=tool_versions,
        imported_from=str(path.relative_to(base)),
        evidence=evidence,
    )


def command_version(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    text = completed.stdout.strip() or completed.stderr.strip()
    return text.splitlines()[0] if text else "unknown"
