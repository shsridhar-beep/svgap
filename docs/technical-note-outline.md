# Technical note outline

## Working title

**When functional RTL benchmarks cannot identify production readiness**

## Draft abstract

Benchmarks for AI-generated register-transfer level designs score combinations
of compilation, simulation, formal equivalence, lint, synthesis quality, and
security policy. Those outcomes do not establish that a design is safe across
asynchronous clock and reset boundaries. We define the structural validity gap:
production-relevant structural properties
that cannot be distinguished using a benchmark's supplied specification,
metadata, and oracle. Four controlled witnesses pair RTL implementations that
receive the same coarse functional pass verdict while differing in clock- or
reset-domain structure. The same functional tests accept both members, while an explicit
structural oracle separates the unsafe and reference structures. These
witnesses do not estimate defect prevalence; they demonstrate that functional
success alone is non-identifying for an important class of silicon risks. An
auditable inventory of 508 public generation tasks finds 12 with multiple clock
inputs and none with native CDC/RDC scoring. In a separate 18-candidate
exploratory generation pilot, all candidates pass functional simulation; three
of 16 structurally determinate candidates fail the reset-release rule, and two
additional cases remain indeterminate because of checker frontend errors. These
descriptive results motivate a larger externally preregistered study rather than a model
ranking. We release the task inventory, manifests, prompts, tests, evidence
schema, and reference implementation to support reproducible measurement.

A follow-on frozen reset-release replication generated 72 candidates over eight
tasks and three model configurations. Functional simulation accepted 57; 14 of
those 57 contain an author-confirmed raw asynchronous reset path
to operational state. These taskpack-conditional detections remain provisional
until full-case independent adjudication.

A blinded synthetic robustness panel (four reviewer configurations, two
isolated repeats) reaches nominal Krippendorff alpha `0.989` and conservative
consensus identical to the reference-oracle split (15/72 overall, 14/57 among
functional passes, zero unresolved). A vendor-disjoint sensitivity analysis,
scoring each candidate only with reviewer configurations from the other
vendor, reproduces the same split exactly. This is supporting reproducibility
evidence, not a replacement for human CDC/RDC expert adjudication.

## Results sequence

1. Define functional validity, structural validity, and structural
   identifiability.
2. Demonstrate paired observational equivalence under functional simulation.
3. Demonstrate structural separation under declared intent.
4. Audit whether public benchmarks supply sufficient structural intent.
5. Report the exploratory pilot with task-level and tool-error caveats.
6. Report the frozen 72-call replication as a lower-bound detection count.
7. Report the synthetic robustness panel and its vendor-disjoint sensitivity
   analysis.
8. Preregister a larger multi-family, multi-sample estimate.

## Central figure

```text
                         functional oracle: PASS
                        /                       \
              safe implementation       unsafe implementation
                        \                       /
                    structural oracle separates them
```
