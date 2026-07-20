# Preregistered protocol: power-on prevalence study

Status: frozen v1.0 on 2026-07-20. The SHA-256 digest of this file is
posted to the repository issue tracker at freeze time, before any
confirmatory generation, so the method provably predates the data.

This protocol is a community-runnable instrument. The maintainer commits
to freezing the method here and to accepting conforming results into the
registry. The maintainer makes no commitment to run the study, and the
published number belongs to whoever runs it honestly.

## Question

Among functionally accepted candidates generated against a frozen
power-on taskpack under declared intent, what fraction carries
`REF-XPROP` structural findings? Secondary, across configurations: does a
higher functional pass rate come with a lower structural-finding rate
among passes, or does the finding rate persist as functional scores
climb? The second question operationalizes the reward-signal argument:
properties invisible to the scoring oracle are invisible to optimization.

## Inputs the runner fixes before generating

1. **Taskpack.** Any frozen taskpack whose manifests declare
   `power_on = "reset_required"`, published with a canonical tree digest
   (`scripts/taskpack_digest.py`) before generation. The runner records
   the digest in the submission. A first-party power-on taskpack ships
   from this repository when ready; the protocol does not wait for it.
2. **Configurations.** Two or more model configurations, named per the
   repository alias policy (open-weights configurations by identifier;
   frontier configurations by stable alias only).
3. **Sampling plan.** Balanced per-cell sampling (every configuration
   runs every task the same number of times), with the per-cell repeat
   count and its power justification stated before generation. Reports
   built on fewer than eight tasks or fewer than thirty total functional
   passes are labeled underpowered by construction.
4. **Generation settings.** Temperature, context, tool access (expected:
   none), and repair policy (expected: none) are declared before
   generation and apply to every cell identically.

## Blinding

Generation runs blind-by-construction: candidates stay out of public
artifacts until the run's verdicts lock. The runner posts digests of the
raw generated outputs before any scoring, then scores, then publishes the
full bundle. Lock first, score second, publish third.

## Scoring and adjudication

Functional scoring uses the taskpack's shipped testbenches. Structural
scoring runs BOTH open reference backends (`reference-yosys` and the
`naja` extra); a verdict counts as confirmed when the two backends agree
rule for rule. Divergences are reported as `unknown`, disclosed in the
submission, and adjudicated openly on the repository. `unknown` and
`tool_error` never count as pass. Duplicate outputs within a cell are
reported and deduplicated in a sensitivity analysis, since generation
events are the unit of collection while distinct designs are the unit of
interest.

The oracle's validation basis is public and citable: an independent blind
expert review concordant on every reviewed case
([independent review result](independent-review-result.md)), a blinded
synthetic panel (alpha 0.989), and 72/72 rule-for-rule cross-oracle
agreement ([cross-oracle result](cross-oracle-naja-result.md)). Adding
independent human adjudication per the
[adjudication protocol](independent-adjudication.md) is welcome and
raises the result's provenance level; the dual-oracle floor above is the
minimum for registry acceptance.

## Estimand and analysis

The primary estimand is the detection fraction: the share of functionally
accepted candidates carrying at least one error-severity `REF-XPROP`
finding, reported with task-clustered uncertainty (cluster bootstrap over
tasks, or an equivalent prespecified method), overall and per
configuration. The secondary analysis reports the relationship between
per-configuration functional pass rate and structural-finding rate among
its passes. Analysis code ships with the submission.

## Stopping rule and reporting

One run of the declared plan, evaluated once; the runner publishes
regardless of the outcome, as a registry submission
(`svgap submission init/validate/bundle`) with full provenance. The
report states its claim boundary: a detection fraction on that taskpack
for those configurations at that time, and neither a universal defect
rate nor a model ranking.

## Prior work disclosure

The maintainer has run exploratory power-on generations privately; they
informed this design, are labeled pilot if ever published, and are
excluded from any confirmatory analysis under this protocol.
