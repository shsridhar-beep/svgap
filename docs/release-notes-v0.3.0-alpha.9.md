# SV-Gap v0.3.0-alpha.9

This release adds a bounded power-on state case study and a descriptive
benchmark audit.

`REF-XPROP-001` checks whether un-reset operational state can reach a module
output when the manifest explicitly requires reset coverage at power-on. The
rule ships with a safe and unsafe controlled witness. Both witnesses pass the
same nominal functional simulation, while the configured structural result
separates them. A separate perturbation test documents the four-state behavior
that hides the distinction from the nominal test.

The release also adds a reproducible descriptive inventory of 508 public
AI-RTL tasks from frozen VerilogEval, RTLLM, and CVDP snapshots. The detector
classifies 373 tasks as sequential, 253 as exposing a reset-like input, 211 as
stating some reset behavior, and 28 as stating comprehensive reset coverage.
It finds no recognizable harness scoring that explicitly perturbs unknown
internal initial state. These are heuristic detector outputs, not a validated
census, defect-prevalence estimate, or model ranking.

Task-level derived JSON and CSV, detector code, tests, source revisions, and a
blank deterministic challenge sample are included. Source benchmark data are
not vendored.
