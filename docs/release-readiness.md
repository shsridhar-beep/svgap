# Public release readiness

Audit date: 2026-07-02

## Ready

- Apache-2.0 license, notice, and third-party inventory are present.
- The quickstart, limitations, security warning, contribution guide, and conduct
  policy are present.
- Twenty-eight tests pass with Yosys 0.66 and Icarus Verilog 13.0, including
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
  `6a5205559bbe1640784236e3d5fcf412dc4b3899a5c7f90dc6e1abf486fbe6d7`.
- Four scoped starter issues are open; see [starter-issues.md](starter-issues.md).
- The public repository is `https://github.com/shsridhar-beep/svgap`. Release
  `v0.1.0-alpha.1` is tagged, published on GitHub, and archived at Zenodo
  (`doi:10.5281/zenodo.21152349`).
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

## Research blocker, not repository blocker

Independent full-case human expert adjudication is required before `14/57` is
described as a validated defect rate. Until then it is an author-confirmed
lower-bound detection count. The blinded synthetic panel is a robustness check,
not a substitute; see [synthetic adjudication](synthetic-adjudication.md).

Current blinded packet: `review_packets/reset-replication-v0.3.zip`, SHA-256
`942bcfc09d3aeafc834f64bdae69c07f08243351c332e36018d10077762655b9`.

No package-registry publication is part of this milestone; installation is
from source or the tagged archive.
