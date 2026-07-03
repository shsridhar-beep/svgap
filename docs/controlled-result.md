# Controlled observability result

Run date: 2026-07-02

Toolchain:

- SV-Gap reference oracle 0.1
- Yosys 0.66
- Icarus Verilog 13.0

| Witness | Functional unsafe | Structural unsafe | Functional safe | Structural safe |
|---|---:|---:|---:|---:|
| Stable level crossing | pass | fail (`REF-CDC-001`) | pass | pass |
| Combinational source crossing | pass | fail (`REF-CDC-002`) | pass | pass |
| Multi-bit counter crossing | pass | fail (`REF-CDC-003`) | pass | pass |
| Asynchronous reset release | pass | fail (`REF-RDC-001`) | pass | pass |

Across the eight deliberately balanced candidates, all eight pass their
functional simulation and four fail the configured structural oracle. The CLI
therefore reports a structural-validity gap of `0.500`.

**Interpretation:** `0.500` is a harness-validation result created by the paired
experimental design. It is not an estimate of defect prevalence in models,
benchmarks, or production RTL. The defensible conclusion is narrower: for each
controlled witness, the functional oracle assigns the same successful outcome
to candidates that the declared structural oracle distinguishes.

Reproduce with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Candidate-level machine-readable reports are regenerated under each example's
`build/` directory and intentionally excluded from source control.
