# Controlled structural-validity result

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

## What a researcher can take from this

The useful result is not the balanced fraction. It is the observable failure of
a functional pass to settle a declared production question. The evidence
profile makes that handoff explicit: what the functional oracle answered, what
the configured structural rule rejected, and what evidence should be added
next. A model or benchmark team can apply the same representation without
claiming that this small controlled suite estimates real-world defect rates.

Continue with one of these paths:

- [Create a local evidence profile from the bundled fixture](evaluate-your-model.md#first-create-and-read-an-evidence-profile).
- [Inspect a public model profile](result-profiles/openweights-deepseek-coder-v2-16b-reset-v02.md).
- [Connect your own model or agent](evaluate-your-model.md#then-connect-your-model).

## Reproduce the evidence

The pinned container reproduces the asynchronous-reset witness. The first image
pull is large and depends on network speed; execution is quick once
the image is cached:

```bash
docker run --rm ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.7 demo
```

To regenerate all four controlled witness pairs from a source checkout after
installing the documented open-source prerequisites:

```bash
python3 -m unittest discover -s tests -v
```

Candidate-level machine-readable reports are regenerated under each example's
`build/` directory and intentionally excluded from source control.
