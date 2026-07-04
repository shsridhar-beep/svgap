# Generic prerecorded adjudication calibration

These traces exercise the generic SV-Gap comparator and adjudication contract.
They are manually authored digital trace fixtures, not outputs from reset-skew
instrumentation and not evidence about a generated candidate.

The suite includes a known divergence, a globally delayed but equivalent trace,
and an intentionally inconclusive candidate-digest mismatch. Run it with a
maximum shift of one sample:

```bash
svgap calibrate-adjudicator examples/adjudication_calibration/suite.json --max-shift 1
```

No netlist rewriting, per-flop perturbation, or reset-skew implementation is
included.
