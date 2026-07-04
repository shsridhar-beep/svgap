# CI and container integration

## Pinned open-tool container

The repository Dockerfile packages SV-Gap with the official OSS CAD Suite
release `2026-05-08`. Linux x86-64 and ARM64 archives are verified against the
SHA-256 digests published in the YosysHQ GitHub release metadata before
extraction. The image uses Python `3.12.10` on Debian Bookworm.

Build and run:

```bash
docker build -t svgap:0.2.0-alpha.1 .
docker run --rm -v "$PWD:/work" svgap:0.2.0-alpha.1 \
  check examples/level_crossing/unsafe/manifest.toml
```

The OSS CAD Suite date and archive digests pin the EDA binaries. The base image
is version-tagged rather than digest-pinned so the container can receive Debian
security rebuilds; record the resulting OCI image digest for an immutable study
replay.

## Reusable GitHub Action

After the v0.2 tag is published, a downstream repository can use:

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v6
  - uses: actions/setup-python@v6
    with:
      python-version: "3.12"
  - uses: shsridhar-beep/svgap@v0.2.0-alpha.1
    with:
      manifest: path/to/manifest.toml
      report: path/to/build/report.json
      sarif: build/svgap.sarif
      html: build/svgap.html
```

The action installs only the open-source Yosys and Icarus packages available on
the GitHub Ubuntu runner, evaluates the candidate, and writes deterministic
SARIF and static HTML. A structural finding leaves the action with exit status
1 after the evidence files are written, allowing it to act as a gate.

For a bitwise-pinned research run, use the container and record its OCI digest.
The convenience action intentionally follows the runner's maintained package
repository and records exact tool versions in each report.

## SARIF upload

Repositories that enable GitHub code scanning can upload the generated file in
a subsequent step with `github/codeql-action/upload-sarif`. Grant
`security-events: write` only in the caller workflow that needs the upload;
SV-Gap's composite action does not request that permission itself.

## Security boundary

Both integrations process generated RTL. Functional commands from an untrusted
manifest can execute arbitrary programs inside their environment. Prefer
content-bound imported functional results, a disposable container, and
read-only source mounts for contributed artifacts.
