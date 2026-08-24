"""Library entry point for evaluating candidates programmatically.

The CLI and this module share one evaluation path. Setup problems (a broken
manifest, an unknown backend) raise; measurement outcomes, including
``unknown`` and ``tool_error``, are returned inside the report, never raised.
"""

from __future__ import annotations

import json
import inspect
from datetime import datetime, timezone
from pathlib import Path

from svgap.backends.registry import BackendError, load_backend
from svgap.functional import run_functional
from svgap.manifest import Manifest, load_manifest
from svgap.model import (
    CheckResult,
    EvaluationReport,
    FunctionalResult,
    OracleConfig,
    OracleResult,
)


def evaluate(
    manifest: Manifest | str | Path,
    *,
    skip_functional: bool = False,
    write_report: bool = True,
    manifest_label: str | None = None,
) -> EvaluationReport:
    """Evaluate one RTL candidate and return its layered report.

    ``manifest`` is a loaded :class:`Manifest` or a path to one. When
    ``write_report`` is true (the default, matching ``svgap check``), the
    schema-versioned report is atomically written to the manifest's report
    path. ``manifest_label`` overrides the manifest path recorded inside the
    report, for callers that need portable paths.
    """
    if not isinstance(manifest, Manifest):
        manifest = load_manifest(Path(manifest))
    functional = (
        FunctionalResult(status="not_run") if skip_functional else run_functional(manifest)
    )
    configs = manifest.oracles or [
        OracleConfig(
            oracle_id="structural",
            oracle_class="structural",
            backend=manifest.backend,
        )
    ]
    oracle_results = [_run_oracle(manifest, config) for config in configs]
    structural_oracle = next(
        item for item in oracle_results if item.oracle_class == "structural"
    )
    structural = structural_oracle.to_check_result()
    gap_member = functional.status == "pass" and any(
        item.contributes_to_gap and item.status == "fail" for item in oracle_results
    )
    report = EvaluationReport(
        schema_version=manifest.schema_version,
        candidate_id=manifest.candidate_id,
        manifest=manifest_label or str(manifest.path),
        functional=functional,
        structural=structural,
        gap_member=gap_member,
        generated_at=datetime.now(timezone.utc).isoformat(),
        oracle_results=oracle_results if manifest.schema_version == "2.0" else [],
    )
    if write_report:
        manifest.report_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
        temporary = manifest.report_path.with_suffix(manifest.report_path.suffix + ".tmp")
        temporary.write_text(payload + "\n", encoding="utf-8")
        temporary.replace(manifest.report_path)
    return report


def _run_oracle(manifest: Manifest, config: OracleConfig) -> OracleResult:
    try:
        backend = load_backend(config.backend)
    except BackendError as exc:
        if config.required:
            raise
        result = CheckResult(
            status="tool_error",
            backend=config.backend,
            backend_version="unavailable",
            diagnostics=[str(exc)],
        )
        return OracleResult.from_check(config, result, coverage={"executed": False})

    check = backend.check
    parameters = inspect.signature(check).parameters
    result = check(manifest, config) if len(parameters) >= 2 else check(manifest)
    if not isinstance(result, CheckResult):
        raise BackendError(
            f"checker backend {config.backend!r} returned an invalid result"
        )
    coverage_method = getattr(backend, "coverage", None)
    coverage: dict = {}
    if callable(coverage_method):
        coverage_parameters = inspect.signature(coverage_method).parameters
        coverage = (
            coverage_method(manifest, config)
            if len(coverage_parameters) >= 2
            else coverage_method(manifest)
        )
        if not isinstance(coverage, dict):
            raise BackendError(
                f"checker backend {config.backend!r} returned invalid coverage"
            )
    return OracleResult.from_check(config, result, coverage=coverage)
