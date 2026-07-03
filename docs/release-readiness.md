# Public release readiness

Audit date: 2026-07-02

## Ready

- Apache-2.0 license, notice, and third-party inventory are present.
- The quickstart, limitations, security warning, contribution guide, and conduct
  policy are present.
- Twenty-three tests pass with Yosys 0.66 and Icarus Verilog 13.0, including
  adversarial oracle and JSON Schema checks.
- A wheel builds and installs successfully in a clean temporary environment.
- The controlled witnesses, 508-task benchmark audit, exploratory pilot, and
  72-candidate reset replication have tracked summaries and interpretation
  boundaries.
- Generated candidates, provider responses, private adjudication mapping, and
  blinded review packets are excluded from Git by default.
- A secret-keyed 72-case v0.3 blinded adjudication packet has been generated locally and verified
  not to contain model names or automated outcomes.
- A portable 72-candidate r3 release bundle is staged locally with manifest
  SHA-256 `bfb53f39280c3c35a417cfe827f90cb310e9239a6fba90c5c2b30d4b3ac56a00`;
  publication is held until blinded labels are locked.
- Four starter-issue drafts are ready in [starter-issues.md](starter-issues.md).

## Decisions required before making the repository public

1. Add ORCID and affiliation to `CITATION.cff` if desired.
2. Document release authority for the model-account context, particularly if
   employer credentials or resources were used. Publication of normalized RTL
   is authorized by the project author; raw provider transcripts remain excluded.
3. Lock two independent full-case reviews before publishing model-labeled RTL.
4. Choose whether the first public tag is `v0.1.0-alpha.1` or an untagged
   development branch. The package currently reports `0.1.0.dev0`.

## Research blocker, not repository blocker

Independent full-case expert adjudication is required before `14/57` is described
as a validated defect rate. Until then it is an author-confirmed lower-bound
detection count.

Current blinded packet: `review_packets/reset-replication-v0.3.zip`, SHA-256
`942bcfc09d3aeafc834f64bdae69c07f08243351c332e36018d10077762655b9`.

The local `origin` points to `https://github.com/shsridhar-beep/svgap.git`. No
commit, tag, push, or public release has been created.
