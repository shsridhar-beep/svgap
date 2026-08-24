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
- Schema-v2 `coverage` is backend-declared metadata. It makes scope inspectable
  but is not independently certified coverage.
- Ordinary lint warnings are retained as lint evidence and do not become
  structural CDC/RDC findings. The published 0/14 calibration applies only to
  the recorded Verilator/Verible versions and default configurations.
- Benchmark interface/scoring detection is heuristic. Reported negative counts
  are not a validated census until negative samples are manually reviewed.
- The core evaluator and shipped EDA dependencies are open source, but the
  generation study and synthetic robustness panel used proprietary model
  endpoints. Their prompts, normalized artifacts, schemas, and analysis code
  are public; exact model replay is not an open-tool-only workflow and is not a
  runtime dependency of SV-Gap.

The absence of a mature, broadly accessible open-source CDC/RDC signoff tool is
itself an ecosystem limitation. SV-Gap therefore keeps checker execution behind
a backend boundary rather than presenting its reference oracle as comprehensive.
