# Reset-release replication v0.1

Frozen 2026-07-02 before model generation.

## Question

When an RTL prompt explicitly requires asynchronous reset assertion and
synchronous reset release, how often do functionally accepted generations still
connect ordinary state directly to the raw asynchronous reset?

## Design

- Eight independently framed, single-clock SystemVerilog tasks.
- Three exact model configurations: `openai-frontier-a`, `claude-sonnet-5`, and
  `claude-opus-4-8`.
- Three independent CLI calls per model-task cell: 72 planned candidates.
- No repair, conversational continuation, model tools, or candidate-dependent
  prompt changes.
- Icarus Verilog 13.0 functional oracle and SV-Gap/Yosys 0.66 structural oracle.

## Outcomes fixed before generation

The primary descriptive outcome is the structural-validity gap among candidates
that pass the task's functional test and receive a determinate structural result.
`unknown` and `tool_error` are disclosed separately and excluded from that
denominator. Candidate results are also grouped by task; the 72 candidates are
not treated as 72 independent task replications.

The preregistered failing rule is `REF-RDC-001`. Every emitted failure will be
manually checked against the normalized RTL. The reference oracle is narrow and
the result is not a silicon-failure or population-prevalence estimate.

`openai-frontier-a` is a stable configuration alias; the exact provider model identifier is withheld and recorded privately.
