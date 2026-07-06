## What changed

Describe the evaluation contract, rule, task, backend, or documentation change.

## Evidence

- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] New rules include paired passing and failing fixtures.
- [ ] `unknown` and `tool_error` remain distinct from `pass`.
- [ ] Tool versions, licenses, and known limitations are documented.
- [ ] Result submissions ran `python scripts/sync_results.py` and include the
      regenerated registry and evidence-profile pages.
- [ ] No credentials, confidential constraints, proprietary RTL, or raw provider
      transcripts are included.

## Claim boundary

State what the change demonstrates and what it does not establish. For
quantitative results, identify the denominator and treatment of inconclusive
cases.
