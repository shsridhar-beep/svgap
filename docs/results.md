# Evidence profiles

SV-Gap publishes multidimensional evidence profiles, not a scalar
leaderboard. Functional failures, structural failures, unknowns, and tool
errors remain visible. Every profile is bounded by its taskpack, evaluator,
and provenance level.

## Frozen generation baseline

| Configuration | Candidates | Functional pass | Functional-pass / structural-fail |
|---|---:|---:|---:|
| `claude-opus-4-8` | 24 | 17 | 1 |
| `claude-sonnet-5` | 24 | 19 | 7 |
| `openai-frontier-a` | 24 | 21 | 6 |

## Exploratory diagnosis profiles

| Configuration | Overall | Passed checks | Total checks |
|---|---|---:|---:|
| `gpt-5.4` | `fail` | 8 | 9 |
| `openai-frontier-a` | `pass` | 9 | 9 |

## Exploratory repair profiles

| Configuration | Overall | Passed checks | Total checks |
|---|---|---:|---:|
| `gpt-5.4` | `pass` | 7 | 7 |
| `openai-frontier-a` | `fail` | 5 | 7 |

## Open-weights seeded baselines

Two fully public, key-free baselines run through the documented
[evaluate-your-model](evaluate-your-model.md) two-stage workflow (local
ollama generation, isolated container evaluation) and packaged with the
submission contract under
[`results/submissions/`](https://github.com/shsridhar-beep/svgap/tree/main/results/submissions):

| Configuration | Generated | Ingested | Functional pass | Determinate | Functional-pass / structural-fail |
|---|---:|---:|---:|---:|---:|
| `qwen2.5-coder:7b` (ollama) | 24 | 22 | 8 | 8 | 8 |
| `deepseek-coder-v2:16b` (ollama) | 24 | 22 | 11 | 9 | 9 |

Per model, two responses were rejected at ingestion for not containing the
required module; deepseek's two structurally indeterminate functional passes
are Yosys latch-inference `tool_error` outcomes, disclosed rather than
counted. Every structurally determinate functional pass in both baselines
contains the declared raw-asynchronous-reset pattern (`REF-RDC-001`). These
are taskpack-conditional detection counts over three unseeded samples per
task, not model rankings or defect-rate estimates.

## Community submissions

No community submission has been accepted yet. The first validated
generation, diagnosis, repair, failure, or abstention profile is
welcome; see [Submit a result](submitting-results.md).

## Interpretation boundary

Profiles describe submitted digital RTL evidence under configured open-source checks. They are not silicon signoff, population estimates, or model rankings.
