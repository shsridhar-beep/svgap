from __future__ import annotations

import os
import subprocess
from pathlib import Path

from svgap.model import FunctionalResult, Manifest


def run_functional(manifest: Manifest) -> FunctionalResult:
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


def command_version(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    text = completed.stdout.strip() or completed.stderr.strip()
    return text.splitlines()[0] if text else "unknown"
