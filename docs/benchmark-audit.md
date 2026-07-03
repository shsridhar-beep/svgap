# Public benchmark structural-identifiability audit

Audit date: 2026-07-02

## Result

| Benchmark subset | Tasks | Functional oracle | Multi-clock | Usable structural intent | Native CDC/RDC scoring |
|---|---:|---:|---:|---:|---:|
| VerilogEval specification-to-RTL | 156 | 156 | 0 (0.0%) | 0 | 0 |
| RTLLM v2 repository tasks | 50 | 50 | 2 (4.0%) | 2 | 0 |
| CVDP v1.1 open-tool, non-agentic generation | 302 | 302 | 10 (3.3%) | 9 | 0 |
| **Combined descriptive inventory** | **508** | **508** | **12 (2.4%)** | **11** | **0** |

The combined row reports heuristic detector outputs, not a validated census or
population estimate. The three benchmark suites differ in construction,
difficulty, and task family; negative cases have not been manually censused.

## Definitions

- **Functional oracle:** the task ships an executable testbench or harness.
- **Multi-clock:** the target module exposes at least two clock-like input
  ports after excluding clock-enable signals.
- **Usable structural intent:** a multi-clock specification explicitly states
  asynchronous, synchronization, or clock-domain intent sufficient to define a
  reference audit. Merely using two clock names is not enough.
- **Native CDC/RDC scoring:** the supplied benchmark harness includes a
  structural checker, structural assertions, or SDC/XDC constraints as a scored
  evaluation dimension.

Multiple reset-named inputs are retained as manual-review candidates but are not
automatically counted as reset-domain risk. Reset-domain relationships require
more intent than signal-name matching.

## Manual review

The detector's two RTLLM multi-clock candidates are its asynchronous FIFO and multi-bit
synchronizer. Both state synchronization intent; neither ships structural
constraints or native CDC/RDC scoring.

The ten manually reviewed CVDP positives are multi-clock tasks in the audited subset: variants
of asynchronous FIFOs, pulse synchronizers, mux synchronizers, clock comparison
or detection, and a two-clock GFCM task. Nine explicitly state synchronization
intent. The clock-jitter task exposes `clk` and `system_clk` but does not state
their relationship, so it is not counted as structurally identifiable.

## Reproduction

```bash
svgap audit verilog-eval /path/to/verilog-eval --output reports/audits
svgap audit rtllm /path/to/RTLLM --output reports/audits
svgap audit cvdp /path/to/cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl --output reports/audits
```

The task-level JSON and CSV files include parsed ports, evidence, and
manual-review flags. Source data are not vendored.

## Frozen sources

- VerilogEval commit `c498220d0a52248f8e3fdffe279075215bde2da6`
- RTLLM commit `41b26896e33b536940116a975626455eed3de65e`
- CVDP JSONL SHA-256
  `cbcd81295561ebb16e4d857e096f4d9908d042c33aff3b58abf236e868411857`

The CVDP dataset describes non-code content as CC BY 4.0, original code as
Apache-2.0, and derivative datapoints under the component licenses in its
NOTICE. This audit retains identifiers and derived metadata only.

## Interpretation boundary

This audit supports a narrower claim: the current heuristic detected limited
multi-clock exposure and no recognizable CDC/RDC scoring artifacts in these
snapshots. Parser recall and native-scoring recall have not been established on
a manually reviewed negative sample, so “only 12 exist” and “none score CDC/RDC”
are not yet justified. The audit does not assess the behavioral purposes of the
functional tests or defect prevalence in generated RTL.
