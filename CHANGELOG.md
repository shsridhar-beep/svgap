# Changelog

All notable changes will be documented here. The project uses semantic
versioning once the manifest and report contracts reach public v0.1.

## Unreleased

### Added

- Acceptance-test suite for the `reference-naja` structural backend: the four
  CDC/RDC witness pairs and their rule IDs, gray-declaration and wildcard-gray
  cases, missing-intent (`unknown`), unparseable/missing-source (`tool_error`),
  report-schema validation, and a registry capability probe.
- Cross-oracle differential of `reference-naja` against the frozen 72-candidate
  reset-replication artifact: 72/72 rule-for-rule agreement with
  `reference-yosys`. Recorded in
  [docs/cross-oracle-naja-result.md](docs/cross-oracle-naja-result.md), including
  a najaeda-accepts / Yosys-rejects result for SystemVerilog function `return`.
- najaeda added to [THIRD_PARTY.md](THIRD_PARTY.md) (Apache-2.0), and a
  `reference-naja` backend doc covering license, the opt-in install, source
  locations, supported rules (REF-XPROP-001 abstains as `unknown`), the
  no-timeout gap, and known false-positive/false-negative classes.
- The `reference-naja` backend is packaged as the optional `naja` extra
  (`pip install "svgap[naja]"`, supported range `najaeda>=0.7.16,<0.8`); the
  default install is unchanged. `svgap doctor` reports an uninstalled optional
  backend with its install command without failing, and `load_backend` raises
  the same actionable hint.

### Fixed

- `reference-naja` now recognizes the wide packed-vector reset synchronizer
  (`logic [1:0] reset_sync; ...`, lowered by naja as one multi-bit `..._dffrn__wN`
  instance) by porting Yosys's wide vector-shift `$adff` fallback into
  `_reset_synchronizer_regs` (bit-0 inactive-constant load plus a strict shift
  chain, over `assign`-resolved D nets). This closes the packed-vector
  REF-RDC-001 false-positive class, raising cross-oracle agreement from 54/72 to
  72/72; an ordinary wide async-reset data register is still flagged.

## 0.3.0-alpha.8 - 2026-07-07

### Added

- A two-minute public Harbor run-report form for completed runs, partial runs,
  setup blockers, counterexamples, and requests for interpretation.
- A researcher-focused Harbor guide and a public collaboration pulse that
  distinguishes author-run evidence from independent replication.

### Changed

- Successful Harbor imports now print the retained report count, test-pass
  count, test-pass/rule-fail count, and voluntary public next steps.
- The Harbor dataset page now offers a low-commitment reporting path before a
  full evidence pull request.
- Project documentation names complete independent agent runs with inspectable
  evidence as the primary collaboration metric. No hidden usage telemetry was
  added.

## 0.3.0-alpha.7 - 2026-07-06

### Added

- Trusted metadata for importing complete jobs from the pinned public Harbor
  dataset without a local repository checkout.

### Changed

- The Harbor dataset page now explains the experiment in test-first language,
  reports the first public run, and invites replication, critique, and new
  evidence from general agent-evaluation researchers.
- Harbor result submissions accept the public dataset identifier
  `svgap/svgap-reset-release@0.2` while retaining digest and report-agreement
  checks.
- Maintainer rebuild and publication operations moved from the public dataset
  page to a repository guide.

## 0.3.0-alpha.6 - 2026-07-06

### Added

- `svgap study quickstart` evaluates a clearly labelled bundled fixture and
  creates an interpretable first evidence profile without requiring a model
  adapter.
- A review-before-publication 90-second onboarding-video kit with narration,
  shot list, sanitized terminal session, captions, accessibility and safety
  checks, and an editable SVG thumbnail.

### Changed

- Study profiles now expose answered, failed, and unanswered production
  questions, next evidence, and the claim boundary directly in HTML.
- Study commands print the exact first report to explain and put result
  interpretation before publication or submission guidance.
- Intermediate Yosys JSON now uses candidate-relative source locations so a
  shared study directory does not disclose the evaluator's workspace path.
- First-visit documentation distinguishes fast execution from the large cold
  container pull and provides a measured path from result to model integration.

## 0.3.0-alpha.5 - 2026-07-06

### Changed

- Replaced the long contributor-oriented landing page with a proof-first,
  cross-registry README that offers a zero-install result, one-command
  container demo, model smoke path, and public or private collaboration route.
- Added a compact current-coverage matrix, platform support, local/no-telemetry
  behavior, untrusted-input guidance, maintainer accountability, and explicit
  claim boundaries to the first-time path.
- `svgap doctor` now prints platform-specific installation recipes, the pinned
  container fallback, and troubleshooting documentation when tools are missing.
- Release automation selects the version-matched release-notes file instead of
  a hard-coded prior version.

### Added

- Research-call intake, bounded design-partner workflow, and one-page experiment
  contract that turn interest into attributable protocol or evidence work.
- Doctor remediation tests for macOS, common Linux package managers, Windows,
  the container fallback, and backend plugin errors.

## 0.3.0-alpha.4 - 2026-07-06

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

## 0.3.0-alpha.3 - 2026-07-05

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

## 0.3.0-alpha.2 - 2026-07-05

### Changed

- Replaced withheld provider model identifiers with stable public configuration
  aliases across repository history, release artifacts, and result provenance.
- Reissued package, container, and archival metadata from the sanitized source
  history.

## 0.3.0-alpha.1 - 2026-07-05

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

## 0.2.0-alpha.1 - 2026-07-04

### Added

- Existential research scope and compact research artifact.
- Content-bound imported functional results and example integration.
- Discoverable third-party checker backend registry and SDK.
- Strict report contract plus SARIF and static HTML export.
- Reset-release taskpack v0.2 with corrected timer intent and calibrated safe/
  unsafe references for all eight tasks.
- Pinned OSS CAD Suite container, reusable GitHub Action, Python 3.11-3.13 CI,
  release automation, governance, support, and community launch materials.

### Changed

- Runtime and package versions now agree.
- Public artifact verification checks exact candidate/file sets and report
  semantics in CI.
- Research positioning treats the reset count as a worked mechanism
  demonstration, not a prerequisite population estimate.

## 0.1.0-alpha.1 - 2026-07-02

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
