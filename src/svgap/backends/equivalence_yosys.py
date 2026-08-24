from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from svgap.backends.formal_yosys import (
    _IDENTIFIER,
    _PROOF_FAILED,
    _RULE_ID,
    _TIMEOUT,
    _last_diagnostic,
    _portable,
    _relative_sources,
    _safe_stem,
)
from svgap.backends.reference_yosys import yosys_quote, yosys_version
from svgap.model import CheckResult, Finding, Manifest, OracleConfig
from svgap.subprocess_utils import run_captured


class EquivalenceYosysBackend:
    """Bounded candidate/reference equivalence after Yosys RTL synthesis."""

    name = "equivalence-yosys"
    version = "0.1"

    def check(
        self, manifest: Manifest, oracle: OracleConfig | None = None
    ) -> CheckResult:
        options = oracle.options if oracle is not None else {}
        configured = _equivalence_options(manifest, options)
        if isinstance(configured, str):
            return self._tool_error(configured)
        reference_sources, reference_top, depth, rule_id, message, timeout = configured

        executable = shutil.which(str(options.get("executable", "yosys")))
        if executable is None:
            return self._tool_error(
                f"Yosys executable not found: {options.get('executable', 'yosys')}"
            )

        build = manifest.path.parent / "build"
        build.mkdir(parents=True, exist_ok=True)
        stem = _safe_stem(oracle, "equivalence")
        script_path = build / f"{stem}.ys"
        log_path = build / f"{stem}.log"
        trace_path = build / f"{stem}-counterexample.vcd"
        script = "\n".join(
            [
                *[
                    f"read_verilog -sv {yosys_quote(path)}"
                    for path in reference_sources
                ],
                f"prep -top {reference_top} -flatten",
                "techmap",
                "opt_clean",
                "rename -top gold",
                "design -stash gold_design",
                *[
                    f"read_verilog -sv {yosys_quote(path)}"
                    for path in manifest.sources
                ],
                f"prep -top {manifest.top} -flatten",
                "techmap",
                "opt_clean",
                "rename -top gate",
                "design -stash gate_design",
                "design -copy-from gold_design -as gold gold",
                "design -copy-from gate_design -as gate gate",
                "miter -equiv -make_assert -make_outputs -flatten gold gate equiv_miter",
                "prep -top equiv_miter -flatten",
                "select -assert-min 1 t:$assert",
                (
                    "sat -verify -prove-asserts "
                    f"-seq {depth} -set-init-zero -show-ports "
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
                diagnostics=[f"equivalence proof timed out after {timeout} seconds: {exc}"],
                tool_versions={"yosys": yosys_version()},
            )
        except OSError as exc:
            return self._tool_error(str(exc), tool_version=yosys_version())

        combined = completed.stdout + "\n" + completed.stderr
        log_path.write_text(combined, encoding="utf-8")
        versions = {"yosys": yosys_version()}
        evidence: dict[str, Any] = {
            "method": "bounded-synthesized-yosys-miter",
            "bound": depth,
            "initial_state": "zero",
            "candidate_top": manifest.top,
            "reference_top": reference_top,
            "reference_sources": [
                _portable(path, manifest.path.parent) for path in reference_sources
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
        depth = options.get("depth", 1)
        rule_id = options.get("rule_id", "REF-EQUIV-001")
        return {
            "class": oracle.oracle_class if oracle is not None else "equivalence",
            "rules": [rule_id] if isinstance(rule_id, str) else [],
            "engine": "yosys-sat-miter",
            "comparison_stage": "post-yosys-rtl-synthesis",
            "proof_scope": "combinational" if depth == 1 else "bounded-sequential",
            "bound": depth,
            "initial_state": "zero",
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


def _equivalence_options(
    manifest: Manifest, options: dict[str, Any]
) -> tuple[list[Path], str, int, str, str, int] | str:
    references = _relative_sources(
        manifest, options.get("reference_sources"), "reference_sources"
    )
    if isinstance(references, str):
        return references.replace("formal-yosys", "equivalence-yosys", 1)
    reference_top = options.get("reference_top", manifest.top)
    if not isinstance(reference_top, str) or _IDENTIFIER.fullmatch(reference_top) is None:
        return "equivalence-yosys reference_top must be a Verilog identifier"
    depth = options.get("depth", 1)
    if not isinstance(depth, int) or isinstance(depth, bool) or not 1 <= depth <= 1000:
        return "equivalence-yosys depth must be an integer from 1 through 1000"
    rule_id = options.get("rule_id", "REF-EQUIV-001")
    if not isinstance(rule_id, str) or _RULE_ID.fullmatch(rule_id) is None:
        return "equivalence-yosys rule_id must be a stable uppercase finding identifier"
    message = options.get(
        "message", "candidate is not equivalent to the reference after Yosys synthesis"
    )
    if not isinstance(message, str) or not message.strip():
        return "equivalence-yosys message must be a nonempty string"
    timeout = options.get("timeout_seconds", 60)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 600:
        return "equivalence-yosys timeout_seconds must be an integer from 1 through 600"
    return references, reference_top, depth, rule_id, message, timeout
