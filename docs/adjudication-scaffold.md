# Generic adjudication scaffold

SV-Gap now includes a generic, deterministic protocol for comparing prerecorded
digital observation traces. It exists to make an adjudication method inspectable
before any project-specific perturbation mechanism is approved or published.

## What is implemented

- a strict JSON trace contract and CSV normalizer;
- content digests and candidate-bound deterministic seed derivation;
- exact or golden-X-wildcard comparison with an explicit bounded global shift;
- `hazard_demonstrated`, `no_divergence_observed`, and `inconclusive` verdicts;
- a calibration gate with known-positive, known-negative, and inconclusive
  prerecorded fixtures; and
- a machine-readable adjudication report.

Run the public calibration:

```bash
svgap calibrate-adjudicator examples/adjudication_calibration/suite.json \
  --max-shift 1
```

The fixtures are deliberately synthetic and prerecorded. They validate protocol
behavior, not a candidate-level hazard claim.

## What remains blocked

`ResetReleaseSkewInstrumenter` is only a capability marker. It has no RTL or
netlist rewrite, skew injection, simulation, or candidate execution code. Any
call returns `BLOCKED_PENDING_PATENT_AND_EMPLOYER_REVIEW`. The project must not
publish a real perturbation implementation or results produced by one until the
appropriate review permits it.

Consequently, the current scaffold supports method legibility and community
review of contracts. It does not upgrade prerecorded examples into empirical
evidence about generated candidates.

## Comparator semantics

A shift of `n` compares the golden trace with its last `n` samples removed to
the observed trace with its first `n` samples removed. The remaining windows
must have equal length. This permits a declared global observation delay without
silently accepting a short matching prefix. Candidate digests and signal sets
must match or the result is inconclusive.
