# Frontier-model handoff baseline v0.1

Run date: 2026-07-05

This exploratory baseline exercises all three SV-Gap challenge tracks without
claiming a model ranking or population estimate.

- **Generation** reuses the immutable 72-call reset-release artifact across
  three archived model configurations.
- **Diagnosis** gives the same normalized evidence case to openai-frontier-a and
  GPT-5.4 with xhigh reasoning and no tools.
- **Repair** gives both configurations the same unsafe reset-release module,
  without the safe reference, and evaluates the normalized returned RTL.

Only normalized submissions are published. Raw provider transcripts and session
identifiers are excluded. Both diagnosis and repair models are from one vendor;
cross-vendor replication remains an open contribution.

Rebuild reports and the registry:

```bash
python scripts/build_adoption_baseline.py
python scripts/verify_result_registry.py
```

Interpret profiles, not an aggregate winner. A challenge pass remains bounded
by the configured functional and structural evidence and is not silicon signoff.

`openai-frontier-a` is a stable configuration alias; the exact provider model identifier is withheld and recorded privately.
