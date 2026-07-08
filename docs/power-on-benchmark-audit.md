# Public benchmark power-on and unknown-state audit

Audit date: 2026-07-07

## Result

| Benchmark subset | Tasks | Sequential | Reset exposed | Reset behavior stated | Comprehensive state intent | Unknown-state scoring |
|---|---:|---:|---:|---:|---:|---:|
| VerilogEval specification-to-RTL | 156 | 81 | 43 | 27 | 0 | 0 |
| RTLLM v2 repository tasks | 50 | 38 | 29 | 29 | 0 | 0 |
| CVDP v1.1 open-tool, non-agentic generation | 302 | 254 | 181 | 155 | 28 | 0 |
| **Combined descriptive inventory** | **508** | **373 (73.4%)** | **253 (49.8%)** | **211 (41.5%)** | **28 (5.5%)** | **0** |

The detector found many sequential tasks and many reset-bearing tasks. It found
far fewer specifications that require reset coverage for all relevant state.
It found no harness that
explicitly randomizes internal initial state, uses an unknown-state assertion,
or compares an output against an X value as a scored condition.

This is evidence of under-representation in these frozen benchmark artifacts,
not a claim about all AI RTL benchmarks or all verification flows.

## Definitions

- **Sequential:** the interface exposes a clock-like input, or the specification
  explicitly describes registers, sequential logic, a pipeline, a counter, or
  a state machine.
- **Reset exposed:** the parsed target interface contains a reset-like input.
- **Reset behavior stated:** the specification states an action or value under
  reset. A reset pin alone does not qualify.
- **Comprehensive state intent:** the specification requires all relevant state,
  registers, or flip-flops to be reset. Resetting one named output does not
  qualify.
- **Unknown-state scoring:** the executable harness explicitly perturbs initial
  internal state or scores an X or unknown-state condition. Random functional
  inputs and ordinary case-inequality comparisons do not qualify.

Comprehensive state intent is the minimum specification evidence used here to
ask the `REF-XPROP-001` question. It does not mean the supplied functional test
actually checks that intent.

## Manual inspection and detector refinement

The 28 comprehensive-intent matches were inspected by task identifier and
matched text. The retained matches explicitly refer to all registers, all
internal state, or all flip-flops. One additional lint task prohibits an
uninitialized register but does not declare reset coverage or target-specific
power-on semantics, so it is excluded from the comprehensive-intent count.

Two false-positive patterns were found during inspection and removed before
freezing these outputs:

- randomized input data was initially confused with randomized internal state;
- generic FSM “initial state” wording was initially confused with power-on
  intent.

A broad follow-up search found harnesses that tolerate or log an X value and
harnesses that use random stimulus. Those were not counted because they do not
perturb unknown internal state or fail a candidate for the relevant condition.

## Reproduction

```bash
.venv/bin/python scripts/audit_power_on_benchmarks.py \
  --verilog-eval /path/to/verilog-eval \
  --rtllm /path/to/RTLLM \
  --cvdp /path/to/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl
```

The task-level JSON and CSV files are under `reports/audits/`. Source data are
not vendored.

To build a deterministic challenge sheet containing every detector-positive
task plus 50 sampled detector-negative tasks:

```bash
.venv/bin/python scripts/build_power_on_audit_validation_sample.py
```

The blank review columns keep detector output separate from later independent
review. A negative sample estimates detector recall; it does not turn this into
a complete manual census.

## Frozen sources

- VerilogEval commit `c498220d0a52248f8e3fdffe279075215bde2da6`
- RTLLM commit `41b26896e33b536940116a975626455eed3de65e`
- CVDP JSONL SHA-256
  `cbcd81295561ebb16e4d857e096f4d9908d042c33aff3b58abf236e868411857`

## Interpretation boundary

The strongest supported statement is: in this 508-task descriptive inventory,
the detector found 28 tasks with enough stated intent to ask the comprehensive
power-on reset question and no harness with recognizable unknown-initial-state
scoring. The outputs are heuristic detector results. Until the negative
challenge sample is independently reviewed, “only 28 exist” and “none score
unknown initial state” should not be presented as a validated census.
