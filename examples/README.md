# Examples

Twenty-two controlled witness pairs exercise every current reference rule.
Each family contains `safe/` and `unsafe/` candidates with one shared
testbench. Both variants pass functional simulation; the unsafe variant is
distinguished only by its configured structural, temporal, protocol, or
equivalence oracle.

## Scenario-to-rule mapping

| Folder | Controlled distinction | Primary unsafe rule |
|---|---|---|
| `level_crossing` | Direct async sample vs two stages | `REF-CDC-001` |
| `comb_crossing` | Logic before synchronizer vs clean source | `REF-CDC-002` |
| `gray_counter` | Binary bus vs registered Gray transfer | `REF-CDC-003` |
| `pulse_crossing` | Direct pulse sampling vs toggle/XOR pulse transfer | `REF-CDC-004` |
| `toggle_crossing` | Sampled level vs source toggle feedback | `REF-CDC-005` |
| `handshake_crossing` | Missing vs synchronized acknowledgment return | `REF-CDC-006` |
| `cdc_reconvergence` | Independent synchronized paths combined vs kept separate | `REF-CDC-007` |
| `async_fifo` | Binary vs bidirectional Gray pointer transfer | `REF-CDC-008` |
| `synchronizer_depth` | Two vs three stages under a three-stage declaration | `REF-META-001` |
| `reset_release` | Raw async release vs recognized reset synchronizer | `REF-RDC-001` |
| `reset_domain_crossing` | Data dependency across independent reset groups vs no dependency | `REF-RDC-002` |
| `reset_gating` | Gated reset vs direct reset | `REF-RDC-003` |
| `reset_reconvergence` | Two resets combined vs one reset at the state pin | `REF-RDC-004` |
| `power_on_x` | Output-reachable un-reset state vs reset-covered state | `REF-XPROP-001` |
| `x_control_masking` | `casex` vs plain `case` with `default` | `REF-XPROP-002` |
| `selective_reset` | Partial vs complete named-state reset | `REF-XPROP-003` |
| `uninitialized_memory` | No memory initialization vs complete constant initialization | `REF-XPROP-004` |
| `temporal_backpressure` | Smoke tests with ready high vs valid/data persistence under stall | `REF-PROT-001` |
| `temporal_response` | Eventual response vs completion within three cycles | `REF-TEMP-001` |
| `temporal_pulse` | First pulse observed vs exactly one-cycle pulse width | `REF-TEMP-002` |
| `synthesis_directive_equivalence` | Tested RTL mode vs synthesized semantics of all modes | `REF-EQUIV-001` |
| `functional_equivalence` | Three tested opcodes vs exhaustive combinational reference comparison | `REF-EQUIV-001` |

`synchronizer_depth` also demonstrates report schema v2: its structural and
optional Verilator lint results are separate `oracle_results`. The other pairs
from the original structural set remain schema v1 fixtures to continuously test
backward compatibility. The five new pairs use schema v2 with `protocol`,
`temporal`, or `equivalence` as the contributing evidence class.

Some unsafe members can emit an additional prerequisite rule (for example the
binary-pointer async-FIFO witness also emits `REF-CDC-003`). Tests require the
primary rule rather than claiming each real design has exactly one defect.

The full definitions and limitations are in
[`docs/finding-id-reference.md`](../docs/finding-id-reference.md). These pairs
calibrate recognizers; they do not establish real-world prevalence.

## Supporting folders

- `adjudication_calibration/`: calibration packets for blinded adjudication.
- `imported_result/`: importing external functional evidence instead of
  running a testbench.
