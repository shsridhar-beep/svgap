# A test pass can hide a hardware mistake

Most coding-agent evals ask one question: did the generated program pass its
tests? For chip-design code, that can miss an important class of mistakes. A
design can behave correctly in the supplied simulation while being wired in a
way that violates a hardware rule in the prompt.

This dataset turns that possibility into a small, reproducible experiment.
Each of its eight SystemVerilog tasks asks an agent to build ordinary control
logic such as a counter, timer, or state machine. The task also says how reset
must be released. Reset puts circuit state into a known starting value. Its
release must reach ordinary state through the requested clock-aligned path.

The evaluator asks two questions about the same generated design:

1. Did it pass the simulation tests?
2. Does the circuit wiring obey the stated reset rule?

The interesting case is a design that passes question 1 and fails question 2.
Harbor records that result as `gap_member = 1`.

You do not need to be a reset-domain expert to try the experiment. If you work
on agent evaluation, the central research question is familiar: what important
requirements remain invisible when an eval stops at test success?

## Try the evaluator without a model key

You need Harbor and a running Docker daemon. The built-in Oracle installs the
known-good answer for each task, which lets you check the complete pipeline
before connecting a model:

```bash
harbor run \
  -d svgap/svgap-reset-release@0.2 \
  -a oracle \
  -o jobs/svgap-oracle \
  --n-concurrent 1
```

All eight tasks should receive `reward = 1`. The evaluator image already
contains the open-source simulation and circuit-analysis tools, so the host
does not need an EDA installation.

## Run an agent

Use any agent supported by Harbor:

```bash
harbor run \
  -d svgap/svgap-reset-release@0.2 \
  -a YOUR_AGENT \
  -m YOUR_MODEL \
  -o jobs/svgap-agent \
  --n-concurrent 1 \
  --n-attempts 1
```

Then inspect the job:

```bash
harbor view jobs/svgap-agent
```

The verifier compiles and simulates generated RTL. Treat that code as
untrusted input and run it on an isolated host. The first run may take longer
while Harbor prepares the agent environment.

## What happened in the first public run

One complete Codex `gpt-5.5` run produced:

| Result | Tasks |
|---|---:|
| Passed the simulation tests | 7 / 8 |
| Passed both the tests and the wiring rule | 5 / 8 |
| Passed the tests but failed the wiring rule | 2 / 8 |
| Unanswered checks or tool failures | 0 / 8 |

The two revealing cases were `reset-counter` and `reset-credits`. Both passed
their simulations. Both connected reset directly to state that the prompt
required to resume through a clock-aligned release path.

[Explore the readable evidence](https://shsridhar-beep.github.io/svgap/result-profiles/codex-gpt-5.5-reset-v02-01/)
or inspect the
[content-addressed reports](https://github.com/shsridhar-beep/svgap/tree/main/results/submissions/codex-gpt-5.5-reset-v02-01).

This is one run, not a model ranking or an estimate of how often the problem
occurs. We are publishing it because the two failures are concrete examples
of a broader eval question worth testing across more agents and task families.

## Reading Harbor's metric names

| Harbor metric | Plain-language meaning |
|---|---|
| `functional_accept` | The simulation tests passed. |
| `structural_accept` | The generated circuit obeyed the stated wiring rule. |
| `gap_member` | Tests passed, but the wiring rule failed on the same design. |
| `reward` | Both checks passed. |
| `unknown` | At least one configured question was not answered. |
| `tool_error` | An evidence-producing tool failed. |

An unanswered question or tool failure never becomes a pass. Each trial keeps
the candidate RTL, the full SV-Gap JSON report, the Harbor verdict, and a
readable HTML evidence page. The number is a convenient summary; the retained
evidence shows why the design received it.

## Help test the research question

We would like collaborators to run different agents, examine surprising
cases, challenge the rule, and propose tasks where test success may conceal a
different hardware mistake. A complete Harbor job can become a reviewable
SV-Gap contribution without cloning this repository.

Install SV-Gap 0.3.0 alpha 7 or newer, then point the importer at the job
directory Harbor created:

```bash
pip install "svgap>=0.3.0a7"

svgap submission from-harbor jobs/svgap-agent/JOB_DIRECTORY \
  --dataset svgap/svgap-reset-release@0.2 \
  --id YOUR-SUBMISSION-ID \
  --title "YOUR TITLE" \
  --provenance-level public \
  --provider YOUR_PROVIDER \
  --contributor "YOUR NAME" \
  --output results/submissions/YOUR-SUBMISSION-ID
```

The importer checks that the job is complete and that its task versions,
reports, verdicts, and numeric scores agree. Open a pull request containing
the resulting directory. Harbor provides the common execution surface; the
[SV-Gap repository](https://github.com/shsridhar-beep/svgap) keeps the
reviewed evidence and the limits on what each result can support. Uploading a
job to Harbor Hub is optional and is not required to contribute.

Other useful contributions include counterexamples, critiques of the reset
rule, new task ideas, and reviews of the open evaluation method. See
[how to submit results](https://shsridhar-beep.github.io/svgap/submitting-results/)
or start a discussion in the
[SV-Gap repository](https://github.com/shsridhar-beep/svgap/discussions).

## Scope

This dataset is intentionally narrow: eight digital RTL tasks and one reset
rule. It does not claim silicon signoff, certification, comprehensive CDC or
RDC coverage, or hardware safety. Its purpose is to make one blind spot of
test-only evaluation visible, inspectable, and open to challenge.

The tasks are `reset-config`, `reset-counter`, `reset-credits`, `reset-events`,
`reset-fsm`, `reset-status`, `reset-timer`, and `reset-watchdog`.

## Learn more

- [SV-Gap source and methodology](https://github.com/shsridhar-beep/svgap)
- [Frozen reset-replication taskpack](https://github.com/shsridhar-beep/svgap/tree/main/taskpacks/reset-replication-v0.2)
- [Harbor adapter source and maintainer guide](https://github.com/shsridhar-beep/svgap/tree/main/integrations/harbor)
