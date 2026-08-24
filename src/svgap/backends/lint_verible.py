from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from svgap.model import CheckResult, Finding, Manifest, OracleConfig


_DIAGNOSTIC = re.compile(
    r"^(?P<location>.+?:\d+:\d+(?:-\d+)?):\s*(?P<message>.*)$"
)


class VeribleLintBackend:
    """Verible syntax/style lint represented independently from structure."""

    name = "lint-verible"
    version = "0.1"

    def check(self, manifest: Manifest, oracle: OracleConfig | None = None) -> CheckResult:
        options = oracle.options if oracle is not None else {}
        executable = str(options.get("executable", "verible-verilog-lint"))
        resolved = shutil.which(executable)
        if resolved is None and Path(executable).is_file():
            resolved = str(Path(executable).resolve())
        if resolved is None:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"Verible executable not found: {executable}"],
            )
        ruleset = str(options.get("ruleset", "default"))
        if ruleset not in {"default", "all", "none"}:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=["lint-verible ruleset must be default, all, or none"],
            )
        sources = [_candidate_relative(path, manifest) for path in manifest.sources]
        command = [resolved, f"--ruleset={ruleset}", *sources]
        try:
            completed = subprocess.run(
                command,
                cwd=manifest.path.parent,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[str(exc)],
                tool_versions={"verible": _version(resolved)},
            )

        findings: list[Finding] = []
        for line in (completed.stdout + "\n" + completed.stderr).splitlines():
            match = _DIAGNOSTIC.match(line)
            if match is None:
                continue
            message = match.group("message")
            code_match = re.search(r"\s+\[([^\]]+)\]\s*$", message)
            if code_match is not None:
                message = message[: code_match.start()].rstrip()
            syntax_error = "syntax error" in message.lower()
            raw_code = (
                code_match.group(1)
                if code_match is not None
                else ("syntax" if syntax_error else "unclassified")
            )
            code = re.sub(r"[^A-Za-z0-9]+", "-", raw_code).strip("-").upper()
            findings.append(
                Finding(
                    rule_id=f"LINT-VERIBLE-{code}",
                    severity="error" if syntax_error else "warning",
                    message=message,
                    evidence={
                        "location": match.group("location"),
                        "command": command,
                        "diagnostic": line,
                    },
                )
            )
        errors = [finding for finding in findings if finding.severity == "error"]
        if completed.returncode not in (0, 1) or (completed.returncode and not findings):
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                findings=findings,
                diagnostics=[
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or f"Verible exited {completed.returncode} without a parsed diagnostic"
                ],
                tool_versions={"verible": _version(resolved)},
            )
        return CheckResult(
            status="fail" if errors else "pass",
            backend=self.name,
            backend_version=self.version,
            findings=findings,
            diagnostics=[],
            tool_versions={"verible": _version(resolved)},
        )

    def coverage(self, manifest: Manifest, oracle: OracleConfig | None = None) -> dict:
        options = oracle.options if oracle is not None else {}
        return {
            "class": "lint",
            "ruleset": str(options.get("ruleset", "default")),
            "source_count": len(manifest.sources),
            "source_scope": "manifest.design.sources",
            "calibrations": [
                {
                    "id": "rdc-lint-baseline-v0.1",
                    "tool_version": "Verible v0.0-4121-gc2ec3416",
                    "configuration": "--ruleset=default",
                    "population": "functionally passing REF-RDC-001 gaps",
                    "cases": 14,
                    "rdc_specific_detections": 0,
                }
            ],
        }


def _candidate_relative(path: Path, manifest: Manifest) -> str:
    try:
        return str(path.relative_to(manifest.path.parent))
    except ValueError:
        return str(path)


def _version(executable: str) -> str:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    lines = (completed.stdout + completed.stderr).strip().splitlines()
    return lines[0] if lines else "unknown"
