# Methodology

## Research claim

SV-Gap separates two questions that conventional RTL generation benchmarks
often conflate:

1. **Functional validity:** did the candidate pass the supplied behavioral
   oracle?
2. **Structural validity:** does the candidate satisfy declared structural
   safety rules under explicit clock and reset intent?

Two candidates can be observationally equivalent under a functional testbench
while differing in structural validity. We call properties that the supplied
benchmark cannot distinguish its **structural observability gap**.

## Primary metric

For candidates whose structural result is determinate:

```text
structural_validity_gap =
  count(functional_pass and structural_fail)
  / count(functional_pass and structural_determinate)
```

The report must also disclose functional coverage, structural determinacy,
tool errors, rule severities, tool versions, and any expert adjudication.

## Evidence policy

- `pass`: the configured oracle completed and emitted no failing finding.
- `fail`: at least one configured failing rule emitted concrete evidence.
- `compile_error`: the candidate was rejected during compilation or elaboration;
  it is not conflated with a behavioral test failure or tool-infrastructure error.
- `unknown`: intent or analyzer coverage was insufficient for a conclusion.
- `tool_error`: the checker could not complete successfully.

`unknown` and `tool_error` are never counted as structural passes.

## Reference-oracle policy

The built-in oracle exists to make the evaluation contract executable and to
support controlled research fixtures. Every rule must have paired positive and
negative fixtures, a stable identifier, source evidence where available, and a
plain-language limitation statement. Broader or signoff-grade analysis belongs
in independently versioned checker backends.
