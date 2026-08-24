# Public benchmark temporal and synthesis-equivalence audit

Audit date: 2026-08-24

## Result

The audited artifacts establish two conservative lower bounds across the same
508 public tasks used by the CDC/RDC and power-on inventories:

1. **Temporal-property gap:** at least **98/508 tasks (19.3%)** state a bounded,
   persistence, progress, or protocol/ordering requirement but have no
   recognizable native temporal property or formal temporal scoring. All 98
   have a functional harness; 97 have recognizable finite event-driven checks.
2. **Synthesis-equivalence gap:** at least **16/508 tasks (3.1%)** explicitly
   require functional equivalence, provide original RTL, and run Yosys, but
   have no recognizable formal-equivalence or post-synthesis behavioral
   comparison. This is **16/16 tasks** in the explicit-equivalence stratum.

These are lower bounds on missing *scoring evidence*, not defect rates in model
outputs. The detector counts only explicit language it recognizes, so omitted
or differently worded contracts can only make the true coverage gap larger.

### Temporal contract coverage

| Benchmark subset | Tasks | Explicit temporal contract | Finite-trace scoring within that stratum | Native temporal property | Formal temporal scoring |
|---|---:|---:|---:|---:|---:|
| VerilogEval specification-to-RTL | 156 | 9 | 9 | 0 | 0 |
| RTLLM v2 repository tasks | 50 | 8 | 8 | 0 | 0 |
| CVDP v1.1 open-tool, non-agentic generation | 302 | 81 | 80 | 0 | 0 |
| **Combined descriptive inventory** | **508** | **98** | **97** | **0** | **0** |

The 98 unique temporal tasks include 83 bounded-latency or cycle-exact
contracts, 5 persistence contracts, 4 progress/liveness contracts, and 14
protocol/ordering contracts. Categories overlap. The protocol group includes
ready/valid, backpressure, FIFO overflow/underflow, and transaction-ordering
language.

The CVDP task without a recognizable finite value check is
`cvdp_copilot_cont_adder_0023`: its cocotb tests drive cycles and log the
outputs, but the supplied test module contains no output assertion. This is
reported separately rather than being silently called temporal coverage.

### Synthesis and equivalence coverage

| Benchmark subset | Explicit synthesis contract | Contract also invokes synthesis | Explicit equivalence contract | Equivalence task has original RTL + synthesis | Formal equivalence | Post-synthesis behavior comparison |
|---|---:|---:|---:|---:|---:|---:|
| VerilogEval specification-to-RTL | 0 | 0 | 0 | 0 | 0 | 0 |
| RTLLM v2 repository tasks | 0 | 0 | 0 | 0 | 0 | 0 |
| CVDP v1.1 open-tool, non-agentic generation | 31 | 16 | 16 | 16 | 0 | 0 |
| **Combined descriptive inventory** | **31** | **16** | **16** | **16** | **0** | **0** |

CVDP contains 25 harnesses that invoke Yosys in total. Sixteen coincide with
an explicit synthesis contract; the other nine are tool-driven repair tasks.
Conversely, **15/31 explicit synthesis-contract tasks (48.4%)** do not invoke a
recognizable synthesis tool in their supplied scoring artifacts.

All 16 explicit-equivalence tasks are CVDP optimization tasks:

- `cvdp_copilot_64b66b_encoder_0022`
- `cvdp_copilot_aes_key_expansion_0001`
- `cvdp_copilot_cont_adder_0045`
- `cvdp_copilot_fan_controller_0008`
- `cvdp_copilot_gaussian_rounding_div_0022`
- `cvdp_copilot_gaussian_rounding_div_0023`
- `cvdp_copilot_gcd_0038`
- `cvdp_copilot_gcd_0045`
- `cvdp_copilot_generic_nbit_counter_0039`
- `cvdp_copilot_image_rotate_0015`
- `cvdp_copilot_scrambler_0024`
- `cvdp_copilot_sorter_0051`
- `cvdp_copilot_sorter_0057`
- `cvdp_copilot_sorter_0059`
- `cvdp_copilot_sync_serial_communication_0052`
- `cvdp_copilot_vga_controller_0026`

In each case, synthesis success and finite RTL simulation answer useful
questions, but they do not answer the task's explicit equivalence question.
Synthesis establishes that a netlist can be produced; it does not establish
that the netlist implements the original design over all admissible inputs and
states.

## What “temporal correctness” means here

- **Bounded:** an event must happen at an exact cycle or within a stated number
  of cycles.
- **Persistence:** a signal or payload must remain asserted or stable until a
  release/acceptance condition.
- **Protocol/ordering:** ready/valid, request/acknowledge, backpressure,
  overflow/underflow, loss, duplication, or ordering behavior.
- **Progress/liveness:** eventual completion, fairness, or absence of
  deadlock/starvation.

A finite test can demonstrate one admissible trace. A temporal assertion or
formal property quantifies over a stated trace space. Neither automatically
subsumes the other: formal assumptions can be wrong, bounds can be too short,
and simulation remains valuable for integration and data-path validation.

The audit therefore does **not** say that 98 tasks perform no temporal testing.
It says their scored artifacts do not make a temporal property/proof obligation
recognizable. The distinction is central to the lower-bound claim.

## Detector and review method

The audit reads the frozen prompt/specification and supplied scoring artifacts
for every task. It records:

- explicit bounded, persistence, progress, and protocol contract language;
- SVA constructs and native temporal assertions;
- formal engines or proof commands;
- finite cycle/event-driven checks;
- explicit synthesis and equivalence requirements;
- synthesis-tool invocation, formal-equivalence commands, and post-synthesis
  behavioral comparison; and
- public reference RTL where the task contract makes it relevant.

Every detector-positive task and its matched excerpt was inspected during
detector refinement. False-positive patterns removed before freezing include
Markdown `##` headings mistaken for SVA delay syntax, generic “consistent
behavior” language mistaken for equivalence, arithmetic overflow mistaken for
FIFO protocol behavior, and ordinary prose “in order” mistaken for transaction
ordering.

This was an AI-assisted maintainer-session inspection, not an independent blind
review. The repository retains a deterministic 176-row validation sheet with
all 126 detector-positive tasks plus 50 sampled detector-negative tasks. Its
review columns are intentionally blank so another reviewer can estimate recall
without inheriting these judgments.

## Reproduction

```bash
.venv/bin/python scripts/audit_temporal_equivalence_benchmarks.py \
  --verilog-eval /path/to/verilog-eval \
  --rtllm /path/to/RTLLM \
  --cvdp /path/to/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl

.venv/bin/python scripts/build_temporal_equivalence_audit_validation_sample.py
```

The task-level JSON/CSV, combined lower-bound summary, and validation sheet are
under `reports/audits/`. Source datasets are not vendored.

## Controlled escape witnesses added to SV-Gap

The audit is paired with five executable witness families:

| Family | Ordinary functional outcome | Additional evidence | Unsafe finding |
|---|---|---|---|
| `temporal_backpressure` | safe = pass; unsafe = pass | bounded ready/valid persistence property | `REF-PROT-001` |
| `temporal_response` | safe = pass; unsafe = pass | bounded completion property | `REF-TEMP-001` |
| `temporal_pulse` | safe = pass; unsafe = pass | one-cycle pulse property | `REF-TEMP-002` |
| `synthesis_directive_equivalence` | safe = pass; unsafe = pass | synthesized reference miter | `REF-EQUIV-001` |
| `functional_equivalence` | safe = pass; unsafe = pass | exhaustive combinational reference miter | `REF-EQUIV-001` |

The synthesis-directive witness is the semantic case: both source-level RTL
implementations look correct to the smoke test, but `synopsys translate_off`
removes required behavior in Yosys's synthesis view. The synthesized miter
finds the divergence.

The five pairs also run Verilator `--Wall` as noncontributing contextual
evidence (with only the fixture filename warning disabled). It passes both
members without a finding. That controlled result does not establish a general
lint recall rate; it shows why ordinary lint and the specialized contract
oracles must remain separate evidence classes.

`formal-yosys` runs bounded SAT with explicit property sources, assumptions,
zero initialization, and `clk2fflogic`. `equivalence-yosys` compares a candidate
and reference after Yosys RTL synthesis. Both are controlled reference
backends. They are not unbounded liveness proofs, industrial sequential
equivalence, four-state equivalence, or silicon signoff.

## Frozen sources

- [VerilogEval](https://github.com/NVlabs/verilog-eval) commit
  `c498220d0a52248f8e3fdffe279075215bde2da6`
- [RTLLM](https://github.com/hkust-zhiyao/RTLLM) commit
  `41b26896e33b536940116a975626455eed3de65e`
- [CVDP](https://github.com/NVlabs/cvdp_benchmark) JSONL SHA-256
  `cbcd81295561ebb16e4d857e096f4d9908d042c33aff3b58abf236e868411857`

## Interpretation boundary

The strongest supported statement is: **within these frozen 508 artifacts, at
least 98 tasks expose a temporal contract without recognizable property/formal
scoring, and at least 16 expose an equivalence contract with original RTL and
synthesis but without recognizable equivalence or post-synthesis behavioral
scoring.**

Do not restate this as “only 98 temporal tasks exist,” “the benchmarks never
test timing,” “16 generated designs are wrong,” or a prevalence claim about all
AI RTL benchmarks. Negative-sample review, independent replication, and broader
parsers would be needed for stronger census claims.
