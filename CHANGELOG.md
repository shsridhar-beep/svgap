# Changelog

All notable changes will be documented here. The project uses semantic
versioning once the manifest and report contracts reach public v0.1.

## Unreleased

## 0.3.0-alpha.4 — 2026-07-06

### Added

- Installed-wheel `svgap study run` smoke and frozen full protocols over the
  packaged reset-release v0.2 taskpack.
- Credential-separated `svgap study evaluate-saved`, packaged taskpack
  discovery, and packaged diagnosis/repair challenge runners.
- Portable study summaries, evidence-file lists, static HTML profiles, and
  public generation-configuration metadata.
- Two reproducible open-weights baseline submissions and generated citable
  profile pages.
- Public Python evaluation API and taskpack resource discovery.

### Changed

- Candidate testbenches are copied into the run directory so reports and
  submission evidence do not retain workstation or installation paths.
- Result-submission PRs have one synchronization command and actionable CI
  guidance for generated registry/profile files.
- Current CI, container, action, model-study, and package documentation is
  coherent with alpha.4.

### Added

- Public Python API: `svgap.evaluate(manifest)` returns the layered
  `EvaluationReport`; `materialize_candidate`, `summarize_reports`, core
  types, and exceptions are exported from the top-level package, and the CLI
  `check` command now shares the same evaluation path. Documented in
  [docs/python-api.md](docs/python-api.md) with an Inspect-AI adapter sketch.

## 0.3.0-alpha.3 — 2026-07-05

### Added

- Provider-agnostic `command` generation adapter: any executable that reads a
  task prompt on stdin and prints the response on stdout can run a full
  taskpack, with the command string and a declared interface label recorded in
  provenance.
- [Evaluate your model](docs/evaluate-your-model.md): the end-to-end recipe
  for scoring an internal checkpoint or API endpoint against a taskpack
  without any provider CLI.
- `svgap check --fail-on {any,gap,report-only}` selects which outcomes gate
  the exit code; exit codes are now documented in the command help.
- A generic, immutable result-submission contract with public, attested-alias,
  and anonymous-case-study provenance levels, deterministic bundles, private
  publication denylists, and static citable evidence profiles.
- Runnable model-neutral diagnosis and repair starters plus a two-stage
  generation/evaluation workflow that keeps untrusted RTL out of the model
  credential environment.
- A frontier RTL handoff collaboration RFC with explicit response, credit, and
  authorship expectations.

## 0.3.0-alpha.2 — 2026-07-05

### Changed

- Replaced withheld provider model identifiers with stable public configuration
  aliases across repository history, release artifacts, and result provenance.
- Reissued package, container, and archival metadata from the sanitized source
  history.

## 0.3.0-alpha.1 — 2026-07-05

### Added

- Intent-preserving `init` and `validate` onboarding commands and an `explain`
  command that exposes answered, failed, and unanswered production questions.
- Strict digital trace, calibration, and adjudication contracts with a
  prerecorded mock calibration suite.
- Frontier-model generation, diagnosis, and repair challenge contracts and a
  multidimensional `challenge-score` workflow.
- A one-command `svgap demo`, bring-your-own-RTL tutorial, and MkDocs site.
- A schema-validated public result registry with reproducible generation,
  diagnosis, and repair profiles.
- A first exploratory diagnosis/repair baseline that exposes distinct
  epistemic and structural-repair failure modes without ranking models.

### Safety boundary

- The reset-release perturbation instrumenter is an unavailable capability
  marker with no rewrite, skew injection, execution, or candidate-result code
  pending patent and employer review.

## 0.2.0-alpha.1 — 2026-07-04

### Added

- Existential research scope and compact research artifact.
- Content-bound imported functional results and example integration.
- Discoverable third-party checker backend registry and SDK.
- Strict report contract plus SARIF and static HTML export.
- Reset-release taskpack v0.2 with corrected timer intent and calibrated safe/
  unsafe references for all eight tasks.
- Pinned OSS CAD Suite container, reusable GitHub Action, Python 3.11–3.13 CI,
  release automation, governance, support, and community launch materials.

### Changed

- Runtime and package versions now agree.
- Public artifact verification checks exact candidate/file sets and report
  semantics in CI.
- Research positioning treats the reset count as a worked mechanism
  demonstration, not a prerequisite population estimate.

## 0.1.0-alpha.1 — 2026-07-02

### Added

- Versioned TOML candidate manifest and JSON report schema.
- Functional command runner with explicit failure states.
- Yosys-backed reference structural oracle.
- Four paired CDC/RDC structural-validity witnesses.
- Gap aggregation command.
- Research protocol, limitations, architecture, and contributor guidance.
- Frozen-task generation and reset-release replication harnesses.
- Deterministic study summaries and portable artifact export.
- Secret-keyed blinded adjudication packets.
- Explicit `compile_error` functional status.
- Adversarial oracle validation for clock intent, reset waivers, and synchronizer stages.
- Blinded four-configuration synthetic adjudication with repeat-stability and
  agreement analysis, explicitly separated from human expert review.
- Deterministic, path-free public export of all 72 reset-release candidates.
- Search-bounded prior-art and novelty positioning through June 2026.

### Changed

- Human adjudication blinding for the published taskpack is documented as
  procedural now that the model-labeled candidate bundle is public.
- Synthetic adjudication records the vendor overlap between reviewer and
  generator configurations.
- Citation metadata carries the release version, author affiliation, and
  ORCID.
