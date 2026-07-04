# Independent adjudication protocol

SV-Gap's first authoring-session review is not independent. Independent review
is optional supporting evidence for the existential framework claim. It is
required only before the reset-release count is promoted from an
author-confirmed lower bound to an independently validated rate. If pursued, at
least two reviewers with CDC/RDC or RTL signoff experience should independently
label the blinded 72-case packet.

Reviewers receive candidate RTL and task intent, but not model identity,
functional results, automated findings, or one another's labels. The primary
label is `yes`, `no`, or `uncertain` for direct raw asynchronous reset exposure
of operational state. Reset synchronizer stages are exempt.

Report:

- Agreement between each reviewer and the reference oracle.
- Inter-reviewer agreement before reconciliation.
- Every overturned automated finding with rationale.
- Every reviewed structural pass labeled `yes` or `uncertain`.
- Unresolved cases separately; do not force consensus.

Only the pre-reconciliation labels should be used for agreement statistics.
Reconciled labels may be used for the final descriptive gap if the paper reports
both original and reconciled values.

Build the local packet with:

```bash
.venv/bin/python scripts/build_blinded_adjudication.py
```

The generated v0.3 packet uses random secret-keyed case identifiers. The packet
and private mapping are excluded from Git. The earlier v0.1 deterministic-ID
packet is revoked because its model/sample identities were enumerable from
public information. v0.2 was superseded after functional compile errors were
separated from behavioral fails.

## Blinding status after public artifact release

The full model-labeled candidate bundle, including automated reports, is now
public under `artifacts/reset-replication-v0.1/`. For this taskpack, blinding
is therefore **procedural, not information-theoretic**: a reviewer could in
principle match candidate RTL against the public bundle and recover model
identity and the automated verdict. Reviewers must attest that they did not
consult the public bundle, automated reports, or synthetic-panel outputs while
labeling, and the adjudication report must disclose this limitation.

Any future powered study restores blind-by-construction review: newly
generated candidates remain excluded from Git until all independent labels for
that study are locked, as this protocol originally required for the first
taskpack.
