# Public release readiness

Audit date: 2026-07-05

## Ready

- Apache-2.0 license, notice, and third-party inventory are present.
- The quickstart, limitations, security warning, contribution guide, and conduct
  policy are present.
- Eighty-one tests pass with Yosys 0.66 and Icarus Verilog 13.0, including
  adversarial oracle and JSON Schema checks.
- A wheel builds and installs successfully in a clean temporary environment.
- The controlled witnesses, 508-task benchmark audit, exploratory pilot, and
  72-candidate reset replication have tracked summaries and interpretation
  boundaries.
- Raw provider responses, private adjudication mappings, and blinded review
  packets are excluded from Git. The normalized public candidate artifact is
  intentionally versioned.
- A secret-keyed 72-case v0.3 blinded adjudication packet has been generated locally and verified
  not to contain model names or automated outcomes.
- The locked eight-panel synthetic review reached nominal alpha `0.989`, exact
  15-yes/57-no consensus across all targets, and zero unresolved cases. It is
  reported as synthetic robustness evidence, not human validation.
- A deterministic 72-candidate bundle is versioned at
  `artifacts/reset-replication-v0.1`; manifest SHA-256 is
  `e523a03b604864d276b35d88d097c45f0a17ed3f9650bd2c3dcb9a9d4ea0f132`.
- Ten scoped issues are open, including five bounded `good first issue` entry
  points for demo, registry, documentation, and oracle-review contributions.
- The public repository is `https://github.com/shsridhar-beep/svgap`. Releases
  `v0.1.0-alpha.1` through `v0.3.0-alpha.2` were rebuilt from rewritten,
  identifier-sanitized tags.
- The pre-redaction Zenodo version deposits were deleted. The replacement
  `v0.3.0-alpha.2` archive is published at DOI
  `10.5281/zenodo.21199886`; an independently fetched copy had zero matches for
  the redacted identifier patterns.
- PyPI `0.3.0a1` was deleted. PyPI `0.3.0a2`, its wheel, source distribution,
  and GHCR image were independently checked after publication.
- Author identity, affiliation, ORCID, and contact are recorded in
  `CITATION.cff`.
- Publication of normalized generated RTL is authorized by the project author.
  Raw provider transcripts remain excluded.

## Decisions closed for the first public snapshot

1. Cite with full name, NVIDIA affiliation, and ORCID (superseding the earlier
   name-only entry).
2. Publish normalized generated RTL under the scoped artifact license; exclude
   raw provider transcripts and credentials.
3. Lock the two-repeat, four-configuration synthetic robustness panel before
   publishing model-labeled RTL. Do not call it human expert adjudication.
4. Tag `v0.1.0-alpha.1` (package version `0.1.0a1`), publish a GitHub Release,
   and archive it at Zenodo (superseding the earlier untagged-branch
   decision).

## Optional evidence for a stronger rate claim

Independent full-case human expert adjudication is required only before `14/57`
is described as a validated defect rate. Until then it is an author-confirmed
lower-bound demonstration count. This does not block the existential research
claim, framework release, or community launch. The blinded synthetic panel is a
robustness check, not a substitute; see
[synthetic adjudication](synthetic-adjudication.md).

Current blinded packet: `review_packets/reset-replication-v0.3.zip`, SHA-256
`942bcfc09d3aeafc834f64bdae69c07f08243351c332e36018d10077762655b9`.

PyPI publication uses GitHub OIDC trusted publishing through the protected
`pypi` environment; no long-lived package-registry token is stored.

## v0.2 alpha released

- The research scope is explicitly existential and no longer treats population
  estimation or human adjudication as a release gate.
- Existing functional verdicts can be imported with a digest binding them to
  the candidate source set.
- Third-party checker backends are discoverable through a documented entry
  point contract.
- Strict report validation, SARIF, static HTML, a composite GitHub Action, and a
  pinned OSS CAD Suite container are implemented.
- Reset taskpack v0.2 fixes the timer ambiguity and calibrates safe/unsafe
  references for all eight tasks in automated tests.
- Release automation builds wheels, source distributions, schemas, taskpack and
  result archives, checksums, and a multi-architecture GHCR image.

Tag `v0.2.0-alpha.1` and its GitHub prerelease were republished from rewritten,
tested commit `42794d6`. The release carries a wheel, source distribution,
schemas, v0.1 result archive, v0.2 taskpack archive, and SHA-256 manifest.
Public `main` requires the Python 3.11–3.13, package, and container checks;
force pushes and branch deletion are disabled. Its superseded archival deposit
was deleted as part of the provider-label history redaction.

## v0.3 adoption alpha released

- `svgap demo` produces the controlled functional-pass/structural-gap witness
  from a source install, wheel, PyPI install, or the open-tool container.
- The documentation site is deployed at
  `https://shsridhar-beep.github.io/svgap/`, with a bring-your-own-RTL tutorial
  and audience-specific contribution paths.
- The schema-validated public result registry carries generation, diagnosis,
  and repair profiles without converting them into a model leaderboard.
- The first exploratory diagnosis/repair baseline demonstrates distinct
  epistemic and repair failure modes across two configurations from one
  provider; it is not a comparative model study.
- Five bounded good-first issues and three seeded Discussions provide public
  entry points for new users and collaborators.
- PyPI trusted publishing, GitHub release assets, the multi-architecture GHCR
  image, Pages deployment, and Zenodo ingestion all completed successfully.

Tag `v0.3.0-alpha.2` was published from tested commit `249a5a2`. The GitHub
release carries the wheel, source distribution, v0.1 generation artifact, v0.2
taskpack, public baseline registry and evidence archive, and SHA-256 manifest.
The container manifest digest is
`sha256:9f99695059014de7055ab57448456e3cc9ac3c3910da4668ba65f8aef345a4b3`.
PyPI `0.3.0a2` and Zenodo DOI `10.5281/zenodo.21199886` carry the sanitized
release. Superseded pre-redaction package and archival versions were deleted.

## v0.3.0-alpha.3 released

- Any model harness can generate through a stdin/stdout command contract.
- Credentialed generation can be separated from network-disabled, disposable
  RTL evaluation; generated RTL remains explicitly treated as untrusted input.
- Generation, diagnosis, and repair evidence can enter one immutable,
  track-aware submission contract with public, attested-alias, or anonymous
  provenance.
- Publication gates verify artifact hashes, recompute deterministic summaries,
  reject common credential/internal-path patterns, and support a private
  submitter-held regex denylist.
- Accepted submissions generate citable static evidence profiles without a
  scalar leaderboard or hosted-service dependency.
- Runnable diagnosis and repair starters, a collaboration RFC, contribution
  credit rules, and a two-working-day acknowledgement target provide a concrete
  frontier-research participation path.

The complete 81-test suite, registry verification, documentation link checker,
strict MkDocs build, deterministic-bundle regression, diagnosis/repair smoke
runs, clean wheel install, GitHub Actions matrix, container quickstart, and
Pages deployment pass. GitHub Release, PyPI `0.3.0a3`, and the multi-architecture
GHCR image are published. The container manifest digest is
`sha256:609e9f2c5b797c7a81f25c7617968e83708307075f30c8da3b1c7a57130b836a`.

Zenodo ingested the tagged source as DOI `10.5281/zenodo.21201211`. An
independently downloaded copy matched Zenodo's published MD5 and had zero
matches for the withheld identifier patterns or local home paths. The PyPI and
GitHub wheels have identical extracted contents; future releases publish one
preserved build artifact to both destinations so their outer archive hashes
also agree. The corrected GitHub `SHA256SUMS` asset verifies directly against a
flat release download.

## v0.3.0-alpha.4 release candidate

- The frozen reset-release v0.2 taskpack and diagnosis/repair challenge assets
  ship inside the wheel.
- `svgap study run ... --smoke` runs one task and one sample; `--full` selects
  the frozen eight-task, three-sample protocol.
- Credentialed generation and credential-free evaluation are separable through
  `svgap study evaluate-saved` without mounting repository task directories.
- Study runs write portable reports, a deterministic summary, an evidence-file
  list, and a static HTML profile.
- `svgap.evaluate`, taskpack discovery, and model-response materialization are
  available as public Python APIs.
- Two deterministic open-weights submissions seed the generated registry and
  profile pages as supporting demonstrations, not independent replications.
- Submission contributors can synchronize the checked-in registry and pages
  with `python scripts/sync_results.py` before opening a pull request.

The complete 94-test suite, strict documentation build, installed-wheel taskpack
discovery, installed-wheel smoke study, installed-wheel diagnosis challenge,
portable-path scan, result-registry regeneration, and deterministic submission
bundle reproduction pass locally. GitHub, PyPI, GHCR, Pages, and Zenodo
publication remain to be verified after the alpha.4 tag is pushed.
