# Category expansion: X-optimism and metastability

Status: design, not yet implemented. Extends the reference oracle from four
rules to six, following the reference-oracle policy: every rule ships with
paired positive/negative fixtures, a stable identifier, and a limitation
statement.

## Why these two

Both are production-relevant properties invisible in kind to the functional
oracle, for two different reasons:

- **X-optimism:** four-state simulation resolves ambiguity deterministically
  (`if` on X takes the else branch; X'd state is silently flushed), so a
  testbench can accept a design whose power-up behavior in silicon is
  undefined. The oracle is not under-sampling the property; its semantics
  erase it.
- **Metastability:** no digital tool models the physical phenomenon, and this
  project must not claim to. It is operationalized the way signoff practice
  operationalizes it - declared parametric structural requirements
  (synchronizer depth) plus the perturbation semantics of
  [perturbation-adjudication.md](perturbation-adjudication.md). The physical
  phenomenon itself remains explicitly out of scope, consistent with
  [limitations.md](limitations.md).

## New rules

### REF-XPROP-001 - un-reset operational state

When the manifest declares `power_on = "reset_required"`, flag any operational
state element with no recognized reset connection (any polarity, sync or
async) whose output cone reaches a module output or a control input (mux
select, enable, branch condition) of other state.

- Synchronizer-exempt flops follow the existing exemption model.
- FPGA-style `initial`/init attributes do not count as reset unless the
  manifest declares `init_attributes_are_power_on = true`; the default models
  an ASIC target where init attributes are not silicon power-on state.
- Evidence: cell name and one witness cone path.
- Limitation: cone walking over the elaborated netlist can miss source intent
  Yosys transforms away; a clean result is not an X-safety proof.

A second rule (X-masking control constructs: wildcard/incomplete case
optimism) is recorded as a candidate `REF-XPROP-002` but intentionally not in
scope until 001 has fixtures and field results.

### REF-META-001 - declared synchronizer depth

When the manifest declares `min_sync_stages = N` for an asynchronous crossing
(default 2 when the crossing is declared without a depth), flag any recognized
synchronizer chain on that crossing with depth `< N`.

- Purely parametric: the rule checks structure against declared intent. It
  computes no MTBF and makes no frequency- or technology-based claim. MTBF
  arithmetic from evaluator-declared parameters is a possible reporting-only
  extension and is deliberately excluded from the rule.
- Distinct from `REF-CDC-001`, which fires when no second stage exists at all.
  `REF-META-001` fires when a synchronizer exists but is shallower than the
  declared requirement (e.g., declared 3-stage for a fast-clock crossing,
  implemented 2-stage).
- Evidence: chain cells and measured depth vs declared depth.
- Limitation: depth recognition inherits the synchronizer-recognition
  heuristics; unrecognized synchronizer topologies report `unknown`, not pass.

## Manifest extensions

```toml
[intent]
power_on = "reset_required"            # enables REF-XPROP-001
init_attributes_are_power_on = false   # default

[[crossings]]
# existing fields ...
min_sync_stages = 3                    # enables REF-META-001 above default
```

Absent declarations mean the rules return `unknown` for the affected scope,
never a silent pass - the same abstention contract as the existing rules.

## Witness pairs

| Family | Unsafe shape | Safe reference shape | Primary rule |
|---|---|---|---|
| Power-on X | Un-reset mode register controlling output logic; testbench passes because simulation X-optimism resolves the branch deterministically | Reset covers the mode register | REF-XPROP-001 |
| Synchronizer depth | Two-stage synchronizer where the manifest declares three stages required | Three destination stages | REF-META-001 |

Both pairs must satisfy the controlled-witness contract: identical interface,
identical functional testbench, both members pass functional simulation, the
structural oracle separates them. The power-on X pair additionally documents
which simulator X-semantics the functional pass depends on (Icarus X handling
at the branch in question).

## What this adds to the research claims

- Extends the structural validity argument from timing-domain hazards
  (CDC/RDC) to value-domain hazards (X), demonstrating the gap is a property
  of the oracle class, not a quirk of clock-domain analysis.
- Both categories test whether the same evaluation contract applies beyond
  clock and reset crossings. They do not by themselves establish novelty or
  prevalence.
- Neither category changes the primary metric; both plug into the existing
  gap definition, report schema, and abstention semantics.

## Sequencing

1. `REF-XPROP-001` + power-on X witness pair (new fixtures, oracle rule,
   tests).
2. Power-on randomization adjudication for `REF-XPROP-001`: per-seed random
   initialization of un-reset state, reusing the golden-trace observer from
   [perturbation-adjudication.md](perturbation-adjudication.md). This gives
   the X category machine adjudication from day one.
3. `REF-META-001` + depth witness pair (rule reuses synchronizer recognition).
   Note: this rule is parametric permanently; depth adequacy is not
   injection-adjudicable (see the generalization section of the perturbation
   design).
4. X-prop generation taskpack (prompts requiring declared power-on behavior)
   - only after the rules are calibrated on witnesses, mirroring the
   reset-release sequence: witnesses first, audit second, generation third.
