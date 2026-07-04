# Frontier-model research workflows

SV-Gap gives chip-design capability researchers a way to study more than whether
a model emits RTL that passes a supplied testbench. The central object is the
handoff evidence: which production questions are answered, failed, or still
unanswered, and what evidence would resolve the uncertainty.

The public [`challenges/v0.1`](../challenges/v0.1/) contract defines three
incremental tracks.

## Generation

The model produces RTL and an evaluation artifact. The score profile records
functional acceptance, whether structural evaluation was determinate, whether
it passed, whether functional provenance was declared, and whether tools ran
cleanly. This separates code-generation capability from evidence-generation
capability.

## Diagnosis

The model reads evaluation evidence and classifies production questions as
answered, failed, or unanswered. An unanswered question must include the next
evidence required. This tests whether a frontier model understands the boundary
of an offline result rather than merely restating a pass/fail label.

The v0.1 scorer checks classifications against the task key and requires
evidence text and a resolution path. It does not establish that free-form
evidence prose is semantically correct. A study making that stronger claim
needs a declared independent adjudication method.

## Repair

The model repairs a candidate with a declared structural finding. The profile
requires that the target finding existed before, is absent afterward, the
functional oracle still passes, structural evaluation passes, and no new rule
regression appears. It also requires the same candidate identifier and
structural backend before and after. Source-level equivalence remains bounded by
the provenance carried in the submitted reports.

## Why researchers may contribute

The contracts create separable research surfaces:

- generation policies that optimize for evidence-complete handoff;
- tool-using agents that request missing intent instead of guessing it;
- diagnosis methods calibrated to explicit unknown states;
- repair agents evaluated for both target removal and regression avoidance;
- new open checker backends and intent-carrying digital RTL taskpacks; and
- reproducible cross-model studies using profiles rather than one blended score.

This is a collaboration surface, not a claim that the example submissions are
model results. The example reports are synthetic contract fixtures. All current
workflows are limited to digital RTL and configured open-source evidence, and a
passing profile is not silicon signoff.
