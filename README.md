# SV-Gap

[![CI](https://github.com/shsridhar-beep/svgap/actions/workflows/ci.yml/badge.svg)](https://github.com/shsridhar-beep/svgap/actions/workflows/ci.yml)
[![Documentation](https://github.com/shsridhar-beep/svgap/actions/workflows/docs.yml/badge.svg)](https://shsridhar-beep.github.io/svgap/)
[![PyPI](https://img.shields.io/pypi/v/svgap.svg?cacheSeconds=300)](https://pypi.org/project/svgap/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21198938-blue.svg)](https://doi.org/10.5281/zenodo.21198938)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://github.com/shsridhar-beep/svgap/blob/main/LICENSE)

**Make the gap between “passes the benchmark” and “reviewable by a chip-design
team” explicit.**

SV-Gap is an open evaluation layer for AI-generated digital RTL. It preserves
the functional result, adds declared design intent and structural evidence, and
reports which production questions are answered, failed, or still unknown.

> Supply RTL and evaluation evidence. Receive a reviewable account of what that
> evidence establishes, what it contradicts, and what evidence would resolve
> the remaining uncertainty.

![SV-Gap turns an offline pass into an evidence profile](https://shsridhar-beep.github.io/svgap/assets/svgap-demo.svg)

## Choose your first step

| Goal | Start here | Time |
|---|---|---:|
| Name one unanswered production question | [Open a one-sentence issue](https://github.com/shsridhar-beep/svgap/issues/new?template=production_question.yml) | 60 seconds |
| Understand the result without installing anything | [Inspect the controlled result](https://shsridhar-beep.github.io/svgap/controlled-result/) or a [public model profile](https://shsridhar-beep.github.io/svgap/result-profiles/openweights-deepseek-coder-v2-16b-reset-v02/) | 2 minutes |
| Create and interpret a local evidence profile | `svgap study quickstart --output my-first-svgap-study` after installation | 2 minutes |
| Evaluate one model or agent | [Run the packaged smoke study](https://shsridhar-beep.github.io/svgap/evaluate-your-model/) | about 10 minutes after prerequisites |
| Run or report the Harbor experiment | [Use the eight-task Harbor path](https://shsridhar-beep.github.io/svgap/harbor/) | 2 minutes to report; run time varies |
| Scope a qualification experiment | [Request a research call](https://github.com/shsridhar-beep/svgap/issues/new?template=collaboration.yml) or [email the maintainer](mailto:shsridhar@nvidia.com?subject=SV-Gap%20research%20call) | 30 minutes |

Do not send proprietary RTL or confidential constraints through GitHub or
email. A public or synthetic artifact is enough for the first experiment.

## What the demo proves

```text
candidate  functional  structural  finding
safe       pass        pass        none
unsafe     pass        fail        REF-RDC-001
```

Both implementations pass the supplied functional test. Declared reset-release
intent and configured structural evidence distinguish them. This is an
executable existence result: it is not a defect-rate estimate, certification,
or silicon signoff.

## Supported today

| Surface | Current support | Boundary |
|---|---|---|
| Domain | AI-generated digital RTL | Analog and mixed-signal design are out of scope |
| Initial properties | Documented CDC/RDC and power-on reset-coverage patterns | Not comprehensive structural signoff |
| Research tracks | Generation, diagnosis, and repair | Profiles remain multidimensional; no scalar leaderboard |
| Functional evidence | Executed commands or digest-bound imported results | Evidence quality remains visible |
| Structural backend | Narrow open Yosys reference backend | Backend `pass` means no configured finding, not a true negative |
| Outcomes | `pass`, `fail`, `unknown`, `tool_error` | Missing intent or coverage never becomes `pass` |
| Platforms | Python 3.11–3.13; tested on macOS and Linux | Native Windows is not tested; use Docker Desktop or WSL2 |

Read the full [methodology](https://shsridhar-beep.github.io/svgap/methodology/),
[limitations](https://shsridhar-beep.github.io/svgap/limitations/), and [scope boundary](https://shsridhar-beep.github.io/svgap/scope-boundary/)
before making claim-bearing use of a profile.

## Trust and security boundary

- SV-Gap runs locally and performs no telemetry or artifact uploads. A model
  generator command supplied by the user may contact its configured provider.
- Generated RTL and functional commands are untrusted input. Do not evaluate
  them on a workstation containing credentials or sensitive source trees.
- The recommended two-stage workflow generates in the credentialed environment
  and evaluates saved responses in a network-disabled, read-only container.
- Only open-source runtime tools are assumed by default. Tool versions,
  provenance, unknowns, and errors remain in the evidence record.
- SV-Gap is evidence infrastructure, not a replacement for organizational
  review, commercial verification, or signoff.
- GitHub's automatic contributor graph reflects commit authors, including
  disclosed AI assistance; it is not a roster of verified human researchers.
  Maintainer accountability and accepted contributions are documented in
  [CONTRIBUTORS.md](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTORS.md).

Follow the [isolated evaluation recipe](https://shsridhar-beep.github.io/svgap/evaluate-your-model/#recommended-separate-generation-from-isolated-evaluation)
for model or contributor outputs you have not reviewed.

## Run locally

The browser result above is the fastest path from a new visit to the research
idea. The container includes the complete open RTL toolchain, but its first
large image pull depends on network speed; the demo itself runs in
under two minutes once the image is cached:

```bash
docker run --rm ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.9 demo
```

For a native macOS installation:

```bash
brew install yosys icarus-verilog
python3 -m venv .venv
.venv/bin/python -m pip install svgap==0.3.0a9
.venv/bin/svgap doctor
.venv/bin/svgap study quickstart --output my-first-svgap-study
```

`quickstart` evaluates a clearly labelled bundled unsafe fixture, writes a
portable HTML evidence profile, and prints the exact report to pass to
`svgap explain`. It teaches the workflow; it is not a model result. Run
`.venv/bin/svgap demo` for the paired safe/unsafe executable witness.

Ubuntu, Debian, CI, and troubleshooting instructions are in
[Linux installation and doctor checks](https://shsridhar-beep.github.io/svgap/linux-install-and-doctor/).
If `doctor` finds a missing prerequisite, it prints the installation command
or container fallback rather than leaving the user at a missing-tool report.

## Evaluate a model or existing RTL

Any model harness can participate: read a prompt from stdin and write the model
response to stdout.

```bash
svgap study run reset-release-v0.2 \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --smoke \
  --output my-first-svgap-study
```

The run produces a portable summary, evidence-file list, reports, and static
HTML profile. Replace `--smoke` with `--full` for the frozen eight-task,
three-sample protocol. See [Evaluate your model](https://shsridhar-beep.github.io/svgap/evaluate-your-model/).

For existing RTL, use `svgap init`, `validate`, `check`, and `explain`; the
[bring-your-own-RTL tutorial](https://shsridhar-beep.github.io/svgap/bring-your-own-rtl/) includes an executable
manifest and imported-result path. Python integrations can call
`svgap.evaluate(manifest)`; see the [Python API](https://shsridhar-beep.github.io/svgap/python-api/).

## Current evidence

- Five controlled witness pairs have identical functional outcomes and
  different configured structural outcomes.
- A frozen 72-call reset-release study contains 57 functional passes; at least
  14 contain the declared raw-reset pattern.
- A heuristic inventory covers 508 public RTL-generation tasks across
  VerilogEval, RTLLM, and CVDP.
- A separate audit of those 508 tasks inventories stated power-on intent and
  recognizable unknown-initial-state scoring.
- Two reproducible open-weights profiles demonstrate the public submission
  path; they are maintainer-produced anchors, not independent replications.

[Controlled result](https://shsridhar-beep.github.io/svgap/controlled-result/) ·
[Reset result](https://shsridhar-beep.github.io/svgap/reset-replication-result/) ·
[Benchmark audit](https://shsridhar-beep.github.io/svgap/benchmark-audit/) ·
[Power-on audit](https://shsridhar-beep.github.io/svgap/power-on-benchmark-audit/) ·
[Evidence profiles](https://shsridhar-beep.github.io/svgap/results/) ·
[Compact research note](https://shsridhar-beep.github.io/svgap/compact-research-note/)

These are bounded existence, taskpack-conditional, and heuristic results. They
are not a population defect estimate, general model ranking, or signoff claim.

## Collaborate

The preferred entry point is one question a functional RTL evaluation leaves
unanswered. A 30-minute scoping call should end with a bounded qualification
experiment, explicit claim boundary, and go/revise/stop decision.

- [Research-call intake](https://github.com/shsridhar-beep/svgap/issues/new?template=collaboration.yml)
- [Report a Harbor run or setup blocker](https://github.com/shsridhar-beep/svgap/issues/new?template=run_report.yml)
- [Current research collaboration pulse](https://shsridhar-beep.github.io/svgap/community-pulse/)
- [Private maintainer email](mailto:shsridhar@nvidia.com?subject=SV-Gap%20research%20call)
- [Design-partner workflow](https://shsridhar-beep.github.io/svgap/design-partner-workflow/)
- [One-page experiment contract](https://shsridhar-beep.github.io/svgap/experiment-contract-template/)
- [Replication and co-design discussion](https://github.com/shsridhar-beep/svgap/discussions/18)

Joining a call is not contributor status. Named credit follows accepted,
attributable protocol design, redistributable evidence, task design, analysis,
validation, documentation, or code. See [Contributors](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTORS.md) and
[Contributing](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTING.md).

## Extend and integrate

- [Submit a result](https://shsridhar-beep.github.io/svgap/submitting-results/)
- [Write a checker backend](https://shsridhar-beep.github.io/svgap/backend-sdk/)
- [Integrate an existing benchmark](https://shsridhar-beep.github.io/svgap/integrating-existing-benchmarks/)
- [Use the GitHub Action or container](https://shsridhar-beep.github.io/svgap/ci-and-container/)
- [Good first issues](https://github.com/shsridhar-beep/svgap/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- [Roadmap](https://github.com/shsridhar-beep/svgap/blob/main/ROADMAP.md)

## Project status and citation

SV-Gap is early research software maintained by
[Shraddha S](https://github.com/shsridhar-beep), who is accountable for project
direction, incorporated changes, research claims, and releases. Material AI
development assistance is disclosed in [CONTRIBUTORS.md](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTORS.md).

SV-Gap is an independent open-source research project. Cite the exact release used. The
independently fetched and scanned alpha.5 archive is
[doi:10.5281/zenodo.21226232](https://doi.org/10.5281/zenodo.21226232). The
[all-versions DOI](https://doi.org/10.5281/zenodo.21198938) always resolves to
the latest archived release.

Apache-2.0. External tools and imported datasets retain their own licenses.
