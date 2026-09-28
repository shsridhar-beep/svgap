# Limitations

SV-Gap intentionally favors auditable conclusions over broad coverage.

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
  it does not establish a true negative.
- `REF-META-001` counts a narrow direct/mux-only register-chain shape. It does
  not compute MTBF, account for placement, or model analog metastability.
- Pulse/toggle/handshake/FIFO recognition checks named structural idioms. It
  does not prove pulse-rate assumptions, bundled-data stability, FIFO
  full/empty equations, pointer monotonicity, or all reachable protocol states.
- CDC reconvergence is a taint-style combinational check over recognized
  synchronized paths. It is neither exhaustive nor path/timing aware.
- Independent-reset crossing currently reports a data dependency between
  declared reset groups; it does not recognize every isolation, retention, or
  reset-handshake protocol.
- Reset gating/reconvergence origin tracing follows elaborated combinational
  cones into sequential reset pins. Library-specific reset cells, scan/test
  overrides, power intent, and reviewed reset-tree exceptions require a broader
  backend. `allow_combination = true` is an explicit waiver, not proof.
- The strict X-control scanner is deliberately lexical after comment/string
  removal. It is not a complete SystemVerilog parser or formal X-propagation
  analysis.
- Memory power-on checks recognize complete constant `$meminit` coverage.
  Procedural scrub loops, macro initialization contracts, ECC initialization,
  retention, and technology-specific memory behavior are not yet recognized.
- Schema-v2 `coverage` separates backend-declared scope from observed execution
  facts. The bounded-formal backend can require a named reachability signal and
  records a non-vacuity witness, but this remains signal- and bound-specific;
  it does not establish complete stimulus, mutation, toggle, or signoff
  coverage, and it is not independently certified.
- Ordinary lint warnings are retained as lint evidence and do not become
  structural CDC/RDC findings. The published 0/14 calibration applies only to
  the recorded Verilator/Verible versions and default configurations. The
  expanded-study 0/11 result is likewise candidate- and configuration-bound.
- `formal-yosys` proves only the explicit immediate properties within the
  configured bound, with assumptions honored, initial registers forced to
  zero, and clocked logic lowered through `clk2fflogic`. It does not prove
  unbounded liveness, validate assumptions, or replace production formal.
- `equivalence-yosys` compares the Yosys-synthesized candidate and reference
  under a bounded, zero-initialized model. It does not perform four-state,
  state-mapped, retiming-aware, or industrial sequential equivalence.
- A public reference implementation is not automatically the only legal
  implementation. Equivalence should contribute only when the task contract
  explicitly requires that reference behavior.
- Benchmark interface/scoring detection is heuristic. Reported negative counts
  are not a validated census until negative samples are manually reviewed.
- The reset and expanded-contract generation taskpacks each contain only eight
  hand-authored tasks. Whole-task bootstrap intervals are finite-task
  sensitivity analyses, not population-prevalence intervals.
- The 48 expanded-contract candidates do not yet have independent human
  adjudication. The two equivalence tasks produced a bounded null result, so
  naturally generated synthesis-semantics divergences remain an empirical gap.
- The core evaluator and shipped EDA dependencies are open source, but the
  generation studies include proprietary hosted model configurations, and the
  synthetic robustness panel used proprietary endpoints. The expanded study
  also includes two local open-weight configurations. Prompts, normalized
  artifacts, schemas, and analysis code are public; exact hosted-model replay
  is not an open-tool-only workflow and is not a runtime dependency of SV-Gap.

The absence of a mature, broadly accessible open-source CDC/RDC signoff tool is
itself an ecosystem limitation. SV-Gap therefore keeps checker execution behind
a backend boundary rather than presenting its reference oracle as comprehensive.
