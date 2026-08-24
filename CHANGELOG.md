# Changelog

All notable changes will be documented here. The project uses semantic
versioning once the manifest and report contracts reach public v0.1.

## Unreleased

## 0.3.0-alpha.13 - 2026-08-24

### Added

- Report and manifest schema v2 with ordered multi-oracle evidence,
  per-oracle class/contribution/required flags and coverage metadata, while
  retaining schema-v1 compatibility.
- Verilator and Verible lint backends as a distinct `lint` evidence class,
  carrying the frozen 0/14 RDC calibration boundary.
- Twelve paired reference fixtures and rules covering declared synchronizer
  depth; pulse, toggle, handshake, reconvergence, and async-FIFO CDC;
  independent reset domains, reset gating, reset reconvergence; X-masking
  control flow, selective reset, and uninitialized memory.
- `formal-yosys` bounded protocol/temporal properties and
  `equivalence-yosys` synthesized reference miters, with five paired witnesses
  and four stable finding IDs.
- A reproducible 508-task temporal/equivalence benchmark audit. It establishes
  conservative lower bounds of 98 explicit temporal contracts without
  recognizable property/formal scoring and 16 explicit equivalence contracts
  with synthesis but no equivalence or post-synthesis comparison.

### Changed

- Schema-v2 profiles now require at least one contributing oracle rather than
  specifically requiring a `structural` class, allowing temporal, protocol,
  and equivalence profiles without mislabeling their evidence.
- `reference-naja` publishes its supported-rule coverage and abstains with
  `unknown` when an expanded Yosys-only intent class is requested.
- The Yosys flow runs `opt_dff` so synchronous reset pins and values remain
  inspectable for selective-reset checks.

### Fixed

- Yosys structural fan-in tracing now visits each net once instead of
  enumerating every path through reconvergent combinational logic, preventing
  one candidate from stalling a complete evaluation batch.
- On POSIX, functional, structural Yosys, bounded-formal, and equivalence tool
  commands run in isolated process groups and reap descendants on timeout, so
  inherited output pipes cannot defeat the configured wall-clock limit.
- The bounded-formal script no longer requests a redundant post-0.33
  `chformal` lowering pass, preserving compatibility with Ubuntu's Yosys 0.33.
- Verilator backend arguments are applied after `--Wall`, allowing a manifest
  to override a default warning such as `DECLFILENAME` deterministically.

## 0.3.0-alpha.12 - 2026-08-17

This release is community-driven. It gathers contributions from three external
contributors across demo scenarios, CLI tooling, test coverage, documentation,
and developer tooling, alongside the first external registry submissions and a
new ordinary-lint baseline study.

### Added

- Demo scenarios beyond reset-release, selectable with `svgap demo --scenario`:
  `comb-crossing` (`REF-CDC-002`), `power-on` (`REF-XPROP-001`), and
  `cdc-crossing` (`REF-CDC-003`, a gray-coded multi-bit bus crossing with
  declared coherence intent against a binary bus synchronized bit-by-bit).
- `svgap demo --scenario all` runs every scenario in sequence, and
  `svgap demo --scenario list` prints the available scenarios and their
  descriptions without requiring the demo tools.
- Ordinary RTL lint baseline study: default Verilator and Verible
  configurations emit no RDC-specific diagnostic for any of the 14 functionally
  passing reset-gap candidates, and the same holds across the 43 structural-pass
  comparators. See
  [docs/rdc-lint-baseline-result.md](docs/rdc-lint-baseline-result.md) and
  `reports/rdc-lint-baseline-v0.1/`.
- First external registry submissions: Gemma 4 12B and GPT-4.1 mini
  reset-release smoke evidence profiles.
- Docker development environment via `docker-compose.yml`, plus Makefile targets
  for the docker development flow.
- Documentation: an annotated intent-manifest example, a finding-ID reference
  table, and a troubleshooting and doctor guide.
- Test coverage: packaged-taskpack manifest validation, malformed
  intent-manifest negative fixtures, a disputed-finding regression fixture
  template (`examples/disputed_finding_template`) that proves a recorded dispute
  never silently converts a checker `fail` or `unknown` into a `pass`, and
  result-registry schema negative fixtures.
- A README star badge and a good-first-issue onboarding row.

### Fixed

- The `svgap demo --scenario all` JSON test derives the expected scenario set
  from the `DemoScenario` enum, so adding a scenario no longer requires updating
  a hardcoded assertion.

### Thanks

External contributions in this release came from @sidbu546, @madhu2000u, and
@waterlemonnn. See [CONTRIBUTORS.md](CONTRIBUTORS.md).

## 0.3.0-alpha.11 - 2026-07-20

### Added

- Frozen, preregistered power-on prevalence protocol with balanced sampling,
  pre-scoring output locks, dual-backend confirmation, task-clustered
  uncertainty, duplicate-output sensitivity analysis, and explicit boundaries
  against universal prevalence or model-ranking claims. The protocol is a
  community-runnable instrument; confirmatory data are not included.
- `REF-XPROP-001` implemented in the `reference-naja` backend, mirroring
  `reference-yosys`'s forward output-reachability walk over un-reset
  sequential state; a manifest that sets `init_attributes_are_power_on`
  abstains as `unknown` rather than guessing.

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
  locations, supported rules, the no-timeout gap, and known
  false-positive/false-negative classes.
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

### Changed

- Community pulse refreshed after the merged external backend contribution and
  completed independent RTL review. Those establish outside participation;
  the primary independent-run adoption metric remains at zero until a public
  replication is submitted.

## 0.3.0-alpha.10 - 2026-07-20

### Added

- Independent RTL designer review imported: five of five controlled witness
  pairs supported and three of three blinded candidates concordant with the
  frozen structural verdicts, at high confidence, with root-cause agreement
  on two. Returned files ship verbatim under
  `artifacts/independent-review-v0.1/` (hash-locked in issue #3 before
  import); summary, reviewer attestation, disclosed mid-review
  clarification, and claim boundaries in `docs/independent-review-result.md`.
- `scripts/verify_synchronizer_bypass.py` and one paragraph in the reset study
  doc: every one of the 14 detected gap cases in the frozen reset artifact also
  contains a two-flop reset synchronizer recognized by the reference oracle in
  the same design, across all three configurations. The script recomputes the
  per-configuration counts from the frozen artifact without modifying it, and
  reports where each synchronizer output is consumed: in all 14 cases only
  synchronous data-path logic (a mux select), never a reset pin, while the
  flagged registers' asynchronous reset pins stay on the raw net.
- Animated terminal demo above the README fold, generated from recorded runs
  by `scripts/gen_readme_demo_gif.py`.
- `examples/README.md` with the scenario-to-rule mapping table, after two
  independent reports of folder-to-rule confusion.

### Changed

- README and docs index openers rewritten with searchable terms; a stale
  project-status disclaimer removed; demo SVG redrawn.

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
