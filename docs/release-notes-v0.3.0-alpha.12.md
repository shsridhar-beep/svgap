# SV-Gap v0.3.0-alpha.12

This release is community-driven. Since alpha.11, external contributors have
added most of what is new here, across the demo, the CLI, the test suite,
documentation, and developer tooling, and the first external registry
submissions arrived.

The `svgap demo` command now carries four scenarios rather than one. Alongside
reset-release, it covers a combinational clock-domain crossing (`REF-CDC-002`),
power-on state reachability (`REF-XPROP-001`), and a multi-bit bus clock-domain
crossing (`REF-CDC-003`). Two new options make the set easier to work with:
`svgap demo --scenario all` runs every scenario in sequence, and
`svgap demo --scenario list` prints the available scenarios and their
descriptions without requiring the demo toolchain.

This release also adds an ordinary RTL lint baseline. Default Verilator and
Verible configurations were run over the frozen reset-release candidates, and
neither linter emitted an RDC-specific diagnostic for any of the 14 functionally
passing reset-gap candidates, nor for any of the 43 structural-pass comparators.
The apparent diagnostic rate is explained by filename and style findings
unrelated to reset behavior, and the one Verilator warning that mentions
synchronization points at the recognized synchronizer rather than at the
raw-reset bypass. This is a descriptive baseline, and it is not a claim that
lint cannot be configured to catch the pattern. See the
[RDC lint baseline result](https://shsridhar-beep.github.io/svgap/rdc-lint-baseline-result/).

The first two external registry submissions are included: reset-release smoke
evidence profiles for Gemma 4 12B and GPT-4.1 mini.

Developer and documentation additions include a Docker development environment
and Makefile targets for it, an annotated intent-manifest example, a finding-ID
reference table, a troubleshooting and doctor guide, and additional test
coverage across taskpack manifests, malformed intent manifests, disputed
findings, and the result-registry schema.

External contributions in this release came from Siddhanth Kalyanaraman
(@sidbu546), @madhu2000u, and Renji (@waterlemonnn), and are recorded in
CONTRIBUTORS.md. Install or upgrade with `pip install --upgrade svgap`, and the
opt-in `reference-naja` backend remains available with
`pip install "svgap[naja]"`.
