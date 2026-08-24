# Architecture

SV-Gap separates functional execution from independently versioned evidence
producers. Schema v2 records every producer as a distinct oracle result.

```text
manifest + RTL
   |
   +-- functional commands/import --------> FunctionalResult
   |
   +-- structural oracle (Yosys/Naja) ----> OracleResult[class=structural]
   +-- ordinary lint (Verilator) ---------> OracleResult[class=lint]
   `-- other configured evidence ---------> OracleResult[class=...]
                                              |
                                              v
                                     EvaluationReport v2
                                     + gap membership
                                     + per-oracle coverage
                                     + versions/diagnostics
```

This prevents a lint-clean result from overwriting a CDC/RDC failure, and it
prevents an unavailable optional tool from being silently reported as a pass.

## Manifest boundary

The manifest is the reproducibility boundary. Relative paths resolve from its
directory. Clock and reset relationships are declared, never inferred merely
from different signal names.

Schema v1 remains accepted and maps its single `[structural]` table to one
compatibility oracle. Schema v2 uses ordered `[[oracles]]` records:

```toml
schema_version = "2.0"
candidate_id = "candidate-a"

[design]
top = "top"
sources = ["design.sv"]

[functional]
commands = [
  ["iverilog", "-g2012", "-o", "${SVGAP_BUILD}/sim.vvp", "design.sv", "tb.sv"],
  ["vvp", "${SVGAP_BUILD}/sim.vvp"],
]

[[oracles]]
id = "reference-structure"
class = "structural"
backend = "reference-yosys"
contributes_to_gap = true
required = true

[[oracles]]
id = "ordinary-lint"
class = "lint"
backend = "lint-verilator"
contributes_to_gap = false
required = false

[intent]
asynchronous_groups = [["source"], ["destination"]]
cdc_reconvergence = "forbid_independent"
x_policy = "strict"

[[intent.clocks]]
name = "source"
port = "src_clk"

[[intent.clocks]]
name = "destination"
port = "dst_clk"

[[intent.crossings]]
source = "event_toggle"
destination = "event_pulse"
protocol = "pulse"
min_sync_stages = 2

[output]
report = "build/report.json"
```

`required = false` means tool absence is retained as `tool_error` evidence but
does not make the command fail. `contributes_to_gap = false` means the result is
contextual evidence and cannot create a structural-gap member. At least one
structural oracle is currently required in a v2 manifest.

The complete syntax example is
[`schemas/manifest-v2.example.toml`](https://github.com/shsridhar-beep/svgap/blob/main/schemas/manifest-v2.example.toml).

## Report boundary

Schema v1 emits the legacy top-level `structural` result. Schema v2 emits
`oracle_results` and deliberately omits that top-level field:

```json
{
  "schema_version": "2.0",
  "functional": {"status": "pass"},
  "oracle_results": [
    {
      "oracle_id": "reference-structure",
      "oracle_class": "structural",
      "status": "fail",
      "contributes_to_gap": true,
      "required": true,
      "coverage": {"rules": ["REF-CDC-001"]}
    },
    {
      "oracle_id": "ordinary-lint",
      "oracle_class": "lint",
      "status": "pass",
      "contributes_to_gap": false,
      "required": false,
      "coverage": {"ruleset": "--Wall"}
    }
  ],
  "gap_member": true
}
```

The actual schema requires the remaining backend, finding, diagnostic, version,
and timestamp fields. Gap membership is:

```text
functional == pass
AND any(oracle.contributes_to_gap AND oracle.status == fail)
```

## Backend boundary

A backend exposes stable `name` and `version` values and implements either:

```python
check(manifest) -> CheckResult
```

or the schema-v2-aware form:

```python
check(manifest, oracle_config) -> CheckResult
coverage(manifest, oracle_config) -> dict
```

It returns `pass`, `fail`, `unknown`, or `tool_error`. Missing required intent
or unsupported analysis must not become `pass`.

## Built-in reference oracle

`reference-yosys` elaborates RTL with Yosys and implements 17 controlled
recognizers across these classes:

- baseline CDC (`REF-CDC-001` through `003`);
- pulse, toggle, handshake, reconvergence, and async-FIFO CDC
  (`REF-CDC-004` through `008`);
- declared synchronizer depth (`REF-META-001`);
- reset release, independent reset domains, reset gating, and reset
  reconvergence (`REF-RDC-001` through `004`);
- output-reachable un-reset state, X-masking control flow, selective reset, and
  memory initialization (`REF-XPROP-001` through `004`).

See the [finding ID reference](finding-id-reference.md) for exact activation
conditions. These are reference shapes with paired fixtures, not a signoff deck.

`reference-naja` independently reproduces the original CDC/RDC/X subset using
Naja's in-process SNL graph. It exposes its supported rules in coverage
metadata and returns `unknown` when newer intent classes are requested.

## Lint evidence

`lint-verilator` and `lint-verible` run ordinary source lint as the separate
`lint` evidence class. Their coverage metadata records the ruleset and the
frozen RDC calibration result: neither default configuration detected the
RDC mechanism in the 14 functionally passing `REF-RDC-001` cases. This makes
lint useful evidence without relabeling it as structural CDC/RDC analysis.
