# Architecture

SV-Gap separates experiment orchestration from structural analysis.

```text
candidate manifest
  |-- RTL sources
  |-- functional commands or imported result
  |-- clock/reset/crossing intent
  `-- checker backend
          |
          v
 normalized EvaluationReport
  |-- functional status and evidence
  |-- structural status and findings
  |-- tool/backend versions
  `-- gap membership
```

## Manifest boundary

The manifest is the reproducibility boundary. Relative file paths resolve from
the manifest directory. Clock relationships are never inferred as asynchronous
merely because two clock names differ; the evaluator must declare asynchronous
groups explicitly.

## Annotated intent-manifest example

This is the manifest the demo's `reset_release` safe design ships with
(`src/svgap/demo_assets/reset_release/safe/manifest.toml`), reduced to the
fields the current loader (`src/svgap/manifest.py`) requires and annotated
one line per field. It is a companion to the unannotated
[`schemas/manifest-v1.example.toml`](https://github.com/shsridhar-beep/svgap/blob/main/schemas/manifest-v1.example.toml)
and to the open [intent-contract RFC](https://github.com/shsridhar-beep/svgap/discussions/20),
which asks whether this contract expresses the production questions
reviewers actually need answered.

```toml
schema_version = "1.0"       # manifest format version; the loader rejects anything else
candidate_id = "demo-reset-release-safe"  # identifies this candidate in the report and gap membership

[design]
top = "reset_release"        # top module name; must be a valid Verilog identifier
sources = ["design.sv"]      # RTL sources, relative to this manifest, checked to exist

[functional]
commands = [
  ["iverilog", "-g2012", "-o", "${SVGAP_BUILD}/sim.vvp", "design.sv", "../tb.sv"],
  ["vvp", "${SVGAP_BUILD}/sim.vvp"],
]                             # functional oracle commands, run inside a candidate-local build dir

[structural]
backend = "reference-yosys"  # checker backend that evaluates the declared intent

[intent]
asynchronous_groups = []     # explicit async clock groups; never inferred from clock names

[[intent.clocks]]
name = "core"                # intent-local clock name, referenced by resets/crossings
port = "clk"                 # RTL port this clock name binds to

[[intent.resets]]
name = "power_on_reset"      # intent-local reset name
port = "arst_n"               # RTL port this reset binds to
active = "low"                # reset is asserted when this port is driven low
assertion = "async"           # the reset can assert without a clock edge
deassertion = "sync"          # release must be synchronized; this is what REF-RDC-001 checks
clock = "core"                # optional; if set, must name a declared intent.clocks entry

[output]
report = "build/report.json" # where `svgap check` writes the normalized report
```

Every field above maps directly to a field `load_manifest` in
`src/svgap/manifest.py` accepts; nothing here is aspirational syntax.

This example only establishes that the manifest's declared reset-release
intent is legible and checkable — a structural pass built from it is still
bounded evidence, not a signoff claim. See the
[scope boundary](scope-boundary.md) for what SV-Gap does and does not claim.

## Backend boundary

A backend implements one operation:

```python
check(manifest) -> CheckResult
```

It must return one of `pass`, `fail`, `unknown`, or `tool_error`, stable rule
identifiers, evidence, and its own version. A backend must return `unknown` when
required intent is absent. It must not silently reinterpret tool failure as a
clean result.

## Built-in reference oracle

The reference oracle elaborates RTL to Yosys JSON and walks register/data
relationships. It is intentionally limited to controlled structural shapes:

- `REF-CDC-001`: asynchronous register crossing without a recognized second
  destination stage;
- `REF-CDC-002`: combinational logic immediately before a recognized
  synchronizer;
- `REF-CDC-003`: independently synchronized multi-bit crossing without a
  declared Gray-code protocol and a recognizable XOR-based source transform;
- `REF-RDC-001`: raw asynchronous reset on unmarked state when the manifest
  requires synchronous deassertion.
- `REF-XPROP-001`: un-reset state reaches a module output when the manifest
  declares that operational state requires reset coverage at power-on.

These rules demonstrate the evaluation contract. They are not a signoff rule
deck. External backends may provide much broader coverage without changing the
manifest/report concepts.
