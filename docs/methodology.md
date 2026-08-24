# Methodology

## Research claim

SV-Gap separates two questions that conventional RTL generation benchmarks
often conflate:

1. **Functional validity:** did the candidate pass the supplied behavioral
   oracle?
2. **Production-contract validity:** does the candidate satisfy the configured
   structural, temporal/protocol, or reference-equivalence obligation under
   explicit intent and assumptions?
3. **Supporting evidence:** what do contextual classes such as ordinary lint
   report without being mistaken for a stronger specialized analysis?

Two candidates can be observationally equivalent under a functional testbench
while differing in structural validity. We call the resulting measurement
failure the **structural validity gap**: the benchmark's supplied contract and
oracle do not identify whether the candidate satisfies the declared structural
property. This term is distinct from control-theoretic structural observability.

The primary claim is existential and diagnostic. It does not require an
estimate of how frequently the gap occurs in a model or population. A
population estimate is a separate follow-on question requiring a sampling
frame, clustered analysis, and broader adjudication. See
[`research-scope-v0.2.md`](research-scope-v0.2.md).

## Primary metric

For candidates whose structural result is determinate:

```text
structural_validity_gap =
  count(functional_pass and structural_fail)
  / count(functional_pass and structural_determinate)
```

The report must also disclose functional coverage, structural determinacy,
tool errors, rule severities, tool versions, and any expert adjudication.

In schema v2, an oracle affects membership only when
`contributes_to_gap = true`. The default CDC/RDC profile makes the structural
oracle contributing and ordinary lint contextual. Temporal, protocol, and
equivalence profiles can instead make their matching specialized oracle
contributing without labeling it structural. A lint failure therefore remains
visible but cannot silently redefine the configured gap. Required and optional
execution policy is separate from contribution policy.

## Evidence policy

- `pass`: the configured oracle completed and emitted no failing finding.
- `fail`: at least one configured failing rule emitted concrete evidence.
- `compile_error`: the candidate was rejected during compilation or elaboration;
  it is not conflated with a behavioral test failure or tool-infrastructure error.
- `unknown`: intent or analyzer coverage was insufficient for a conclusion.
- `tool_error`: the checker could not complete successfully.

`unknown` and `tool_error` are never counted as oracle passes.

Schema v1 has one structural result. Schema v2 has an ordered
`oracle_results` array, and each result includes its class, contribution flag,
required flag, backend provenance, findings, diagnostics, and backend-declared
coverage. Aggregators normalize v1 into a one-element structural-oracle view.

## Reference-oracle policy

The built-in oracle exists to make the evaluation contract executable and to
support controlled research fixtures. Every rule must have paired positive and
negative fixtures, a stable identifier, source evidence where available, and a
plain-language limitation statement. Broader or signoff-grade analysis belongs
in independently versioned checker backends. See the
[finding ID reference](finding-id-reference.md) for what each stable
identifier detects.

Bounded temporal and equivalence reference backends follow the same fixture and
stable-ID policy. Their reports must expose the proof bound, initialization and
assumption treatment, comparison stage, and non-signoff boundary. A bounded
property result must not be restated as an unbounded liveness proof; a
zero-initialized synthesized miter must not be restated as general sequential
or four-state equivalence.
