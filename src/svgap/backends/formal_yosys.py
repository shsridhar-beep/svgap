from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from svgap.backends.reference_yosys import yosys_quote, yosys_version
from svgap.model import CheckResult, Finding, Manifest, OracleConfig
from svgap.subprocess_utils import run_captured


_RULE_ID = re.compile(r"[A-Z0-9][A-Z0-9_.-]*")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_PROOF_FAILED = re.compile(
    r"(?i)(?:proof did fail|SAT proof finished\s*-\s*model found:\s*FAIL)"
)
_TIMEOUT = re.compile(r"(?i)(?:timeout|timed out)")


class FormalYosysBackend:
    """Bounded Yosys SAT checks over an explicit formal property harness.

    This is intentionally a small research oracle, not a replacement for a
    production property-verification flow.  The manifest names the property
    sources, proof top, bound, and stable finding ID explicitly.
    """

    name = "formal-yosys"
    version = "0.1"

    def check(
        self, manifest: Manifest, oracle: OracleConfig | None = None
    ) -> CheckResult:
        options = oracle.options if oracle is not None else {}
        configured = _formal_options(manifest, options)
        if isinstance(configured, str):
            return self._tool_error(configured)
        property_sources, property_top, depth, rule_id, message, timeout = configured

        executable = shutil.which(str(options.get("executable", "yosys")))
        if executable is None:
            return self._tool_error(
                f"Yosys executable not found: {options.get('executable', 'yosys')}"
            )

        build = manifest.path.parent / "build"
        build.mkdir(parents=True, exist_ok=True)
        script_path = build / f"{_safe_stem(oracle, 'formal')}.ys"
        log_path = build / f"{_safe_stem(oracle, 'formal')}.log"
        trace_path = build / f"{_safe_stem(oracle, 'formal')}-counterexample.vcd"
        script = "\n".join(
            [
                *[
                    f"read_verilog -formal -sv {yosys_quote(path)}"
                    for path in manifest.sources
                ],
                *[
                    f"read_verilog -formal -sv {yosys_quote(path)}"
                    for path in property_sources
                ],
                f"prep -top {property_top} -flatten",
                "clk2fflogic",
                "select -assert-min 1 t:$assert",
                "opt_clean",
                (
                    "sat -verify -prove-asserts "
                    f"-seq {depth} -set-init-zero -set-assumes -show-ports "
                    f"-dump_vcd {yosys_quote(trace_path)}"
                ),
            ]
        )
        script_path.write_text(script + "\n", encoding="utf-8")
        try:
            completed = run_captured(
                [executable, "-s", str(script_path)],
                cwd=manifest.path.parent,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return CheckResult(
                status="unknown",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"bounded proof timed out after {timeout} seconds: {exc}"],
                tool_versions={"yosys": yosys_version()},
            )
        except OSError as exc:
            return self._tool_error(str(exc), tool_version=yosys_version())

        combined = completed.stdout + "\n" + completed.stderr
        log_path.write_text(combined, encoding="utf-8")
        versions = {"yosys": yosys_version()}
        evidence: dict[str, Any] = {
            "method": "bounded-yosys-sat",
            "bound": depth,
            "initial_state": "zero",
            "assumptions": "honored",
            "property_top": property_top,
            "property_sources": [
                _portable(path, manifest.path.parent) for path in property_sources
            ],
            "script": _portable(script_path, manifest.path.parent),
            "log": _portable(log_path, manifest.path.parent),
        }
        if trace_path.is_file():
            evidence["counterexample"] = _portable(trace_path, manifest.path.parent)
        if completed.returncode == 0:
            return CheckResult(
                status="pass",
                backend=self.name,
                backend_version=self.version,
                tool_versions=versions,
            )
        if _PROOF_FAILED.search(combined):
            return CheckResult(
                status="fail",
                backend=self.name,
                backend_version=self.version,
                findings=[
                    Finding(
                        rule_id=rule_id,
                        severity="error",
                        message=message,
                        evidence=evidence,
                    )
                ],
                tool_versions=versions,
            )
        if _TIMEOUT.search(combined):
            return CheckResult(
                status="unknown",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[_last_diagnostic(combined)],
                tool_versions=versions,
            )
        return CheckResult(
            status="tool_error",
            backend=self.name,
            backend_version=self.version,
            diagnostics=[_last_diagnostic(combined)],
            tool_versions=versions,
        )

    def coverage(
        self, manifest: Manifest, oracle: OracleConfig | None = None
    ) -> dict[str, Any]:
        options = oracle.options if oracle is not None else {}
        depth = options.get("depth", 12)
        rule_id = options.get("rule_id", "REF-TEMP-001")
        return {
            "class": oracle.oracle_class if oracle is not None else "temporal",
            "rules": [rule_id] if isinstance(rule_id, str) else [],
            "engine": "yosys-sat",
            "proof_scope": "bounded",
            "bound": depth,
            "initial_state": "zero",
            "assumptions": "honored",
            "reference_only": True,
            "signoff_grade": False,
        }

    def _tool_error(
        self, diagnostic: str, *, tool_version: str | None = None
    ) -> CheckResult:
        versions = {"yosys": tool_version} if tool_version is not None else {}
        return CheckResult(
            status="tool_error",
            backend=self.name,
            backend_version=self.version,
            diagnostics=[diagnostic],
            tool_versions=versions,
        )


def _formal_options(
    manifest: Manifest, options: dict[str, Any]
) -> tuple[list[Path], str, int, str, str, int] | str:
    property_sources = _relative_sources(
        manifest, options.get("property_sources"), "property_sources"
    )
    if isinstance(property_sources, str):
        return property_sources
    if not any(
        re.search(r"\bassert\s*\(", path.read_text(encoding="utf-8", errors="replace"))
        for path in property_sources
    ):
        return "formal-yosys property_sources must contain at least one immediate assert"
    property_top = options.get("property_top")
    if not isinstance(property_top, str) or _IDENTIFIER.fullmatch(property_top) is None:
        return "formal-yosys property_top must be a Verilog identifier"
    depth = options.get("depth", 12)
    if not isinstance(depth, int) or isinstance(depth, bool) or not 1 <= depth <= 1000:
        return "formal-yosys depth must be an integer from 1 through 1000"
    rule_id = options.get("rule_id", "REF-TEMP-001")
    if not isinstance(rule_id, str) or _RULE_ID.fullmatch(rule_id) is None:
        return "formal-yosys rule_id must be a stable uppercase finding identifier"
    message = options.get("message", "bounded temporal contract is violated")
    if not isinstance(message, str) or not message.strip():
        return "formal-yosys message must be a nonempty string"
    timeout = options.get("timeout_seconds", 60)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 600:
        return "formal-yosys timeout_seconds must be an integer from 1 through 600"
    return property_sources, property_top, depth, rule_id, message, timeout


def _relative_sources(
    manifest: Manifest, value: Any, option_name: str
) -> list[Path] | str:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        return f"formal-yosys {option_name} must be a nonempty array of relative paths"
    base = manifest.path.parent.resolve()
    resolved: list[Path] = []
    for item in value:
        path_value = Path(item)
        if path_value.is_absolute():
            return f"formal-yosys {option_name} paths must be relative"
        path = (base / path_value).resolve()
        if not path.is_relative_to(base):
            return f"formal-yosys {option_name} paths must remain inside the manifest directory"
        if not path.is_file():
            return f"formal-yosys {option_name} file does not exist: {item}"
        resolved.append(path)
    return resolved


def _safe_stem(oracle: OracleConfig | None, fallback: str) -> str:
    value = oracle.oracle_id if oracle is not None else fallback
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or fallback


def _portable(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _last_diagnostic(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else "Yosys exited without a diagnostic"
