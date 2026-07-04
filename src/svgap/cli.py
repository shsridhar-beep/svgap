from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from svgap.backends.registry import BackendError, discover_backends, load_backend
from svgap.audit import audit_benchmark, write_audit
from svgap.functional import run_functional
from svgap.manifest import ManifestError, load_manifest
from svgap.model import EvaluationReport, FunctionalResult
from svgap.pilot import materialize_candidate
from svgap.provenance import canonical_file_set_digest
from svgap.reporting import build_html, dumps_sarif
from svgap.study import summarize_reports
from svgap.validation import ReportValidationError, validate_report_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svgap", description="Production-readiness evaluation for AI-generated RTL"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="check local open-source tool prerequisites")
    digest = subparsers.add_parser("digest", help="print the canonical source digest for a manifest")
    digest.add_argument("manifest", type=Path)
    check = subparsers.add_parser("check", help="evaluate one RTL candidate")
    check.add_argument("manifest", type=Path)
    check.add_argument("--skip-functional", action="store_true")
    check.add_argument("--json", action="store_true", help="print the full report to stdout")
    gap = subparsers.add_parser("gap", help="aggregate existing evaluation reports")
    gap.add_argument("reports", nargs="+", type=Path)
    audit = subparsers.add_parser("audit", help="audit a public benchmark's structural coverage")
    audit.add_argument("kind", choices=("verilog-eval", "rtllm", "cvdp"))
    audit.add_argument("root", type=Path)
    audit.add_argument("--output", type=Path, default=Path("reports/audits"))
    pilot = subparsers.add_parser("pilot", help="ingest and evaluate one generated RTL response")
    pilot.add_argument("task", type=Path, help="task directory containing task.toml")
    pilot.add_argument("response", type=Path, help="raw model response")
    pilot.add_argument("--model", required=True, help="model identifier recorded in provenance")
    pilot.add_argument("--run-id", help="unique run label used for the output directory")
    pilot.add_argument("--output", type=Path, default=Path("reports/generated/pilot-v0.1"))
    summarize = subparsers.add_parser("summarize", help="deterministically aggregate a study")
    summarize.add_argument("root", type=Path, help="study directory containing candidate reports")
    summarize.add_argument("--output", type=Path)
    export = subparsers.add_parser("export", help="export reports as SARIF and/or static HTML")
    export.add_argument("reports", nargs="+", type=Path)
    export.add_argument("--sarif", type=Path)
    export.add_argument("--html", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "digest":
        try:
            manifest = load_manifest(args.manifest)
        except ManifestError as exc:
            print(f"manifest error: {exc}", file=sys.stderr)
            return 2
        print(canonical_file_set_digest(manifest.path.parent, manifest.sources))
        return 0
    if args.command == "check":
        return check(args.manifest, args.skip_functional, args.json)
    if args.command == "gap":
        return gap(args.reports)
    if args.command == "audit":
        return run_audit(args.kind, args.root, args.output)
    if args.command == "pilot":
        try:
            manifest = materialize_candidate(
                args.task, args.response, args.model, args.output, args.run_id
            )
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            print(f"pilot ingestion failed: {exc}", file=sys.stderr)
            return 2
        print(f"manifest    {manifest}")
        return check(manifest, False, False)
    if args.command == "summarize":
        reports = list(args.root.resolve().glob("*/*/report.json"))
        if not reports:
            print("no candidate reports found", file=sys.stderr)
            return 2
        payload = json.dumps(summarize_reports(reports), indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
            print(args.output)
        else:
            print(payload, end="")
        return 0
    if args.command == "export":
        if args.sarif is None and args.html is None:
            print("export requires --sarif and/or --html", file=sys.stderr)
            return 2
        reports = []
        try:
            for path in args.reports:
                reports.append(
                    validate_report_payload(json.loads(path.read_text(encoding="utf-8")))
                )
        except (OSError, json.JSONDecodeError, ReportValidationError) as exc:
            print(f"cannot export reports: {exc}", file=sys.stderr)
            return 2
        if args.sarif:
            args.sarif.parent.mkdir(parents=True, exist_ok=True)
            args.sarif.write_text(dumps_sarif(reports), encoding="utf-8")
            print(f"sarif       {args.sarif}")
        if args.html:
            args.html.parent.mkdir(parents=True, exist_ok=True)
            args.html.write_text(build_html(reports), encoding="utf-8")
            print(f"html        {args.html}")
        return 0
    return 2


def doctor() -> int:
    missing = []
    for tool in ("yosys", "iverilog", "vvp"):
        path = shutil.which(tool)
        print(f"{tool:10} {path or 'MISSING'}")
        if path is None:
            missing.append(tool)
    if not missing:
        version = subprocess.run(
            ["yosys", "-V"], capture_output=True, text=True, check=False
        ).stdout.strip()
        print(f"backend    reference-yosys 0.1 ({version})")
    backends, backend_errors = discover_backends()
    print(f"backends   {', '.join(sorted(backends))}")
    for name, error in sorted(backend_errors.items()):
        print(f"plugin     {name}: {error}")
        missing.append(f"backend:{name}")
    return 1 if missing else 0


def check(manifest_path: Path, skip_functional: bool, print_json: bool) -> int:
    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    functional = (
        FunctionalResult(status="not_run") if skip_functional else run_functional(manifest)
    )
    try:
        backend = load_backend(manifest.backend)
    except (BackendError, ImportError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    structural = backend.check(manifest)
    report = EvaluationReport(
        schema_version="1.0",
        candidate_id=manifest.candidate_id,
        manifest=portable_path(manifest.path),
        functional=functional,
        structural=structural,
        gap_member=functional.status == "pass" and structural.status == "fail",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    manifest.report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    temporary_report = manifest.report_path.with_suffix(manifest.report_path.suffix + ".tmp")
    temporary_report.write_text(payload + "\n", encoding="utf-8")
    temporary_report.replace(manifest.report_path)
    if print_json:
        print(payload)
    else:
        print_summary(report, manifest.report_path)

    if functional.status == "tool_error" or structural.status == "tool_error":
        return 2
    if functional.status == "unknown" or structural.status == "unknown":
        return 3
    return 1 if functional.status in ("fail", "compile_error") or structural.status == "fail" else 0


def print_summary(report: EvaluationReport, report_path: Path) -> None:
    print(f"candidate   {report.candidate_id}")
    print(f"functional  {report.functional.status}")
    print(f"structural  {report.structural.status}")
    print(f"gap member  {'yes' if report.gap_member else 'no'}")
    for finding in report.structural.findings:
        source = finding.evidence.get("source_cell") or finding.evidence.get("cell")
        destination = finding.evidence.get("destination_cell")
        context = f" [{source} -> {destination}]" if destination else f" [{source}]" if source else ""
        print(f"{finding.severity.upper():7} {finding.rule_id}: {finding.message}{context}")
    for diagnostic in report.structural.diagnostics:
        print(f"UNKNOWN  {diagnostic}")
    print(f"report      {report_path}")


def gap(report_paths: list[Path]) -> int:
    reports = []
    for path in report_paths:
        try:
            reports.append(validate_report_payload(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, ReportValidationError) as exc:
            print(f"cannot read {path}: {exc}", file=sys.stderr)
            return 2
    functional_pass = [item for item in reports if item["functional"]["status"] == "pass"]
    determinate = [
        item for item in functional_pass if item["structural"]["status"] in ("pass", "fail")
    ]
    failures = [item for item in determinate if item["structural"]["status"] == "fail"]
    value = len(failures) / len(determinate) if determinate else None
    print(f"reports                    {len(reports)}")
    print(f"functional pass            {len(functional_pass)}")
    print(f"structurally determinate    {len(determinate)}")
    print(f"structural failures         {len(failures)}")
    print(f"structural-validity gap     {value:.3f}" if value is not None else "structural-validity gap     n/a")
    return 0


def portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def run_audit(kind: str, root: Path, output: Path) -> int:
    try:
        audit = audit_benchmark(kind, root)  # type: ignore[arg-type]
        write_audit(audit, output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2
    for key, value in audit.summary().items():
        print(f"{key:39} {value}")
    print(f"reports                                 {output.resolve()}")
    return 0
