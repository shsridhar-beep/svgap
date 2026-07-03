# Synthetic adjudication protocol

Human CDC/RDC reviewers were not available for the first public snapshot. To
stress-test the author and reference-oracle labels without presenting model
outputs as expert ground truth, SV-Gap runs a blinded synthetic panel.

## Frozen design

- Four reviewer configurations not used to generate the candidate RTL:
  OpenAI Reviewer A, GPT-5.5, Claude Fable 5, and Claude Haiku 4.5.
- Two isolated, stateless repeats per configuration.
- Seventy-two target candidates plus 12 hidden calibration controls (six
  positive and six negative) in every repeat.
- Secret-keyed case identifiers and no generation-model identity, functional
  result, automated verdict, or other reviewer's label in the prompt.
- A `yes`/`no`/`uncertain` decision with numbered RTL evidence under a fixed
  reset-domain rubric.

The runner validates the public JSON schema and rejects evidence lines outside
the candidate. Provider-specific field aliases are normalized mechanically;
the decision itself is never rewritten by another model. Completed judgments
are immutable on resume unless `--retry-complete` is explicitly supplied.

## Analysis

Report calibration accuracy, exact within-configuration repeat agreement,
nominal Cohen's kappa, pairwise panel agreement, and nominal Krippendorff's
alpha. For a conservative four-configuration consensus, a repeat disagreement
collapses that configuration's vote to `uncertain`; at least three matching
configuration votes are required for `yes` or `no`. Everything else remains
unresolved.

Synthetic consensus is compared with the reference oracle as a robustness
analysis. It is not independent human expert adjudication, cannot establish a
silicon-failure rate, and does not convert the author-confirmed `14/57`
lower-bound count into a validated prevalence estimate.

Every reviewer configuration shares a vendor with at least one generator
configuration, and one reviewer shares a model family with one generator. No
reviewer model generated any candidate. To bound vendor-correlated blind
spots, a vendor-disjoint sensitivity analysis
(`scripts/analyze_vendor_disjoint.py`) rescores every candidate using only the
two reviewer configurations from the other vendor, requiring unanimity for
`yes` or `no`. On the locked panels this reproduces the full-panel consensus
exactly (see the [result](synthetic-adjudication-result.md)). Residual risk
from patterns both vendors miss remains, and human sample review stays the
control for it.

## Reproduction boundary

The schema and runner are public. Candidate mappings, raw reviewer transcripts,
and per-case synthetic labels remain excluded from Git to preserve the blinded
record and avoid conflating model judgments with human labels. Aggregate results
are published after all eight repeat panels are locked.

After cloning the public artifact, a fresh blinded packet can be constructed
with new opaque identifiers:

```bash
.venv/bin/python scripts/build_blinded_adjudication.py \
  --source artifacts/reset-replication-v0.1/candidates
.venv/bin/python scripts/build_synthetic_calibration.py
```

Run each configured provider twice with `scripts/run_synthetic_review.py`, then
use `scripts/analyze_synthetic_review.py`. Provider authentication is local and
must never be committed. A newly constructed packet will intentionally have
different case identifiers from the locked first-public-snapshot panel.
