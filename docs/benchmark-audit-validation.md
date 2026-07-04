# Benchmark-audit validation appendix

The 508-task inventory is a heuristic detector result. Its role in the primary
existential claim is diagnostic, so manual validation is useful supporting
evidence rather than a gate on framework release.

## Public challenge sample

Run:

```bash
.venv/bin/python scripts/build_audit_validation_sample.py
```

The deterministic seed `svgap-benchmark-audit-validation-v0.2` selects:

- every task the detector marked for manual review; and
- 20 detector-negative VerilogEval tasks, 15 detector-negative RTLLM tasks, and
  15 detector-negative CVDP tasks.

The resulting `reports/audits/validation-sample-v0.2.csv` contains blank review
fields. Maintainers and contributors can independently label whether each task
has multiple clock domains, enough intent to define a structural question, and
native CDC/RDC scoring.

## Reporting

Keep detector output and review labels separate. Report:

- agreement by field and benchmark;
- every false positive and sampled false negative;
- evidence for native-scoring decisions;
- reviewer identity and relevant expertise; and
- the fact that negative recall is estimated from a sample, not established by
  a complete census.

Do not rewrite the frozen detector outputs after review. Parser improvements
produce a new audit version and a side-by-side difference table.

## Why it does not block the claim

The controlled witnesses are sufficient to establish that functional success
can be non-identifying. The benchmark inventory asks a separate ecosystem
question: how often current task artifacts appear to expose the intent needed
to evaluate this property. Unvalidated inventory counts can be published as
detector outputs so long as they are not called a census.
