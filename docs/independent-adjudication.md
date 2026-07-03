# Independent adjudication protocol

SV-Gap's first authoring-session review is not independent. Before the
reset-release result is submitted as research evidence, at least two reviewers
with CDC/RDC or RTL signoff experience should independently label the blinded
72-case packet.

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
and private mapping are excluded from Git. Keep the mapping—and any public
model-labeled candidate bundle—away from reviewers until all independent labels
are locked. The earlier v0.1 deterministic-ID packet is revoked because its
model/sample identities were enumerable from public information. v0.2 was
superseded after functional compile errors were separated from behavioral fails.
