# Reset-release replication v0.2 protocol

## Research role

This taskpack tests whether the SV-Gap contract makes one recurring
research-to-production mismatch explicit. It is a confirmatory mechanism
demonstration, not a prevalence study or model leaderboard.

## Frozen unit

- Eight task families.
- One prompt, functional testbench, and declared reset intent per task.
- One safe and one unsafe executable reference per task.
- One structural property: `REF-RDC-001`.
- No repair or candidate-dependent prompt changes.

The reference calibration must pass before generation: both references pass the
functional test, the safe reference passes structurally, and the unsafe
reference fails with `REF-RDC-001`.

## Generation record

Before a run, publish or otherwise externally timestamp the taskpack digest and
record:

- exact requested model and provider interface version;
- configuration parameters exposed by the provider;
- number of independent calls per model-task cell;
- tool-use and conversational-continuation policy;
- generation start and completion timestamps; and
- failures that occur before an RTL candidate is returned.

Do not infer an unreported seed or resolved model identifier. Record unavailable
fields as unavailable.

## Outcomes

The primary demonstration outcome is the count of functionally accepted
candidates with a `REF-RDC-001` finding. Also report:

- every functional and structural status;
- counts by task and generation configuration;
- exact duplicate normalized RTL outputs;
- tool versions and taskpack/evaluator digests; and
- candidate-level evidence for every structural finding.

Calls are generation events, not independent draws from a universal
population. Percentages may summarize this taskpack but must not be described
as prevalence.

## Comparison with v0.1

Keep v0.1 immutable. Report v0.2 beside it and identify the material design
changes:

- the timer prompt now specifies that both internal count and `expired` reset
  to zero;
- every task has executable safe and unsafe references;
- reference calibration is an automated release gate; and
- duplicate-output disclosure is part of the frozen analysis.

Do not pool v0.1 and v0.2 into one rate. A stable result across versions is a
replication of the mechanism under two taskpack contracts, not a larger
population sample.

## Review

Author inspection, synthetic review, independent expert review, or competing
backends may be attached as separate evidence layers. None is a prerequisite
for publishing the executable taskpack or its existential result. Any evidence
layer must identify its reviewer/oracle, version, blinding status, and scope.
