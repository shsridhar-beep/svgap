# SV-Gap v0.3.0-alpha.13

This release expands SV-Gap from five initial structural mechanisms to 21
stable reference rules and 22 paired witnesses spanning CDC, RDC, synchronizer
depth, X and power-on behavior, bounded protocol and temporal properties, and
synthesized functional equivalence. The reference oracles remain controlled
research instruments, not a production signoff deck.

Schema v2 records ordered multi-oracle evidence and makes each oracle's class,
coverage, required status, and contribution to gap membership explicit. The
17 structural pairs run through the narrow Yosys backend; Naja independently
covers the original five-rule subset and abstains outside that coverage.
Verilator and Verible lint remain a separate, normally noncontributing evidence
class.

Two new backends cover categories that structural inspection cannot decide:

- `formal-yosys` runs bounded Yosys SAT against explicit property harnesses and
  supplies the protocol and temporal rules;
- `equivalence-yosys` compares a candidate with an explicit reference after
  Yosys RTL synthesis.

Five new witness pairs calibrate ready/valid persistence, bounded response,
one-cycle pulse width, synthesis-directive semantics, and direct functional
equivalence. Both sides of every pair pass the same ordinary functional test;
the configured property or equivalence oracle separates the safe and unsafe
implementations. Ordinary Verilator lint passes both sides of these fixtures.

The release also carries a reproducible descriptive audit of the same 508
public RTL-generation tasks previously inventoried across VerilogEval, RTLLM,
and CVDP. It establishes two conservative lower bounds on absent scoring
evidence:

- 98/508 tasks (19.3%) explicitly state a temporal contract but provide no
  recognizable native temporal assertion or formal temporal scoring;
- 16/508 tasks (3.1%), comprising all 16 explicitly equivalence-oriented tasks,
  synthesize the RTL but provide neither formal equivalence nor post-synthesis
  behavioral comparison.

These counts describe missing benchmark evidence, not RTL defect prevalence,
model quality, or production-workload prevalence. The detector-positive rows
were reviewed in an AI-assisted maintainer session; independent replication and
negative-sample review remain open validation work.

Evaluation robustness is improved in two places. Structural fan-in tracing now
visits each net once rather than enumerating every path through reconvergent
logic. On POSIX, functional, structural Yosys, bounded-formal, and equivalence
commands also run in isolated process groups whose descendants are reaped on
timeout. Together these changes prevent a single pathological candidate or
inherited tool pipe from stalling an evaluation batch.

Install or upgrade with `pip install --upgrade svgap`. The optional independent
Naja backend remains available with `pip install "svgap[naja]"`. The GitHub
prerelease carries a checksummed `temporal-equivalence-audit-v0.1.tar.gz`
evidence bundle and the schema-v1 and schema-v2 report contracts.

## Verified release artifacts

- GitHub: [`v0.3.0-alpha.13`](https://github.com/shsridhar-beep/svgap/releases/tag/v0.3.0-alpha.13)
- PyPI: [`svgap==0.3.0a13`](https://pypi.org/project/svgap/0.3.0a13/)
- GitHub/PyPI wheel: `sha256:6ba6913609474083c3f6ddd349ea72c5610abe8e8745ce9f4e2dfa781f206d77`
- GitHub/PyPI source distribution: `sha256:d8ef79972fe68acf90ef4f7cdeec723fa14ab6dd8c9cd3e3d723270999fc6f8b`
- Container: `ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.13`
- Multi-architecture container index: `sha256:af55831a46af27573141f29827be24e041a0f9f82a37db1af5b50ac92a8c789d`
- Temporal/equivalence audit archive: `sha256:6be779441725ee64068225d7568c5848779ec68b1176b1aab954e681c60b4030`
- Zenodo: [doi:10.5281/zenodo.22087102](https://doi.org/10.5281/zenodo.22087102)

The GitHub checksum manifest verifies against a flat release download, and
PyPI advertises the same wheel and source-distribution hashes. The container
index contains both `linux/amd64` and `linux/arm64` images. An independently
downloaded Zenodo archive matched its published MD5
`cbd72815fb7548c89f5a34db7ae6dd04`; its extracted tree matched the tagged Git
tree file-for-file and byte-for-byte and contained none of the explicitly
excluded local images, power-on taskpack, or `.DS_Store` files.
