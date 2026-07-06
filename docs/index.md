# SV-Gap documentation

SV-Gap makes the gap between “passes the benchmark” and “reviewable by a
chip-design team” explicit for AI-generated digital RTL.

![SV-Gap turns an offline pass into an evidence profile](assets/svgap-demo.svg)

## Start here

- [Run the two-minute demonstration](https://github.com/shsridhar-beep/svgap#see-the-gap-in-two-minutes)
- [Run one packaged model-evaluation task](evaluate-your-model.md)
- [Bring your own RTL](bring-your-own-rtl.md)
- [Integrate an existing benchmark](integrating-existing-benchmarks.md)
- [Study frontier-model handoff capability](frontier-model-research.md)

## Copy-paste JSON demo

Use `--json` with `--output` when a CI job, issue, or agent benchmark needs a
machine-readable first result and a preserved reproducer:

```bash
svgap demo --json --output demo-output \
  | jq '{status, safe: .safe.structural, unsafe: .unsafe.structural, findings: .unsafe.findings}'
```

```json
{
  "findings": [
    "REF-RDC-001"
  ],
  "safe": "pass",
  "status": "pass",
  "unsafe": "fail"
}
```

Attach `demo-output/summary.json`, both `*/build/report.json` files, and the
preserved manifests/RTL sources when filing an issue or publishing a CI
artifact. Do not commit `demo-output`; it is generated evidence.

Claim boundary: this controlled witness shows that the supplied functional
oracle does not identify the structural reset-release finding. It is not a
defect-rate estimate or silicon signoff.

## Build the ecosystem

- [Write a checker backend](backend-sdk.md)
- [Understand the architecture](architecture.md)
- [Review the scope boundary](scope-boundary.md)
- [Contribute](https://github.com/shsridhar-beep/svgap/blob/main/CONTRIBUTING.md)

## Research evidence

- [Compact research note](compact-research-note.md)
- [Controlled result](controlled-result.md)
- [Reset-release result](reset-replication-result.md)
- [Benchmark audit](benchmark-audit.md)
- [Methodology](methodology.md)
- [Limitations](limitations.md)
