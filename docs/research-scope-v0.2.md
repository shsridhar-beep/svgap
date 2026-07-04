# Research scope v0.2: making the production trust gap legible

## Objective

SV-Gap is a measurement framework for explaining why an artifact that succeeds
under an offline research evaluation may still be rejected by a production
team. The primary contribution is existential and diagnostic, not a population
estimate:

> A benchmark can assign the same successful functional outcome to artifacts
> that differ on a declared production requirement, and the benchmark contract
> can omit the intent required to evaluate that requirement at all.

The project makes this failure legible by recording three independently
inspectable layers:

1. the functional result supplied by the research workflow;
2. the production intent that downstream evaluation requires; and
3. a structural result with explicit abstention and tool-failure states.

## What must be demonstrated

The core claim needs only the following evidence:

- A controlled witness pair receives the same successful functional verdict.
- A declared production property distinguishes the two implementations.
- A versioned structural oracle reports the distinction with inspectable
  evidence.
- Removing the required intent makes the structural question unanswerable
  rather than silently successful.
- The same contract can be applied to generated artifacts and existing
  benchmark metadata without changing the meaning of their functional result.

The four shipped CDC/RDC witness pairs satisfy the first three conditions. The
manifest and `unknown` state operationalize the fourth. The benchmark audit and
reset-release replication demonstrate the fifth.

## What is deliberately not required

Community release and the existential research claim do not depend on:

- estimating the prevalence of unsafe generated RTL;
- ranking models or vendors;
- showing that every structural finding causes a silicon failure;
- independent human review of every generated candidate;
- a signoff-complete open-source CDC/RDC checker; or
- generalizing the reset result to other production domains.

Those are valuable follow-on studies. They answer frequency, comparative, or
external-validity questions rather than establishing the measurement failure or
the usefulness of the evaluation contract.

## Claim hierarchy

### Primary claim

Functional success is non-identifying for some production-required structural
properties. Evaluations that report functional success alone therefore cannot
support a production-readiness conclusion for those properties.

### Secondary claim

Production validity can be unidentifiable from the benchmark artifact itself
when clock, reset, crossing, or other downstream intent is absent. Adding a
checker after the fact cannot recover intent that was never represented.

### Demonstration claim

In the frozen reset-release taskpack, the supplied functional tests accepted 57
outputs. The reference oracle identified 14 accepted outputs containing a
directly inspectable raw asynchronous-reset connection to operational state
despite a synchronized-release requirement. This is a taskpack-conditional
demonstration count, not a prevalence estimate.

### Engineering claim

An intent-carrying manifest, layered results, stable evidence, and explicit
`unknown` and `tool_error` outcomes provide a practical handoff contract between
frontier research workflows and production evaluation workflows.

## Falsifiability

The existential claim would fail for a witness if the functional oracle
distinguished its safe and unsafe members, the structural oracle failed to
distinguish them under the declared intent, or the declared property did not
correspond to a real production requirement. Each witness is therefore
executable and independently challengeable.

The framework would fail as a handoff mechanism if imported functional results
could not retain provenance, structural backends could not abstain, or evidence
could not be reproduced across a versioned toolchain. These are release
requirements for v0.2.

## Evaluation unit

SV-Gap reports candidate-level outcomes and task-level groupings. Repeated model
calls are generation events, not independent samples from a universal RTL
population. Exact duplicate normalized outputs are disclosed separately. No
confidence interval or percentage is presented as population prevalence without
a separately designed sampling study.

## Community invitation

Contributors do not need to accept the reference oracle as ground truth. They
can contribute competing backends, intent-bearing taskpacks, imported functional
results, disputed-case evidence, and domain-specific production properties. The
framework succeeds when disagreements become explicit records rather than
unexamined reasons for production teams to distrust research artifacts.
