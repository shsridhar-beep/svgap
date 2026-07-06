# Python API

`import svgap` exposes the same evaluation path as the CLI, for eval
harnesses and pipelines that live in Python. The contract is unchanged:
setup errors raise; measurement outcomes — including `unknown` and
`tool_error` — come back inside the report, never as exceptions; a
structural `pass` means no configured finding, not verified safety.

## Evaluate one candidate

```python
import svgap

report = svgap.evaluate("path/to/manifest.toml")

report.functional.status   # pass | fail | compile_error | unknown | tool_error | not_run
report.structural.status   # pass | fail | unknown | tool_error
report.gap_member          # functional pass AND structural fail
report.structural.findings # rule_id, severity, message, evidence
```

`evaluate` accepts a path or a loaded `Manifest`, and writes the
schema-versioned report to the manifest's report path by default
(`write_report=False` returns the report without touching disk).
`skip_functional=True` records `not_run` instead of executing the
functional command; a candidate whose functional result was not observed is
never counted as a gap member.

## Score a raw model response

`materialize_candidate` is the library form of `svgap pilot`: it normalizes
a raw model response against a taskpack task and returns a ready manifest.

```python
import svgap

manifest = svgap.materialize_candidate(
    task_dir,            # taskpack task directory containing task.toml
    response_path,       # raw model output (fenced or bare RTL)
    "my-model-a",        # configuration label recorded in provenance
    output_root,         # where the candidate and report will live
    run_id="my-model-a--sample-01",
)
report = svgap.evaluate(manifest)
```

## Aggregate a study

```python
reports = sorted(output_root.glob("*/*/report.json"))
summary = svgap.summarize_reports(reports)
```

## Exported surface

`evaluate`, `load_manifest`, `materialize_candidate`, `run_functional`,
`summarize_reports`, `load_backend`, `discover_backends`,
`validate_report_payload`, the `Manifest`, `EvaluationReport`,
`FunctionalResult`, `CheckResult`, and `Finding` types, and the
`ManifestError`, `BackendError`, and `ReportValidationError` exceptions.
Anything not exported from the top-level package is internal and may change
without notice.

## Inspect-AI adapter sketch

The following shows the shape of an [Inspect AI](https://inspect.aisi.org.uk)
task over a taskpack: the dataset is the task prompts, the solver is plain
generation, and the scorer materializes and evaluates each completion. It is
an illustrative integration, not a CI-tested artifact — pin your Inspect
version and validate against the calibrated taskpack references before
relying on it.

```python
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import generate

import svgap

TASK_ROOT = svgap.taskpack_root("reset-release-v0.2") / "tasks"
OUTPUT = Path("reports/generated/inspect-study")


def samples() -> list[Sample]:
    return [
        Sample(
            id=task_dir.name,
            input=(task_dir / "prompt.md").read_text(),
            target="structural_pass",
            metadata={"task_dir": str(task_dir)},
        )
        for task_dir in sorted(TASK_ROOT.iterdir())
        if (task_dir / "task.toml").is_file()
    ]


@scorer(metrics=[accuracy()])
def svgap_scorer():
    async def score(state, target: Target) -> Score:
        task_dir = Path(state.metadata["task_dir"])
        response = OUTPUT / "_responses" / f"{state.sample_id}.txt"
        response.parent.mkdir(parents=True, exist_ok=True)
        response.write_text(state.output.completion)
        manifest = svgap.materialize_candidate(
            task_dir, response, "inspect-run", OUTPUT, run_id=state.sample_id
        )
        report = svgap.evaluate(manifest)
        return Score(
            value=(
                report.functional.status == "pass"
                and report.structural.status == "pass"
            ),
            answer=report.structural.status,
            explanation=(
                f"functional={report.functional.status} "
                f"structural={report.structural.status} "
                f"gap_member={report.gap_member} "
                f"findings={[f.rule_id for f in report.structural.findings]}"
            ),
        )

    return score


@task
def svgap_reset_release() -> Task:
    return Task(dataset=samples(), solver=generate(), scorer=svgap_scorer())
```

The score's `explanation` deliberately carries the full layered outcome:
an Inspect accuracy number over this task is a harness convenience, not a
replacement for the profile — report `unknown` and `tool_error` counts
alongside it, and treat the result as taskpack-conditional per the
[interpretation rules](evaluate-your-model.md#interpretation-rules).

## Security note

Generated RTL is untrusted input to external EDA tools. The two-stage
isolation guidance in [evaluate your model](evaluate-your-model.md) applies
equally to library callers: evaluate unreviewed candidates in an isolated
environment, not on a credentialed workstation.
