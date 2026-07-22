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

## Public evidence submissions

The profiles below are maintainer-produced anchors; independent
submissions are welcome and are listed with full attribution. Start
with a
[one-sentence production question](https://github.com/shsridhar-beep/svgap/issues/new?template=production_question.yml)
or go straight to [submitting results](submitting-results.md).

| Submission | Track | Configuration | Provenance | Contributor |
|---|---|---|---|---|
| [Codex gpt-5.5 reset-release generation profile](result-profiles/codex-gpt-5.5-reset-v02-01.md) | `generation` | `gpt-5.5` | `public` | Shraddha Sridhar |
| [GPT-4.1 mini reset-release v0.2 smoke profile](result-profiles/gpt-4-1-mini-reset-v02-smoke-01.md) | `generation` | `gpt-4.1-mini` | `public` | Siddhanth Kalyanaraman (@sidbu546) |
| [DeepSeek-Coder-V2-16B open-weights reset-release generation profile](result-profiles/openweights-deepseek-coder-v2-16b-reset-v02.md) | `generation` | `deepseek-coder-v2-16b` | `public` | Shraddha Sridhar |
| [Qwen2.5-Coder-7B open-weights reset-release generation profile](result-profiles/openweights-qwen25-coder-7b-reset-v02.md) | `generation` | `qwen2.5-coder-7b` | `public` | Shraddha Sridhar |

## Interpretation boundary

Profiles describe submitted digital RTL evidence under configured open-source checks. They are not silicon signoff, population estimates, or model rankings.
