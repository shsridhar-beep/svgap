# Generation pilot v0.1

> Superseded for the reset-release claim by the larger frozen
> [reset replication](reset-replication-result.md). This page preserves the
> exploratory result and its provenance.

Run date: 2026-07-02

## Design

This exploratory run used six frozen prompts, three model configurations, and
one sample per configuration-task cell (18 candidates). Model tools were
disabled. Each response was evaluated without repair. The functional oracle was
Icarus Verilog; the narrow structural oracle used Yosys 0.66.

The configurations were the installed Codex CLI default, Claude's `sonnet`
alias, and Claude's `opus` alias. A post-run metadata check resolved the Claude
aliases to `claude-sonnet-5` and `claude-opus-4-8`. Codex CLI did not emit its
resolved default model identifier, so that configuration remains labeled by
interface and date rather than assigned a guessed model name.

## Result

| Outcome | Candidates |
|---|---:|
| Functional pass | 18 / 18 |
| Structural pass | 13 / 18 |
| Structural fail | 3 / 18 |
| Structural tool error | 2 / 18 |

Among the 16 functionally passing candidates for which the reference structural
oracle returned a determinate result, 3 failed: a descriptive gap of `3/16 =
18.75%`. All three failures occurred on the reset-release task. Every
configuration built a two-stage reset synchronizer but still connected the raw
asynchronous reset to the counter's asynchronous reset pin. The simulations
passed because they do not model recovery/removal timing at reset deassertion.

Two otherwise functionally passing Gray-counter candidates used SystemVerilog
function `return` syntax accepted by Icarus Verilog 13.0 but rejected by Yosys
0.66. They are reported as `tool_error`, excluded from the denominator, and not
reclassified as design failures.

## Defensible claim

The run supports a narrow existence claim: in this frozen pilot, offline
functional tests accepted all 18 generated candidates, while a declared
production-oriented structural check rejected three determinate candidates
sharing an asynchronous reset-release hazard. It does **not** support a claim
that 18.75% of generated RTL is unsafe, a comparison between models, or a
benchmark-wide prevalence estimate.

The stronger observation is task-level: the reset-release requirement failed in
all three observed configurations despite explicit prompt language. Because
there is only one reset task and one sample per cell, this is a case-study signal
to preregister and replicate, not an uncertainty-qualified estimate.

## Reproducibility and release boundary

The prompts and ingestion code are tracked under `taskpacks/pilot-v0.1/`.
Machine-readable aggregate outcomes are in
`reports/pilot-v0.1-summary.json`. Raw provider responses, normalized RTL, and
candidate reports are retained locally under `reports/generated/` and excluded
from Git pending an explicit output-release and provenance review.

Known threats to validity:

- Two vendors but three configurations; this is not three independent model
  families.
- One sample per cell and only six tasks.
- CLI-mediated generation adds provider system instructions even with tools
  disabled.
- The Codex default model was not resolved in emitted metadata.
- The built-in oracle covers only narrow structural shapes and is not signoff.
- Two Yosys parse failures make the result sensitive to open-tool frontend
  coverage.
