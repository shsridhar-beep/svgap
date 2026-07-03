# Limitations

SV-Gap v0.1 intentionally favors auditable conclusions over broad coverage.

- The built-in reference oracle recognizes only documented structural shapes.
- Yosys elaboration can erase or transform source-level intent.
- Yosys 0.66 rejects some SystemVerilog function syntax accepted by Icarus
  Verilog 13.0; these cases are reported as `tool_error`, not design failures.
- Clock and reset metadata are supplied by the evaluator and may be wrong.
- Safe CDC is protocol-dependent; structure alone cannot prove every protocol.
- Gray recognition checks a declared signal and XOR-based source cone; it does
  not formally prove single-bit transition behavior for all reachable states.
- Functional tests do not model analog metastability.
- A clean report is not evidence of silicon signoff.
- Findings require expert review before being described as field failures.
- Structural `pass` means that the configured narrow rules emitted no finding;
  it does not establish a true negative. Gated or inverted resets, async
  set/reset cells, mux hazards, and broader protocols remain incomplete.
- Benchmark interface/scoring detection is heuristic. Reported negative counts
  are not a validated census until negative samples are manually reviewed.

The absence of a mature, broadly accessible open-source CDC/RDC signoff tool is
itself an ecosystem limitation. SV-Gap therefore keeps checker execution behind
a backend boundary rather than presenting its reference oracle as comprehensive.
