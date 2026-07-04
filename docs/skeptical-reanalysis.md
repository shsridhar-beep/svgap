# OpenAI Frontier A maximum-reasoning reanalysis

Audit date: 2026-07-02

A read-only OpenAI Frontier A review was run with maximum reasoning effort over the
repository, 98 stored candidate reports, available Yosys netlists, benchmark
audit artifacts, and the blinded review packet. This is an automated skeptical
review, not independent expert adjudication.

## Conclusion change

The stored arithmetic is internally consistent, and manual inspection confirmed
all 15 candidates flagged by `REF-RDC-001`. However, the earlier presentation of
`14/57 = 24.6%` as a structural-validity rate was too strong. Without independent
labels for detected passes, it is a lower-bound detection count; false negatives
are unknown. The benchmark `12/508` result is likewise a heuristic detector count,
not a validated census.

## Corrected after review

- Undeclared clock names in asynchronous groups now make analysis `unknown`.
- A register can no longer serve as its own second synchronizer stage.
- User RTL attributes can no longer waive operational reset state.
- Reset synchronizer recognition checks the declared inactive reset value.
- The controlled reset-safe witness now asserts operational reset asynchronously
  through a derived local reset and releases it synchronously.
- Functional failure and inconclusive structural outcomes now return nonzero CLI
  exit codes.
- Report output paths and task IDs are confined; functional subprocesses receive
  a reduced environment; reports are replaced atomically.
- Comma-declared Verilog inputs and common `aclk`/`clockA` names are recognized by
  the benchmark heuristic. Re-audit counts happened to remain unchanged.
- Compile/elaboration errors are separated from behavioral functional failures.
- A portable canonical taskpack digest and deterministic study summarizer were
  added.
- The reversible adjudication packet was revoked. v0.3 uses secret-keyed opaque
  IDs and hides all model and automated-outcome fields.
- A portable, content-addressed 72-candidate public artifact bundle is staged
  locally with no personal paths or raw provider transcripts.
- JSON Schema validation is now exercised in CI tests.

## Still open before a prevalence- or signoff-oriented claim

- Independent CDC/RDC review is needed before describing the reset count as an
  independently validated rate; it is not a gate on the existential framework
  claim or public artifacts.
- The reference oracle still does not cover every gated/inverted reset, async
  set/reset cell, mux hazard, or general protocol. Structural `pass` means no
  configured finding, not verified safety.
- Benchmark-audit recall needs a manually reviewed negative sample or census.
- The local pre-generation freeze was not externally timestamped and must not be
  called preregistration.
- A pinned replay container and second-simulator sensitivity run remain desirable
  before technical-note submission.
- Generated-output release authority should be documented for the provider
  account context, especially if employer resources or credentials were used.

## Strongest defensible claim now

> In a locally archived 72-call reset taskpack, 57 outputs passed the supplied
> Icarus testbenches, and at least 14 of those 57 contain a directly inspectable
> raw asynchronous-reset connection to ordinary operational state despite a
> prompt requesting synchronized release. This demonstrates that the supplied
> functional pass/fail oracles can accept that structural pattern; it does not
> establish population prevalence, a silicon-failure rate, model ranking, or a
> validated 24.6% defect rate.
