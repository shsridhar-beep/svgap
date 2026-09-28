from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from svgap.artifacts import existing_artifacts
from svgap.model import CheckResult, Finding, Manifest, OracleConfig


_DIAGNOSTIC = re.compile(
    r"^%(?P<severity>Warning|Error)(?:-(?P<code>[A-Z0-9_]+))?:\s*(?P<message>.*)$"
)


class VerilatorLintBackend:
    """Ordinary Verilator lint as a distinct, non-structural evidence class."""

    name = "lint-verilator"
    version = "0.2"

    def check(self, manifest: Manifest, oracle: OracleConfig | None = None) -> CheckResult:
        options = oracle.options if oracle is not None else {}
        executable = str(options.get("executable", "verilator"))
        resolved = shutil.which(executable)
        if resolved is None:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"Verilator executable not found: {executable}"],
                observed_coverage={"executed": False, "requirements_met": False},
            )
        sources = [_candidate_relative(path, manifest) for path in manifest.sources]
        extra_args = options.get("extra_args", [])
        if not isinstance(extra_args, list) or not all(
            isinstance(item, str) for item in extra_args
        ):
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=["lint-verilator extra_args must be an array of strings"],
                observed_coverage={"executed": False, "requirements_met": False},
            )
        # Place caller policy after the built-in defaults so a targeted
        # ``-Wno-*`` can override ``--Wall`` deterministically.
        command = [
            resolved,
            "--lint-only",
            "--Wall",
            "--Wno-fatal",
            *extra_args,
            "--top-module",
            manifest.top,
            *sources,
        ]
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
                tool_versions={"verilator": _version(resolved)},
                observed_coverage={"executed": False, "requirements_met": False},
            )

        build = manifest.path.parent / "build"
        build.mkdir(parents=True, exist_ok=True)
        log_path = build / f"{_safe_stem(oracle, 'verilator')}.log"
        log_path.write_text(
            completed.stdout + "\n" + completed.stderr, encoding="utf-8"
        )
        artifacts = existing_artifacts(
            manifest.path.parent, lint_log=(log_path, "tool-log")
        )

        findings: list[Finding] = []
        for line in (completed.stdout + "\n" + completed.stderr).splitlines():
            match = _DIAGNOSTIC.match(line)
            if match is None:
                continue
            severity = "error" if match.group("severity") == "Error" else "warning"
            code = match.group("code") or match.group("severity").upper()
            findings.append(
                Finding(
                    rule_id=f"LINT-VERILATOR-{code}",
                    severity=severity,
                    message=match.group("message"),
                    evidence={"command": command, "diagnostic": line},
                )
            )
        errors = [finding for finding in findings if finding.severity == "error"]
        if completed.returncode != 0 and not errors:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                findings=findings,
                diagnostics=[
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or f"Verilator exited {completed.returncode} without a parsed diagnostic"
                ],
                tool_versions={"verilator": _version(resolved)},
                artifacts=artifacts,
                observed_coverage={"executed": True, "requirements_met": False},
            )
        return CheckResult(
            status="fail" if errors else "pass",
            backend=self.name,
            backend_version=self.version,
            findings=findings,
            diagnostics=[],
            tool_versions={"verilator": _version(resolved)},
            artifacts=artifacts,
            observed_coverage={"executed": True, "requirements_met": True},
        )

    def coverage(self, manifest: Manifest, oracle: OracleConfig | None = None) -> dict:
        options = oracle.options if oracle is not None else {}
        return {
            "class": "lint",
            "ruleset": "--Wall",
            "source_count": len(manifest.sources),
            "source_scope": "manifest.design.sources",
            "extra_args": options.get("extra_args", []),
            "calibrations": [
                {
                    "id": "rdc-lint-baseline-v0.1",
                    "tool_version": "Verilator 5.050",
                    "configuration": "--lint-only --Wall --Wno-fatal",
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


def _safe_stem(oracle: OracleConfig | None, fallback: str) -> str:
    value = oracle.oracle_id if oracle is not None else fallback
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or fallback


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
    return (completed.stdout.strip() or completed.stderr.strip() or "unknown").splitlines()[0]
