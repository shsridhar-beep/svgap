# Public v0.1 release criteria

The repository is ready to become public only when all criteria below are met.

## Scientific integrity

- Every built-in rule has a passing and failing fixture.
- Every primary result preserves raw RTL, intent, logs, and tool versions.
- Unknown and tool-error outcomes are reported separately from passes.
- Claims say "detected structural violation," not "would fail in silicon."
- Limitations and adjudication procedures are visible from the README.

## User experience

- A fresh supported machine can reproduce the quickstart.
- The quickstart completes in under ten minutes after prerequisites are present.
- CLI failures have actionable messages and stable exit codes.
- Generated reports validate against the published schema.

## Community readiness

- Apache-2.0 licensing and third-party notices are complete.
- Contribution templates cover tasks and backends.
- Security guidance warns that generated RTL and test commands are untrusted.
- At least four well-scoped starter issues are ready.
- Maintainer and conduct-enforcement contacts are named.

## Evidence

- Controlled safe/unsafe witnesses reproduce on CI.
- At least one public-data audit or model pilot is versioned with the release.
- A short technical note explains the protocol without overstating prevalence.
