# Category expansion: X propagation and metastability containment

Status: implemented in `reference-yosys` with paired controlled fixtures.
`reference-naja` does not implement the expanded rules and returns `unknown`
when their intent fields are present.

## Implemented X rules

- `REF-XPROP-001` checks output-reachable operational state when
  `power_on = "reset_required"`.
- `REF-XPROP-002` retains source-level constructs that Yosys lowering would
  otherwise erase: `casex`, `casez`, wildcard equality, and incomplete plain
  `case` control flow under `x_policy = "strict"`.
- `REF-XPROP-003` binds named state to a required reset and optional reset value.
- `REF-XPROP-004` checks declared deterministic memory power-on intent against
  complete, constant Yosys `$meminit` coverage.

Example intent:

```toml
[intent]
power_on = "reset_required"
x_policy = "strict"
memory_power_on = "initialized_or_reset"

[[intent.state_requirements]]
signal = "mode"
reset = "core_reset"
value = "01"
```

The source scan in `REF-XPROP-002` removes comments and string contents before
tokenizing case constructs. It is intentionally not a complete SystemVerilog
semantic analysis. `REF-XPROP-004` recognizes complete static initialization;
the `initialized_or_reset` intent name reserves the broader contract, but
procedural memory scrub/reset recognition remains a documented gap.

## Implemented metastability-depth rule

`REF-META-001` compares a recognized destination register-chain depth with the
explicit `min_sync_stages` on the matching crossing:

```toml
[[intent.crossings]]
source = "status_src"
destination = "status_dst"
protocol = "single_bit"
min_sync_stages = 3
```

This rule is parametric. It does not model analog metastability, compute MTBF,
or infer a sufficient depth from clock frequency and technology data. A
two-stage chain under a declared three-stage requirement fails; the paired safe
fixture has three stages. `REF-CDC-001` remains distinct: it identifies the
absence of a recognized second stage.

## Controlled witnesses

| Family | Unsafe member | Safe member | Rule |
|---|---|---|---|
| `power_on_x` | Output-reachable state lacks reset | State is reset | `REF-XPROP-001` |
| `x_control_masking` | `casex` masks unknown selector values | Plain `case` includes `default` | `REF-XPROP-002` |
| `selective_reset` | Only part of named state receives the required value | Entire state receives it | `REF-XPROP-003` |
| `uninitialized_memory` | Memory has no static initialization | Every word has constant initialization | `REF-XPROP-004` |
| `synchronizer_depth` | Two stages under a three-stage requirement | Three stages | `REF-META-001` |

Each pair has the same interface and testbench. Both variants pass functional
simulation; only the unsafe member triggers its primary rule. That establishes
detector behavior on controlled shapes, not prevalence or silicon defect rate.
