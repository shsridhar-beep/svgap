# When offline success cannot identify production validity

## Compact research artifact

AI research teams commonly evaluate generated artifacts with executable offline
oracles: compile the artifact, run a test suite, compare outputs, and report a
pass rate. Production teams inherit a different obligation. They must determine
whether the implementation satisfies deployment properties that may be absent
from the functional semantics and absent from the benchmark metadata.

SV-Gap makes that handoff failure explicit for generated RTL. Clock-domain and
reset-domain safety are the first case study because standard RTL simulation
does not reproduce analog metastability or recovery/removal timing, while a CDC
or RDC analysis requires declared clock and reset relationships.

## Central result

```text
                         OFFLINE FUNCTIONAL ORACLE
                      same observation: both PASS
                         /                 \
                        /                   \
       reference implementation       hazardous implementation
                        \                   /
                         \                 /
                 DECLARED PRODUCTION INTENT +
                      STRUCTURAL ORACLE
                       PASS          FAIL
```

Four controlled witness families instantiate this construction: a stable
single-bit crossing, combinational logic before synchronization, an incoherent
multi-bit crossing, and asynchronous reset release. In every family, both
members pass the supplied functional simulation while the configured structural
rule separates them. The deliberately balanced `4/8` result validates the
measurement harness; it is not a defect-rate estimate.

## Why this is a trust problem

The production team cannot infer the missing property from a functional pass.
In many cases it cannot even run the additional evaluation because the research
artifact does not state the clock groups, reset semantics, crossing protocol, or
other intent that gives the property meaning. The resulting distrust is not
necessarily resistance to AI or a demand for more benchmark examples. It is a
traceable mismatch between what the offline result establishes and what the
production decision requires.

SV-Gap represents that mismatch as a layered record:

```text
functional result + production intent + structural result + evidence
```

Structural analysis may return `pass`, `fail`, `unknown`, or `tool_error`.
Missing intent and analyzer limitations therefore remain visible instead of
being converted into apparent success.

## Public benchmark inventory

The current automated inventory covers 508 tasks from VerilogEval, RTLLM, and
CVDP. It detects 12 tasks with multiple clock-like ports, 11 with sufficient
intent for the reference audit, and no recognizable native CDC/RDC scoring
artifact. These are heuristic inventory counts, not a validated census. Their
role in the existential argument is diagnostic: current task formats frequently
do not expose the metadata needed for this production question.

## Generated-RTL demonstration

A frozen reset-release taskpack generated 72 outputs across eight tasks and
three model configurations. Fifty-seven passed the supplied Icarus testbenches.
The reference oracle identified at least 14 of those accepted outputs with a raw
asynchronous-reset connection to operational state despite a synchronized-
release requirement. The 72 calls contain 69 unique normalized RTL texts; the
three duplicate pairs are structural passes and do not change the 14 detected
cases.

The result demonstrates recurrence within the taskpack and supplies public
artifacts for inspection. It does not estimate the frequency of the pattern in
all generated RTL. A blinded synthetic panel reproduced the case-level split,
but synthetic agreement is robustness evidence rather than human signoff.

## Contribution

The contribution is an executable evaluation contract for making production
trust failures legible:

1. attach explicit production intent to an evaluated artifact;
2. preserve the original functional result rather than replacing it;
3. apply independently versioned production-oriented oracles;
4. distinguish findings, missing information, and tool failures;
5. retain source-level evidence and provenance; and
6. allow alternative backends and adjudications to disagree visibly.

This changes the research-to-production conversation from “the benchmark says
it works” versus “production does not trust it” to a concrete account of which
property was measured, which was not, what information is missing, and what
evidence would resolve the disagreement.

## Interpretation boundary

SV-Gap v0.2 is not silicon signoff and its reference rules are intentionally
narrow. The framework is useful even when a team substitutes a commercial or
independent open checker: the durable contribution is the intent and evidence
contract, not the completeness of one backend.

## Reproduction map

- Controlled witnesses: `examples/`
- Public benchmark inventory: `reports/audits/`
- Reset taskpack: `taskpacks/reset-replication-v0.1/`
- Generated candidates: `artifacts/reset-replication-v0.1/`
- Result and limitations: `docs/reset-replication-result.md` and
  `docs/limitations.md`
- Machine-readable contracts: `schemas/`
