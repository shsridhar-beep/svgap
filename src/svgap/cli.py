from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
import platform
import shlex
import shutil
import subprocess
import sys
import tomllib
from tempfile import TemporaryDirectory
from pathlib import Path

from svgap.backends.registry import (
    BackendError,
    discover_backends,
    load_backend,
    unavailable_backends,
)
from svgap.challenge import ChallengeError, score_challenge
from svgap.challenge_runner import ChallengeRunError, run_challenge
from svgap.audit import audit_benchmark, write_audit
from svgap.adjudication import (
    InstrumenterUnavailable,
    MockPrerecordedInstrumenter,
    ResetReleaseSkewInstrumenter,
    TraceError,
    adjudicate_prerecorded,
    compare_traces,
    load_trace,
    run_calibration_suite,
    trace_digest,
    trace_from_csv,
)
from svgap.api import evaluate
from svgap.demo import (
    DemoError,
    build_demo_summary,
    materialize_demo,
    render_demo_summary,
    require_demo_tools,
    write_demo_summary,
)
from svgap.legibility import explain_payload, render_explanation
from svgap.manifest import ManifestError, load_manifest
from svgap.model import EvaluationReport
from svgap.onboarding import manifest_readiness, render_manifest_draft
from svgap.pilot import materialize_candidate
from svgap.provenance import canonical_file_set_digest
from svgap.reporting import build_html, dumps_sarif
from svgap.resources import ResourceError, TASKPACKS, taskpack_metadata
from svgap.study import summarize_reports
from svgap.study_runner import (
    StudyError,
    evaluate_saved_responses,
    run_quickstart,
    run_study,
)
from svgap.submission import (
    SubmissionError,
    bundle_submission,
    initialize_submission,
    initialize_submission_from_harbor,
    validate_submission,
)
from svgap.validation import ReportValidationError, validate_report_payload


RUN_REPORT_URL = (
    "https://github.com/shsridhar-beep/svgap/issues/new?template=run_report.yml"
)
RESULT_CONTRIBUTION_URL = (
    "https://shsridhar-beep.github.io/svgap/submitting-results/"
)


def harbor_submission_receipt(
    manifest: dict[str, object], output: Path
) -> list[str]:
    summary_path = output / str(
        (manifest.get("artifacts") or {}).get("summary", "summary.json")
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = [
        f"submission  {output.resolve()}",
        f"id          {manifest['submission_id']}",
        f"source      {(manifest.get('source') or {})['job_id']}",
    ]
    if summary.get("kind") == "generation_reports":
        lines.extend(
            [
                f"reports     {summary['report_count']}",
                f"tests pass  {summary['functional_pass']}",
                f"pass/rule   {summary['gap_members']}",
            ]
        )
    lines.extend(
        [
            f"report run  {RUN_REPORT_URL}",
            f"contribute  {RESULT_CONTRIBUTION_URL}",
            "privacy     no telemetry or automatic upload",
        ]
    )
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svgap", description="Production-evidence profiles for AI-generated digital RTL"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="check local open-source tool prerequisites")
    demo = subparsers.add_parser(
        "demo", help="run the controlled functional-pass/structural-gap demonstration"
    )
    demo.add_argument("--output", type=Path, help="preserve demo sources, reports, and summary")
    demo.add_argument("--json", action="store_true", help="print the demo summary as JSON")
    taskpack = subparsers.add_parser(
        "taskpack", help="list and inspect packaged frozen taskpacks"
    )
    taskpack_commands = taskpack.add_subparsers(dest="taskpack_command", required=True)
    taskpack_commands.add_parser("list", help="list installed taskpacks")
    taskpack_show = taskpack_commands.add_parser("show", help="show taskpack metadata")
    taskpack_show.add_argument("taskpack")
    taskpack_path = taskpack_commands.add_parser("path", help="print the installed taskpack path")
    taskpack_path.add_argument("taskpack")
    study = subparsers.add_parser(
        "study", help="create evidence profiles from a fixture, model, or saved responses"
    )
    study_commands = study.add_subparsers(dest="study_command", required=True)
    study_quickstart = study_commands.add_parser(
        "quickstart",
        help="evaluate a bundled fixture and create a first evidence profile",
        description=(
            "Evaluate a labelled known-unsafe fixture with the local open toolchain, "
            "then write an HTML profile and an explainable report."
        ),
        epilog="This validates the evidence workflow; it is not a model result.",
    )
    study_quickstart.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new directory for the profile and reproducible evidence",
    )
    study_run = study_commands.add_parser(
        "run", help="generate and evaluate a smoke or frozen full study"
    )
    study_run.add_argument("taskpack")
    study_run.add_argument(
        "--command",
        required=True,
        dest="generator_command",
        help="reads prompt on stdin; writes response",
    )
    study_run.add_argument("--label", required=True, help="stable public configuration label")
    study_run.add_argument("--interface-label", default="custom-command")
    mode = study_run.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="one task and one sample (default)")
    mode.add_argument("--full", action="store_true", help="all frozen tasks and three samples")
    study_run.add_argument("--task", action="append", dest="tasks", help="expert task override; repeatable")
    study_run.add_argument("--samples", type=int, help="expert sample-count override")
    study_run.add_argument("--generate-only", action="store_true")
    study_run.add_argument(
        "--generation-config",
        type=Path,
        help="public JSON object containing decoding and harness parameters",
    )
    study_run.add_argument("--output", required=True, type=Path)
    study_evaluate = study_commands.add_parser(
        "evaluate-saved", help="evaluate responses generated in a separate trust domain"
    )
    study_evaluate.add_argument("taskpack")
    study_evaluate.add_argument("--responses", required=True, type=Path)
    study_evaluate.add_argument("--output", required=True, type=Path)
    challenge_group = subparsers.add_parser(
        "challenge", help="run or score packaged generation, diagnosis, and repair challenges"
    )
    challenge_commands = challenge_group.add_subparsers(
        dest="challenge_command", required=True
    )
    challenge_run = challenge_commands.add_parser(
        "run", help="run a packaged diagnosis or repair starter"
    )
    challenge_run.add_argument("track", choices=("diagnosis", "repair"))
    challenge_run.add_argument("--command", required=True, dest="generator_command")
    challenge_run.add_argument("--label", required=True)
    challenge_run.add_argument("--run-id", required=True)
    challenge_run.add_argument("--output", required=True, type=Path)
    challenge_score = challenge_commands.add_parser(
        "score", help="score a challenge submission"
    )
    challenge_score.add_argument("task", type=Path)
    challenge_score.add_argument("submission", type=Path)
    challenge_score.add_argument("--output", type=Path)
    challenge_score.add_argument("--json", action="store_true")
    initialize = subparsers.add_parser(
        "init", help="create a manifest draft without inferring design intent"
    )
    initialize.add_argument("source", type=Path)
    initialize.add_argument("--top", required=True)
    initialize.add_argument("--candidate-id", required=True)
    initialize.add_argument("--output", required=True, type=Path)
    validate = subparsers.add_parser(
        "validate", help="validate a manifest and report unanswered evidence questions"
    )
    validate.add_argument("manifest", type=Path)
    validate.add_argument("--json", action="store_true")
    explain = subparsers.add_parser(
        "explain", help="translate a report into answered, failed, and unanswered questions"
    )
    explain.add_argument("report", type=Path)
    explain.add_argument("--json", action="store_true")
    explain.add_argument(
        "--report-only",
        action="store_true",
        help="print the explanation without using evidence outcomes as the exit code",
    )
    digest = subparsers.add_parser("digest", help="print the canonical source digest for a manifest")
    digest.add_argument("manifest", type=Path)
    check = subparsers.add_parser(
        "check",
        help="evaluate one RTL candidate",
        epilog=(
            "exit codes: 0 pass, 1 functional or structural fail, "
            "2 tool or manifest error, 3 unknown (insufficient intent or coverage). "
            "--fail-on narrows which outcomes gate the exit code; the report always "
            "records the full result."
        ),
    )
    check.add_argument("manifest", type=Path)
    check.add_argument("--skip-functional", action="store_true")
    check.add_argument("--json", action="store_true", help="print the full report to stdout")
    check.add_argument(
        "--fail-on",
        choices=("any", "gap", "report-only"),
        default="any",
        help=(
            "any (default): nonzero on fail, unknown, or tool error; "
            "gap: nonzero only for functional-pass/structural-fail candidates "
            "(tool errors still exit 2); report-only: always exit 0 once a "
            "report is written"
        ),
    )
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
    trace = subparsers.add_parser("trace-normalize", help="normalize observer CSV into a digital trace")
    trace.add_argument("csv", type=Path)
    trace.add_argument("--trace-id", required=True)
    trace.add_argument("--candidate-digest", required=True)
    trace.add_argument("--observer", required=True)
    trace.add_argument("--observer-version", required=True)
    trace.add_argument("--sampling", required=True)
    trace.add_argument("--output", required=True, type=Path)
    compare = subparsers.add_parser("compare-traces", help="compare two normalized digital traces")
    compare.add_argument("golden", type=Path)
    compare.add_argument("observed", type=Path)
    compare.add_argument("--max-shift", type=int, default=0)
    compare.add_argument("--warmup-samples", type=int, default=0)
    compare.add_argument("--x-policy", choices=("exact", "golden_x_wildcard"), default="exact")
    compare.add_argument("--json", action="store_true")
    calibrate = subparsers.add_parser(
        "calibrate-adjudicator", help="run a prerecorded generic calibration suite"
    )
    calibrate.add_argument("suite", type=Path)
    calibrate.add_argument("--max-shift", type=int, default=0)
    calibrate.add_argument("--warmup-samples", type=int, default=0)
    calibrate.add_argument("--output", type=Path)
    adjudicate = subparsers.add_parser(
        "adjudicate", help="adjudicate prerecorded traces or report unavailable instrumenters"
    )
    adjudicate.add_argument(
        "--instrumenter",
        required=True,
        choices=("mock-prerecorded", "reset-release-skew"),
    )
    adjudicate.add_argument("--candidate-id")
    adjudicate.add_argument("--rule-id")
    adjudicate.add_argument("--golden", type=Path)
    adjudicate.add_argument("--observed", nargs="*", type=Path, default=[])
    adjudicate.add_argument("--calibration-suite", type=Path)
    adjudicate.add_argument("--semantics", default="generic-prerecorded-trace-comparison")
    adjudicate.add_argument("--semantics-version", default="1.0")
    adjudicate.add_argument("--max-shift", type=int, default=0)
    adjudicate.add_argument("--warmup-samples", type=int, default=0)
    adjudicate.add_argument("--output", type=Path)
    challenge = subparsers.add_parser(
        "challenge-score", help="score a frontier-model generation, diagnosis, or repair submission"
    )
    challenge.add_argument("task", type=Path)
    challenge.add_argument("submission", type=Path)
    challenge.add_argument("--output", type=Path)
    challenge.add_argument("--json", action="store_true")
    submission = subparsers.add_parser(
        "submission", help="create, validate, and bundle a public result submission"
    )
    submission_commands = submission.add_subparsers(
        dest="submission_command", required=True
    )
    submission_init = submission_commands.add_parser(
        "init", help="create a submission directory from track-specific evidence"
    )
    submission_init.add_argument(
        "evidence",
        nargs="+",
        type=Path,
        help="generation report.json files or diagnosis/repair result.json files",
    )
    submission_init.add_argument("--id", required=True, dest="submission_id")
    submission_init.add_argument("--title", required=True)
    submission_init.add_argument(
        "--track", required=True, choices=("generation", "diagnosis", "repair")
    )
    submission_init.add_argument("--configuration-label", required=True)
    submission_init.add_argument(
        "--provenance-level",
        required=True,
        choices=("public", "attested_alias", "anonymous_case_study"),
    )
    submission_init.add_argument("--provider")
    submission_init.add_argument("--model-id")
    submission_init.add_argument("--attestor")
    submission_init.add_argument("--attestation")
    submission_init.add_argument("--taskpack-id", required=True)
    submission_init.add_argument("--taskpack-version", required=True)
    submission_init.add_argument("--contributor", required=True)
    submission_init.add_argument("--output", required=True, type=Path)
    submission_validate = submission_commands.add_parser(
        "validate", help="validate hashes, profiles, provenance, and publication safety"
    )
    submission_validate.add_argument("directory", type=Path)
    submission_validate.add_argument(
        "--denylist",
        type=Path,
        help="private file containing one case-insensitive regex per line",
    )
    submission_bundle = submission_commands.add_parser(
        "bundle", help="create a deterministic publication bundle"
    )
    submission_bundle.add_argument("directory", type=Path)
    submission_bundle.add_argument("--output", required=True, type=Path)
    submission_bundle.add_argument("--denylist", type=Path)
    submission_harbor = submission_commands.add_parser(
        "from-harbor",
        help="create a validated submission directory from a complete Harbor job",
    )
    submission_harbor.add_argument("job", type=Path)
    submission_harbor.add_argument(
        "--dataset",
        required=True,
        help="pinned Harbor reference or local dataset path",
    )
    submission_harbor.add_argument("--id", required=True, dest="submission_id")
    submission_harbor.add_argument("--title", required=True)
    submission_harbor.add_argument("--configuration-label")
    submission_harbor.add_argument(
        "--provenance-level",
        required=True,
        choices=("public", "attested_alias", "anonymous_case_study"),
    )
    submission_harbor.add_argument("--provider")
    submission_harbor.add_argument("--model-id")
    submission_harbor.add_argument("--attestor")
    submission_harbor.add_argument("--attestation")
    submission_harbor.add_argument("--contributor", required=True)
    submission_harbor.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "demo":
        return run_demo_command(args.output, args.json)
    if args.command == "taskpack":
        try:
            if args.taskpack_command == "list":
                for identifier in TASKPACKS:
                    metadata = taskpack_metadata(identifier)
                    print(
                        f"{identifier}\t{len(metadata['tasks'])} tasks\t"
                        f"{metadata['canonical_digest']}"
                    )
                return 0
            metadata = taskpack_metadata(args.taskpack)
            if args.taskpack_command == "path":
                print(metadata["path"])
            else:
                print(json.dumps(metadata, indent=2, sort_keys=True))
            return 0
        except ResourceError as exc:
            print(f"taskpack error: {exc}", file=sys.stderr)
            return 2
    if args.command == "study":
        try:
            if args.study_command == "quickstart":
                result = run_quickstart(output=args.output)
            elif args.study_command == "run":
                generation_config = None
                if args.generation_config:
                    generation_config = json.loads(
                        args.generation_config.read_text(encoding="utf-8")
                    )
                    if not isinstance(generation_config, dict):
                        raise StudyError("generation config must be a JSON object")
                result = run_study(
                    args.taskpack,
                    command=args.generator_command,
                    label=args.label,
                    interface_label=args.interface_label,
                    output=args.output,
                    full=args.full,
                    tasks=args.tasks,
                    samples=args.samples,
                    generate_only=args.generate_only,
                    generation_config=generation_config,
                )
            else:
                result = evaluate_saved_responses(
                    args.taskpack, responses=args.responses, output=args.output
                )
        except (
            OSError,
            json.JSONDecodeError,
            ResourceError,
            StudyError,
            subprocess.SubprocessError,
        ) as exc:
            print(f"study failed: {exc}", file=sys.stderr)
            return 2
        for key in ("mode", "report_count", "functional_pass", "gap_members", "responses", "summary", "profile", "evidence", "first_report"):
            if key in result:
                print(f"{key:16}{result[key]}")
        if result.get("failures"):
            print(f"failures        {len(result['failures'])}", file=sys.stderr)
            return 2
        if args.study_command != "run" or not args.generate_only:
            print(f"read            {result['profile']}")
            print(
                f"interpret       {shlex.quote(sys.executable)} -m svgap explain "
                f"--report-only {shlex.quote(result['first_report'])}"
            )
            if args.study_command == "quickstart":
                print(
                    "next            connect your generator with `svgap study run`; "
                    "this fixture is not a model result"
                )
            else:
                print("next            inspect the profile before preparing a submission")
        return 0
    if args.command == "challenge":
        try:
            if args.challenge_command == "run":
                result = run_challenge(
                    args.track,
                    command=args.generator_command,
                    label=args.label,
                    run_id=args.run_id,
                    output=args.output,
                )
            else:
                result = score_challenge(args.task, args.submission)
                payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(payload, encoding="utf-8")
                if args.json or not args.output:
                    print(payload, end="")
            if args.challenge_command == "run":
                print(f"track           {result['track']}")
                print(f"overall         {result['overall']}")
                print(f"result          {args.output.resolve() / 'result.json'}")
            return 0 if result["overall"] == "pass" else 1
        except (OSError, ValueError, ChallengeError, ChallengeRunError, subprocess.SubprocessError) as exc:
            print(f"challenge failed: {exc}", file=sys.stderr)
            return 2
    if args.command == "init":
        output = args.output.resolve()
        source = args.source.resolve()
        if output.exists():
            print(f"refusing to overwrite existing manifest: {output}", file=sys.stderr)
            return 2
        if not source.is_file():
            print(f"source file does not exist: {source}", file=sys.stderr)
            return 2
        try:
            relative_source = source.relative_to(output.parent)
            draft = render_manifest_draft(relative_source, args.top, args.candidate_id)
        except ValueError as exc:
            print(f"cannot initialize manifest: {exc}", file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(draft, encoding="utf-8")
        print(f"manifest    {output}")
        print("status      incomplete: add functional evidence and explicit design intent")
        return 0
    if args.command == "validate":
        try:
            manifest = load_manifest(args.manifest)
            load_backend(manifest.backend)
            readiness = manifest_readiness(manifest)
        except (ManifestError, BackendError) as exc:
            print(f"manifest validation failed: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(readiness, indent=2, sort_keys=True))
        else:
            print(f"candidate   {readiness['candidate_id']}")
            print(f"status      {readiness['status']}")
            for item in readiness["answered"]:
                print(f"answered    {item}")
            for item in readiness["unanswered"]:
                print(f"unanswered  {item}")
        return 0 if readiness["status"] == "ready" else 3
    if args.command == "explain":
        try:
            payload = json.loads(args.report.read_text(encoding="utf-8"))
            explanation = explain_payload(payload)
        except (OSError, json.JSONDecodeError, ValueError, ReportValidationError) as exc:
            print(f"cannot explain report: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(explanation, indent=2, sort_keys=True))
        else:
            print(render_explanation(explanation), end="")
        if args.report_only:
            return 0
        return 1 if explanation["failed"] else (3 if explanation["unanswered"] else 0)
    if args.command == "digest":
        try:
            manifest = load_manifest(args.manifest)
        except ManifestError as exc:
            print(f"manifest error: {exc}", file=sys.stderr)
            return 2
        print(canonical_file_set_digest(manifest.path.parent, manifest.sources))
        return 0
    if args.command == "check":
        return check(args.manifest, args.skip_functional, args.json, args.fail_on)
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
    if args.command == "trace-normalize":
        try:
            trace = trace_from_csv(
                args.csv,
                trace_id=args.trace_id,
                candidate_digest=args.candidate_digest,
                observer_name=args.observer,
                observer_version=args.observer_version,
                sampling=args.sampling,
            )
        except TraceError as exc:
            print(f"trace normalization failed: {exc}", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(trace.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"trace       {args.output}")
        print(f"digest      {trace_digest(trace)}")
        return 0
    if args.command == "compare-traces":
        try:
            result = compare_traces(
                load_trace(args.golden),
                load_trace(args.observed),
                max_shift=args.max_shift,
                warmup_samples=args.warmup_samples,
                x_policy=args.x_policy,
            )
        except TraceError as exc:
            print(f"trace comparison inconclusive: {exc}", file=sys.stderr)
            return 3
        payload = asdict(result)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        elif result.equivalent:
            print(f"equivalent  yes (matched shift {result.matched_shift})")
        else:
            print("equivalent  no")
            if result.first_divergence:
                item = result.first_divergence
                print(
                    f"divergence  cycle={item.cycle} signal={item.signal} "
                    f"golden={item.golden} observed={item.observed}"
                )
        return 0 if result.equivalent else 1
    if args.command == "calibrate-adjudicator":
        try:
            result = run_calibration_suite(
                args.suite,
                max_shift=args.max_shift,
                warmup_samples=args.warmup_samples,
            )
        except TraceError as exc:
            print(f"calibration failed: {exc}", file=sys.stderr)
            return 2
        payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
            print(f"calibration {args.output}")
        else:
            print(payload, end="")
        return 0 if result["status"] == "pass" else 1
    if args.command == "adjudicate":
        if args.instrumenter == "reset-release-skew":
            try:
                ResetReleaseSkewInstrumenter().trace_for_seed(0)
            except InstrumenterUnavailable as exc:
                print(str(exc), file=sys.stderr)
                return 4
        missing = [
            name
            for name, value in (
                ("--candidate-id", args.candidate_id),
                ("--rule-id", args.rule_id),
                ("--golden", args.golden),
                ("--calibration-suite", args.calibration_suite),
                ("--output", args.output),
            )
            if not value
        ]
        if missing or not args.observed:
            print(
                "mock-prerecorded adjudication requires "
                + ", ".join([*missing, *([] if args.observed else ["--observed"])]),
                file=sys.stderr,
            )
            return 2
        try:
            calibration = run_calibration_suite(
                args.calibration_suite,
                max_shift=args.max_shift,
                warmup_samples=args.warmup_samples,
            )
            golden = load_trace(args.golden)
            traces = {index: load_trace(path) for index, path in enumerate(args.observed)}
            result = adjudicate_prerecorded(
                candidate_id=args.candidate_id,
                rule_id=args.rule_id,
                golden=golden,
                instrumenter=MockPrerecordedInstrumenter(traces),
                seeds=list(traces),
                semantics_name=args.semantics,
                semantics_version=args.semantics_version,
                calibration_status=calibration["status"],
                calibration_suite_digest=calibration["suite_digest"],
                max_shift=args.max_shift,
                warmup_samples=args.warmup_samples,
            )
        except TraceError as exc:
            print(f"adjudication inconclusive: {exc}", file=sys.stderr)
            return 3
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"verdict     {result['verdict']}")
        print(f"report      {args.output}")
        return {"hazard_demonstrated": 1, "no_divergence_observed": 0}.get(
            result["verdict"], 3
        )
    if args.command == "challenge-score":
        try:
            result = score_challenge(args.task, args.submission)
        except ChallengeError as exc:
            print(f"challenge scoring failed: {exc}", file=sys.stderr)
            return 2
        payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
            print(f"result      {args.output}")
        if args.json or not args.output:
            print(payload, end="")
        return 0 if result["overall"] == "pass" else 1
    if args.command == "submission":
        try:
            if args.submission_command == "init":
                manifest = initialize_submission(
                    args.evidence,
                    args.output,
                    submission_id=args.submission_id,
                    title=args.title,
                    track=args.track,
                    configuration_label=args.configuration_label,
                    provenance_level=args.provenance_level,
                    taskpack_id=args.taskpack_id,
                    taskpack_version=args.taskpack_version,
                    contributor=args.contributor,
                    provider=args.provider,
                    model_id=args.model_id,
                    attestor=args.attestor,
                    attestation=args.attestation,
                )
                print(f"submission  {args.output.resolve()}")
                print(f"id          {manifest['submission_id']}")
                return 0
            if args.submission_command == "validate":
                manifest, artifacts = validate_submission(
                    args.directory, denylist=args.denylist
                )
                print(f"valid       {manifest['submission_id']}")
                print(f"artifacts   {len(artifacts)}")
                return 0
            if args.submission_command == "bundle":
                digest = bundle_submission(
                    args.directory, args.output, denylist=args.denylist
                )
                print(f"bundle      {args.output.resolve()}")
                print(f"sha256      {digest}")
                return 0
            if args.submission_command == "from-harbor":
                manifest = initialize_submission_from_harbor(
                    args.job,
                    args.dataset,
                    args.output,
                    submission_id=args.submission_id,
                    title=args.title,
                    provenance_level=args.provenance_level,
                    contributor=args.contributor,
                    configuration_label=args.configuration_label,
                    provider=args.provider,
                    model_id=args.model_id,
                    attestor=args.attestor,
                    attestation=args.attestation,
                )
                for line in harbor_submission_receipt(manifest, args.output):
                    print(line)
                return 0
        except SubmissionError as exc:
            print(f"submission failed: {exc}", file=sys.stderr)
            return 2
    return 2


def doctor() -> int:
    missing_tools = []
    for tool in ("yosys", "iverilog", "vvp"):
        path = shutil.which(tool)
        print(f"{tool:10} {path or 'MISSING'}")
        if path is None:
            missing_tools.append(tool)
    if not missing_tools:
        version = subprocess.run(
            ["yosys", "-V"], capture_output=True, text=True, check=False
        ).stdout.strip()
        print(f"backend    reference-yosys 0.2 ({version})")
    backends, backend_errors = discover_backends()
    print(f"backends   {', '.join(sorted(backends))}")
    for name, hint in sorted(unavailable_backends().items()):
        print(f"optional   {name}: {hint}")
    for name, error in sorted(backend_errors.items()):
        print(f"plugin     {name}: {error}")
    if missing_tools:
        print()
        print("Install the missing open RTL prerequisites:")
        system = platform.system()
        if system == "Darwin":
            print("  macOS:          brew install yosys icarus-verilog")
        elif system == "Linux":
            print("  Ubuntu/Debian:  sudo apt-get update && sudo apt-get install -y yosys iverilog")
            print("  Fedora:         sudo dnf install -y yosys iverilog")
            print("  Arch:           sudo pacman -S yosys iverilog")
        elif system == "Windows":
            print("  Native Windows is not currently tested; use Docker Desktop or WSL2.")
        else:
            print(f"  No native installation recipe is maintained for {system or 'this platform'}.")
        print("Or use the pinned container with no host EDA installation:")
        print("  docker run --rm ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.9 doctor")
        print("Docs: https://shsridhar-beep.github.io/svgap/linux-install-and-doctor/")
    return 1 if missing_tools or backend_errors else 0


def run_demo_command(output: Path | None, print_json: bool) -> int:
    try:
        require_demo_tools()
        if output is None:
            with TemporaryDirectory(prefix="svgap-demo-") as directory:
                return _execute_demo(Path(directory), None, print_json)
        root = materialize_demo(output)
        return _execute_demo(root, root, print_json)
    except (DemoError, OSError, json.JSONDecodeError, ReportValidationError) as exc:
        print(f"demo failed: {exc}", file=sys.stderr)
        return 2


def _execute_demo(root: Path, preserved_output: Path | None, print_json: bool) -> int:
    if preserved_output is None:
        materialize_demo(root)
    with redirect_stdout(io.StringIO()):
        safe_code = check(root / "safe/manifest.toml", False, False)
        unsafe_code = check(root / "unsafe/manifest.toml", False, False)
    safe_report = validate_report_payload(
        json.loads((root / "safe/build/report.json").read_text(encoding="utf-8"))
    )
    unsafe_report = validate_report_payload(
        json.loads((root / "unsafe/build/report.json").read_text(encoding="utf-8"))
    )
    summary = build_demo_summary(safe_report, unsafe_report)
    if safe_code != 0 or unsafe_code != 1:
        summary["status"] = "fail"
    if preserved_output is not None:
        write_demo_summary(summary, root)
    if print_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_demo_summary(summary, preserved_output), end="")
    return 0 if summary["status"] == "pass" else 1


def check(
    manifest_path: Path,
    skip_functional: bool,
    print_json: bool,
    fail_on: str = "any",
) -> int:
    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    try:
        report = evaluate(
            manifest,
            skip_functional=skip_functional,
            manifest_label=portable_path(manifest.path),
        )
    except (BackendError, ImportError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if print_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print_summary(report, manifest.report_path)

    functional, structural = report.functional, report.structural
    if fail_on == "report-only":
        return 0
    if functional.status == "tool_error" or structural.status == "tool_error":
        return 2
    if fail_on == "gap":
        return 1 if report.gap_member else 0
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
