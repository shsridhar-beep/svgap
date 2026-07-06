# Evaluate your model

!!! danger "Generated RTL is untrusted code"
    The local evaluator is not a security sandbox. A generated candidate is
    processed by external EDA tools and may contain simulator system tasks.
    Do not evaluate untrusted RTL on a workstation containing credentials or
    sensitive source trees. Use the isolated two-stage container path below for
    model or contributor outputs you have not inspected.

This is the end-to-end recipe for running your own model — an internal
checkpoint, an API endpoint, or any local runtime — through an SV-Gap
taskpack and producing the same layered result the published studies use.
No provider CLI is required.

Read the [research protocol](research-protocol.md) and
[research scope](research-scope-v0.2.md) before interpreting numbers. The
output is a taskpack-conditional detection count with explicit `unknown`
states, not a defect rate or a leaderboard entry.

## What the harness needs from you

One thing: a way to turn a task prompt into a model response. The contract is
deliberately minimal —

- the prompt arrives on **stdin**;
- the response (containing the RTL, fenced or bare) goes to **stdout**;
- a nonzero exit means generation failed for that task.

Everything else — response normalization, manifest construction, functional
simulation, structural checking, provenance hashes — is the harness's job.

## Path A: one command over a whole taskpack

Wrap your model in any executable. For an OpenAI-compatible endpoint:

```python
#!/usr/bin/env python3
# my_generate.py — stdin: prompt, stdout: response
import os, sys
from openai import OpenAI

client = OpenAI(base_url=os.environ.get("MY_BASE_URL"))
response = client.chat.completions.create(
    model=os.environ["MY_MODEL"],
    messages=[{"role": "user", "content": sys.stdin.read()}],
)
print(response.choices[0].message.content)
```

Start with the packaged smoke protocol: one calibrated task and one sample.
No source checkout is required:

```bash
svgap study run reset-release-v0.2 \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --interface-label "my-lab-harness 1.0" \
  --smoke \
  --output reports/generated/my-model-study
```

The output includes `study-summary.json`, `evidence-profile.html`, and
`evidence-files.txt`. Replace `--smoke` with `--full` to run the frozen eight
tasks with three samples each. Use `svgap taskpack show reset-release-v0.2` to
inspect the exact task list and canonical digest before a claim-bearing run.

Environment variables (API keys, endpoints) pass through to your command.
The prompt is never placed on the command line, and the recorded provenance
contains your command string and interface label — not your credentials.

Do not place credentials directly in `--command`: the command string is
retained as provenance. Prefer environment variables supplied to the generator.

## Recommended: separate generation from isolated evaluation

Generate responses in the credentialed host environment without invoking any
EDA tool:

```bash
svgap study run reset-release-v0.2 \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --interface-label "my-lab-harness 1.0" \
  --full \
  --generate-only \
  --output reports/generated/my-model-study
```

Then evaluate only the saved responses in a disposable, network-disabled
container. The evaluation container receives no model credentials and cannot
read the rest of the repository:

```bash
mkdir -p reports/evaluated/my-model-study

docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 256 \
  --memory 4g \
  --cpus 2 \
  --tmpfs /tmp:rw,nosuid,size=512m \
  -v "$PWD/reports/generated/my-model-study/_responses:/responses:ro" \
  -v "$PWD/reports/evaluated/my-model-study:/output:rw" \
  ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.4 \
  study evaluate-saved reset-release-v0.2 \
  --responses /responses \
  --output /output
```

Resource limits reduce accidental damage and denial-of-service risk; they do
not turn the reference evaluator into a formally verified sandbox. Apply your
organization's approved isolation controls for hostile-input evaluation.

## Path B: bring pre-generated responses

If generation already happened elsewhere, score each saved response directly:

```bash
svgap pilot "$(svgap taskpack path reset-release-v0.2)/tasks/reset_counter" \
  response.txt --model my-model-a --run-id my-model-a--sample-01 \
  --output reports/generated/my-model-study
```

`pilot` normalizes the response, materializes the candidate with the task's
declared intent, runs the functional testbench and the structural oracle, and
writes a schema-validated `report.json`.

## Path C: stay in Python

Eval harnesses that live in Python (Inspect AI, custom loops) can skip the
shell entirely: `svgap.materialize_candidate` plus `svgap.evaluate` are the
library form of the same pipeline, and the [Python API](python-api.md) page
includes an Inspect-AI adapter sketch.

## Aggregate and read the result

```bash
svgap summarize reports/generated/my-model-study
svgap gap reports/generated/my-model-study/*/*/report.json
svgap export reports/generated/my-model-study/*/*/report.json \
  --html my-model-study.html
svgap explain reports/generated/my-model-study/<run>/<task>/report.json
```

`summarize` is deterministic over the report set. `gap` prints the detected
structural-validity gap over functionally passing, structurally determinate
candidates. `explain` translates one report into answered, failed, and
unanswered production questions.

## Interpretation rules

- Repeated calls to one configuration are generation events, not independent
  samples; report per-task groupings, not just totals.
- Exact duplicate normalized outputs are disclosed by the summary; do not
  count them as independent evidence.
- `unknown` and `tool_error` are never structural passes. Report them.
- The number you get is conditional on this taskpack and the configured
  rules. It does not rank models or estimate population prevalence.

## Withheld model identifiers

If your lab cannot name a checkpoint, use a stable configuration alias as the
`--label` and record the true identifier privately. The published studies use
this pattern themselves (`openai-frontier-a` is such an alias); the report
schema treats labels as opaque configuration names.

## Gate a generation pipeline in CI

`svgap check` exits nonzero on failing, unknown, or tool-error outcomes by
default. To gate only on the headline condition — functionally accepted but
structurally failing RTL:

```bash
svgap check candidate/manifest.toml --fail-on gap
```

`--fail-on report-only` writes the report and never gates. Exit codes:
`0` pass, `1` fail, `2` tool or manifest error, `3` unknown.

## Share what you found

- Post the profile and harness friction in
  [Discussions](https://github.com/shsridhar-beep/svgap/discussions);
  friction reports directly shape the roadmap.
- The [challenges contract](frontier-model-research.md) adds diagnosis and
  repair tracks beyond generation.
- Create a contribution-ready directory with `svgap submission init`, validate
  it with a private denylist using `svgap submission validate`, and open a pull
  request beneath `results/submissions/`. See
  [Submit a result](submitting-results.md).
