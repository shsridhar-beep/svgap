# SV-Gap v0.3.0-alpha.4

This prerelease makes the frontier-research workflow usable from an installed
wheel rather than requiring knowledge of repository scripts.

## Researcher quickstart

```bash
svgap study run reset-release-v0.2 \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --smoke \
  --output my-first-svgap-study
```

The default smoke path runs one calibrated task and one sample. `--full` runs
the frozen eight-task, three-sample protocol. Both produce portable reports, a
deterministic study summary, an evidence-file list, and a static HTML profile.

## What is new

- Frozen taskpack and challenge resources ship inside the Python wheel.
- Generation can run separately from credential-free evaluation with
  `svgap study evaluate-saved`.
- Diagnosis and repair starters run through `svgap challenge run`.
- `svgap.evaluate` and taskpack discovery are public Python APIs.
- Two open-weights generation baselines provide reproducible profile anchors.
- Submission PRs use one registry/profile synchronization command.

Generated RTL remains untrusted input. Use the documented network-disabled,
credential-free container path for unreviewed outputs. Profiles are bounded by
the declared taskpack and open checker; they are not silicon signoff, population
estimates, or general model rankings.

## Release artifacts

- GitHub: `v0.3.0-alpha.4`
- PyPI: `svgap==0.3.0a4`
- Container: `ghcr.io/shsridhar-beep/svgap:v0.3.0-alpha.4`
- Container manifest: `sha256:6e29400d4c673b47bee22d7550887674e8d1b28c9edc714e5e528c119d869e21`
- Zenodo: [doi:10.5281/zenodo.21223430](https://doi.org/10.5281/zenodo.21223430)

The GitHub and PyPI wheels are byte-identical. The independently downloaded
Zenodo archive matched its published MD5 and passed the public identifier and
local-path scan.
