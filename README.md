# SV-Gap

[![CI](https://github.com/shsridhar-beep/svgap/actions/workflows/ci.yml/badge.svg)](https://github.com/shsridhar-beep/svgap/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21152349.svg)](https://doi.org/10.5281/zenodo.21152349)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**Production-readiness evaluation for AI-generated RTL.**

Functional tests answer whether sampled behavior looked correct. They do not
answer whether the RTL is structurally safe to deploy in silicon. SV-Gap makes
that missing evaluation layer explicit, starting with clock-domain crossing
(CDC) and reset-domain crossing (RDC) risks.

> **Early reference implementation.** SV-Gap v0.1 is research software, not a
> replacement for commercial CDC/RDC signoff. Its built-in reference oracle is
> deliberately narrow, transparent, and validated only on the shipped fixtures.

## The gap it measures

```text
generated RTL + design intent + functional result
                       |
                       v
               structural checks
                       |
                       v
        pass | fail | unknown | tool_error
```

The **detected** structural-validity gap is the fraction of functionally passing,
structurally determinate candidates that trigger at least one configured
structural rule. Until full-case expert adjudication establishes false negatives,
it is a detection fraction—not a validated defect rate.

## Thirty-second tour

Prerequisites are Python 3.11+, Yosys, and Icarus Verilog. On macOS, install
the RTL tools with `brew install yosys icarus-verilog`. From the repository
root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/svgap doctor
.venv/bin/svgap check examples/level_crossing/unsafe/manifest.toml
.venv/bin/svgap check examples/level_crossing/safe/manifest.toml
```

The unsafe example is expected to pass its functional test and fail the
structural oracle. The safe example is expected to pass both.

The four controlled witness pairs reproduce this distinction end to end; see
the [controlled result](docs/controlled-result.md). Its deliberately balanced
`0.500` gap validates the harness and must not be interpreted as defect
prevalence.

## What you can do here

**Gate your own generation pipeline.** Write a manifest declaring your
design's clocks, resets, and asynchronous groups, then run `svgap check`
after your functional tests. Your evaluation gains a structural dimension
with explicit `unknown` and `tool_error` states instead of silent passes.
The [architecture](docs/architecture.md) doc describes the manifest contract;
`examples/` holds working templates.

**Rerun the reset study on your model.** The
[reset-release taskpack](taskpacks/reset-replication-v0.1/) ships the frozen
prompts, testbenches, and harness behind the `14/57` result. Generate your
own samples, score them with the same oracle, and you have a comparable
detection count for your model in an afternoon — see the
[research protocol](docs/research-protocol.md) before interpreting it.

**Audit a benchmark for structural intent.** `svgap audit` censuses a task
set for multi-clock interfaces, declared clock/reset intent, and native
CDC/RDC scoring — the same tooling behind the
[benchmark audit](docs/benchmark-audit.md). Point it at your own benchmark to
learn whether structural safety is even scorable from your task metadata.

**Extend the oracle.** The backend boundary is one function:
`check(manifest) -> CheckResult`. Wrap a commercial checker, write an
independent second implementation, or contribute a witness pair or task pack
— the [open issues](https://github.com/shsridhar-beep/svgap/issues) are
scoped entry points, and two designed-but-unbuilt v0.2 components
([perturbation adjudication](docs/perturbation-adjudication.md),
[X-optimism and metastability rules](docs/category-expansion-xprop-metastability.md))
are documented and waiting.

An automated inventory of 508 public RTL-generation tasks — from
[VerilogEval](https://github.com/NVlabs/verilog-eval),
[RTLLM](https://github.com/hkust-zhiyao/RTLLM), and
[CVDP](https://github.com/NVlabs/cvdp_benchmark) — detected 12
multi-clock tasks (2.4%) and no recognizable native CDC/RDC scoring artifacts.
These are heuristic detector counts, not a validated census; see the
[benchmark audit](docs/benchmark-audit.md) for definitions, revisions, and
interpretation limits.

In a first 18-candidate generation pilot, all 18 candidates passed their
functional tests; 3 of 16 structurally determinate candidates failed the reset
release rule, while 2 were held out as Yosys frontend tool errors. This is an
exploratory case-study result, not a prevalence estimate or model ranking. See
the [generation pilot](docs/pilot-result.md).

In a locally frozen 72-call reset-release taskpack, 57 outputs passed the supplied
Icarus tests. At least 14 of those 57 contain an author-confirmed direct raw
asynchronous-reset connection to operational state despite a synchronized-
release requirement. Full-case independent review is pending, so `14/57` is a
lower-bound detection count, not a validated 24.6% defect rate. See the
[replication result](docs/reset-replication-result.md).

A blinded synthetic robustness panel used four reviewer configurations with two
isolated repeats each. Conservative consensus reproduced all 15 reference-oracle
positives (14 among the 57 functional passes), with nominal Krippendorff alpha
`0.989` and no unresolved target cases. This is not human expert validation; see
the [synthetic adjudication result](docs/synthetic-adjudication-result.md).

## What v0.1 includes

- A versioned intent manifest and normalized report contract.
- A Yosys-backed reference oracle for a small set of high-confidence patterns.
- Paired safe/unsafe examples with identical functional expectations.
- A six-task generation pack with response normalization and provenance hashes.
- A frozen eight-task reset-release replication with 72 portable generated-RTL
  candidates and content-addressed evidence.
- Blinded synthetic-review tooling with calibration, repeat stability, and
  agreement analysis, explicitly separated from human expert adjudication.
- Terminal and JSON reports with raw evidence and explicit inconclusive states.
- A backend interface intended for open and commercial checker adapters.

## What v0.1 does not claim

- Silicon signoff, exhaustive CDC/RDC coverage, or formal proof.
- General X-propagation or metastability modeling.
- Correctness without accurate clocks, resets, and asynchronous relationships.
- That every warning corresponds to a realizable field failure.

See [methodology](docs/methodology.md), [architecture](docs/architecture.md),
[limitations](docs/limitations.md), and [contributing](CONTRIBUTING.md) before
interpreting or extending results.

The frozen 72-candidate artifact is published under
[`artifacts/reset-replication-v0.1`](artifacts/reset-replication-v0.1) with
portable manifests, exact prompts, testbenches, reports, and content hashes.
The [synthetic adjudication protocol](docs/synthetic-adjudication.md) describes
the blinded robustness panel and why it is not human expert validation.

Public-release decisions and the remaining research-evidence boundary are
tracked in [release readiness](docs/release-readiness.md).
The skeptical [OpenAI Frontier A reanalysis](docs/skeptical-reanalysis.md) records why the
quantitative claims were narrowed and which release blockers remain.

## Contribution paths

1. Add a structural-risk task pack.
2. Add a checker backend.
3. Add a benchmark or functional-result adapter.
4. Contribute reproduced model outputs and expert-adjudicated evidence.

## Citing

Cite the archived release
([doi:10.5281/zenodo.21152349](https://doi.org/10.5281/zenodo.21152349));
machine-readable metadata is in [CITATION.cff](CITATION.cff).

## License

Apache-2.0. External tools and imported datasets retain their own licenses.
