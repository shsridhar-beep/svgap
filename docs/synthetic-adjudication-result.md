# Synthetic adjudication result

Run date: 2026-07-02

This robustness study used four blinded reviewer configurations with two
isolated repeats each over 72 target candidates and 12 hidden calibration
controls. It is synthetic review, not independent human CDC/RDC adjudication.

## Calibration

| Repeat panel | Correct | Accuracy |
|---|---:|---:|
| openai-frontier-b/repeat-01 | 12/12 | 1.000 |
| openai-frontier-b/repeat-02 | 12/12 | 1.000 |
| gpt-5.5/repeat-01 | 12/12 | 1.000 |
| gpt-5.5/repeat-02 | 12/12 | 1.000 |
| claude-fable-5/repeat-01 | 12/12 | 1.000 |
| claude-fable-5/repeat-02 | 12/12 | 1.000 |
| claude-haiku-4-5/repeat-01 | 12/12 | 1.000 |
| claude-haiku-4-5/repeat-02 | 11/12 | 0.917 |

## Repeat stability

| Reviewer configuration | Exact agreement | Rate | Cohen kappa |
|---|---:|---:|---:|
| openai-frontier-b | 72/72 | 1.000 | 1.000 |
| gpt-5.5 | 72/72 | 1.000 | 1.000 |
| claude-fable-5 | 72/72 | 1.000 | 1.000 |
| claude-haiku-4-5 | 71/72 | 0.986 | 0.957 |

Nominal Krippendorff alpha across all eight repeat panels was `0.989`.
Across the 28 pairwise repeat-panel comparisons, exact agreement ranged from
`0.986` to `1.000`, and nominal Cohen kappa ranged from
`0.957` to `1.000`.

## Conservative consensus

Repeat disagreement collapses a configuration vote to `uncertain`; at least
three of four configurations must agree for `yes` or `no`.

- All 72 targets: yes=15, no=57, unresolved=0.
- Among 57 functional passes:
  yes=14, no=43, unresolved=0.

Reference-oracle comparison:

- `oracle_no__consensus_no`: 57
- `oracle_yes__consensus_yes`: 15

## Vendor-disjoint sensitivity analysis

Every reviewer configuration shares a vendor with at least one generator
configuration, so each candidate was rescored using only the two reviewer
configurations whose vendor differs from the candidate's generator, with
unanimity required for `yes` or `no`
(`scripts/analyze_vendor_disjoint.py`).

- All 72 targets: yes=15, no=57, unresolved=0 — identical to the full-panel
  consensus and the reference oracle.
- Among 57 functional passes: yes=14, no=43, unresolved=0.
- By generator vendor: Anthropic-generated candidates score 9 yes / 39 no
  under OpenAI-only review; OpenAI-generated candidates score 6 yes / 18 no
  under Anthropic-only review.

Same-vendor and same-family reviewer/generator pairings therefore do not
drive any consensus label in this study. Patterns invisible to both vendor
families remain uncontrolled by construction.

## Interpretation boundary

These results test whether diverse model configurations can reproduce the
case-level structural distinction under blinding. They do not establish a
population prevalence, silicon-failure rate, model ranking, or human-validated
defect rate. Any unresolved cases remain unresolved rather than being forced
through post-hoc arbitration. The author-confirmed lower-bound claim and the
human-review requirement remain in force.
