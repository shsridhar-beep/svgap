# Finding ID reference

Every checker finding has a stable `rule_id`, severity, message, and
JSON-serializable evidence. The Yosys reference backend implements the narrow
rules below; `reference-naja` intentionally covers only the original five-rule
subset and abstains when a newer intent class is requested.

| Finding ID | Detects | Activation | Backends |
|---|---|---|---|
| `REF-CDC-001` | Async crossing without a recognized second destination stage | Declared asynchronous clock groups | Yosys, Naja |
| `REF-CDC-002` | Combinational logic between source state and synchronizer input | Declared asynchronous clock groups | Yosys, Naja |
| `REF-CDC-003` | Independently synchronized multi-bit crossing without recognized Gray coherence | Declared asynchronous clock groups | Yosys, Naja |
| `REF-CDC-004` | Pulse crossing without recognized source toggle encoding and destination XOR reconstruction | `protocol = "pulse"` | Yosys |
| `REF-CDC-005` | Toggle crossing without recognized source-state toggle feedback | `protocol = "toggle"` | Yosys |
| `REF-CDC-006` | Handshake without a synchronized return acknowledgment | `protocol = "handshake"` and named return endpoints | Yosys |
| `REF-CDC-007` | Two independently synchronized paths reconverge in destination combinational logic | `cdc_reconvergence = "forbid_independent"` | Yosys |
| `REF-CDC-008` | Async FIFO shape without synchronized Gray pointers in both directions | `protocol = "async_fifo"` and named return endpoints | Yosys |
| `REF-META-001` | Recognized synchronizer chain is shallower than the declared minimum | `min_sync_stages = N` | Yosys |
| `REF-RDC-001` | Raw async reset reaches ordinary state although synchronous deassertion is required | Reset `deassertion = "sync"` | Yosys, Naja |
| `REF-RDC-002` | Data path crosses between independently reset state domains | `independent_reset_groups` | Yosys |
| `REF-RDC-003` | Reset reaches a state-element reset pin through unapproved combinational logic | Reset `allow_combination = false` | Yosys |
| `REF-RDC-004` | Multiple declared resets reconverge on one state-element reset pin | Two declared reset origins reach one reset pin | Yosys |
| `REF-XPROP-001` | Un-reset operational state reaches an output despite required reset coverage | `power_on = "reset_required"` | Yosys, Naja |
| `REF-XPROP-002` | `casex`, `casez`, wildcard equality, or a plain `case` without `default` under strict X policy | `x_policy = "strict"` | Yosys |
| `REF-XPROP-003` | Named state lacks its required reset or reset value | `[[intent.state_requirements]]` | Yosys |
| `REF-XPROP-004` | Memory lacks recognized complete static initialization | `memory_power_on = "initialized_or_reset"` | Yosys |
| `REF-NAJA-FRONTEND-001` | Naja/slang frontend warning retained as evidence | Naja frontend warning | Naja |

All `REF-*` entries except `REF-NAJA-FRONTEND-001` have `error` severity.
Frontend warnings do not change a verdict.

The lint evidence backends use tool-derived identifiers rather than pretending
to be structural rules:

- `LINT-VERILATOR-<CODE>` for parsed Verilator diagnostics;
- `LINT-VERIBLE-<RULE>` for parsed Verible diagnostics.

Lint warnings remain warning evidence by default. Syntax/tool errors can fail
the lint oracle, but a lint oracle contributes to gap membership only when its
schema-v2 profile explicitly sets `contributes_to_gap = true`.

These recognizers are controlled research oracles, not a signoff deck. In
particular, `REF-META-001` measures declared chain depth but computes no MTBF;
`REF-CDC-008` recognizes a pointer-transfer shape but does not prove FIFO
full/empty logic; and `REF-XPROP-004` currently recognizes complete Yosys
`$meminit` coverage, not arbitrary procedural memory scrub sequences. See
[Limitations](limitations.md).
