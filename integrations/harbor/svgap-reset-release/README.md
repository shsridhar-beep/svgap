# Can your RTL agent pass simulation and still be wrong?

Yes. An agent can produce SystemVerilog that passes its testbench while wiring
an asynchronous reset directly into ordinary state. Simulation says pass. The
structural evidence says the design releases reset unsafely.

This compact dataset makes that difference measurable. Eight reset-release
tasks evaluate each generated design twice:

1. Does it do the requested job in simulation?
2. Does every state element satisfy the declared synchronous reset-release
   requirement?

The same candidate is used for both questions. An unanswered structural
question never becomes a pass.

## Try the experiment on your agent

```bash
harbor run \
  -d svgap/svgap-reset-release@0.2 \
  -a YOUR_AGENT \
  -m YOUR_MODEL
```

Already using Harbor for agent evals? This is a one-flag dataset change. The
image includes the open-source Yosys and Icarus Verilog evaluation stack, so
you do not need an EDA installation on the host.

## The first public run found the gap

A single `gpt-5.5` Codex run produced:

| Outcome | Tasks |
|---|---:|
| Passed functional simulation | 7 / 8 |
| Passed both functional and structural checks | 5 / 8 |
| Passed simulation but failed reset-release structure | 2 / 8 |
| Infrastructure unknowns or tool errors | 0 / 8 |

The two gap members were `reset-counter` and `reset-credits`. Both simulated
successfully. Both retained raw asynchronous reset paths into state that was
required to release synchronously.

[Read the complete evidence profile](https://shsridhar-beep.github.io/svgap/result-profiles/codex-gpt-5.5-reset-v02-01/)
or inspect the
[content-addressed reports](https://github.com/shsridhar-beep/svgap/tree/main/results/submissions/codex-gpt-5.5-reset-v02-01).

This one run demonstrates the evaluation behavior. It is not a population
estimate or a general model ranking.

## What the eight tasks probe

The tasks cover counters, configuration state, credits, events, control state,
fault status, timers, and watchdog logic. Every prompt requires asynchronous
reset assertion and clock-aligned release into functional state.

Each task ships with:

- a functional simulation oracle;
- an explicit clock and reset-intent declaration;
- a structural `REF-RDC-001` check;
- a safe Oracle solution; and
- a known-unsafe witness that passes simulation but fails the structural rule.

The unsafe witness calibrates the evaluator. It is never installed as an Oracle
solution and is never presented as a model result.

## How to read the score

| Harbor metric | Meaning |
|---|---|
| `functional_accept` | The supplied simulation oracle passed. |
| `structural_accept` | The configured reset-release rule passed. |
| `gap_member` | Functional pass and structural fail on the same RTL. |
| `reward` | Both functional and structural checks passed. |
| `unknown` | A configured question remained unanswered. |
| `tool_error` | An evidence-producing tool failed. |

Every run retains the candidate RTL, full SV-Gap JSON report, readable HTML
evidence profile, and Harbor verdict. The numeric reward is a convenience, not
a replacement for the evidence record.

## Why this exists

Most code-agent evals stop when tests pass. Hardware has important properties
that ordinary simulation may not exercise. SV-Gap adds an explicit structural
validity layer so researchers can measure that blind spot without adopting a
proprietary signoff flow.

This dataset is deliberately narrow. It evaluates one reset-release property
on eight digital RTL tasks. It does not claim silicon signoff, certification,
comprehensive CDC or RDC coverage, or hardware safety.

## Reproduce and contribute

The evaluator image is pinned to the public SV-Gap `v0.3.0-alpha.6` container
digest. All eight safe Oracle solutions pass both layers, and all eight unsafe
witnesses pass functional simulation while failing the structural rule.

Harbor is the execution and distribution surface. The SV-Gap repository is the
canonical, claim-disciplined results record. Convert a complete Harbor job into
a ready-to-review contribution with:

```bash
svgap submission from-harbor JOB_DIRECTORY \
  --dataset integrations/harbor/svgap-reset-release \
  --id YOUR-SUBMISSION-ID \
  --title "YOUR TITLE" \
  --provenance-level public \
  --provider YOUR_PROVIDER \
  --contributor "YOUR NAME" \
  --output results/submissions/YOUR-SUBMISSION-ID
```

The importer rejects partial jobs, task or image drift, mixed model
configurations, and disagreement among the numeric rewards, Harbor verdicts,
and full SV-Gap reports.

## Links

- [SV-Gap source and methodology](https://github.com/shsridhar-beep/svgap)
- [How to submit results](https://shsridhar-beep.github.io/svgap/submitting-results/)
- [Frozen reset-replication taskpack](https://github.com/shsridhar-beep/svgap/tree/main/taskpacks/reset-replication-v0.2)
- [Harbor adapter source](https://github.com/shsridhar-beep/svgap/tree/main/integrations/harbor/svgap-reset-release)
