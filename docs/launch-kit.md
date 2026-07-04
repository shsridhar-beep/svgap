# Community launch kit

## One-sentence description

SV-Gap makes explicit why an AI-generated artifact can pass an offline benchmark
yet remain untrusted by production: the benchmark may neither observe nor even
represent a required production property.

## Talk demonstration

1. Run the safe and unsafe reset witnesses; both pass the same functional test.
2. Show the structural result separating them.
3. Remove reset intent and show `unknown`, not `pass`.
4. Show one public generated candidate from the reset artifact.
5. End on the handoff record: functional result + intent + structural result +
   evidence.

The point is not that one checker makes RTL production-ready. The point is that
the reason for non-adoption becomes inspectable and actionable.

## Launch post

> Frontier research teams often hand production teams an artifact plus an
> offline pass rate. Production teams need a different object: the artifact,
> declared deployment intent, layered validity results, and evidence. We built
> SV-Gap to make that mismatch executable for AI-generated RTL. The first public
> case study starts with CDC/RDC, where functional simulation can accept designs
> that differ on reset and crossing safety. We are looking for contributors who
> can add intent-bearing taskpacks, independent checker backends, and real
> research-to-production handoff cases.

## Contribution calls

Ask specifically for:

- a second open-source structural frontend or checker backend;
- a taskpack derived from a public production-style design requirement;
- an adapter that imports results from a public RTL benchmark;
- a false positive or false negative with a minimal regression fixture; and
- a CI integration from an applied research workflow.

Do not make independent human review, a model leaderboard, or agreement with the
current oracle a condition of participation.

## Maintainer demo commands

```bash
svgap check examples/reset_release/unsafe/manifest.toml
svgap check examples/reset_release/safe/manifest.toml
svgap check examples/imported_result/manifest.toml
svgap export examples/imported_result/build/report.json \
  --sarif /tmp/svgap.sarif --html /tmp/svgap.html
make calibrate-v02
```

## Release checklist

- CI, package, container, and artifact-verification jobs pass.
- Version agrees across package metadata, runtime, changelog, tag, and notes.
- v0.2 taskpack digest matches `freeze.json`.
- GitHub release is marked prerelease and includes wheels, source archive,
  schemas, taskpack archive, result archive, and checksums.
- Zenodo has ingested the tag before the DOI is advertised as that version's
  archive.
- `main` requires passing CI and disallows force pushes and deletion.
