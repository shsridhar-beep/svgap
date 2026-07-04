# Pilot research protocol

## Question

Can a conventional functional RTL oracle assign the same successful outcome to
implementations that differ on declared production-relevant structural rules?

This is an existential construct-validity question. It does not require a
population defect-rate estimate. The full claim hierarchy is frozen in
[`research-scope-v0.2.md`](research-scope-v0.2.md).

## Controlled witnesses

The first release contains four paired witnesses. Each pair shares a module
interface and functional testbench:

| Family | Unsafe shape | Safe reference shape | Primary rule |
|---|---|---|---|
| Stable level | Direct async sampling | Two destination stages | REF-CDC-001 |
| Derived control | Combinational logic before sync | Registered source then two stages | REF-CDC-002 |
| Counter bus | Independent binary-bit synchronization | Registered Gray code and decode | REF-CDC-003 |
| Reset release | Raw async deassertion at state | Async assert, sync deassert | REF-RDC-001 |

Passing these witnesses demonstrates oracle non-identifiability under the
supplied simulations. It does not estimate the prevalence of defects in model
outputs. That estimate requires a preregistered task set, multiple model
families and samples, and task-clustered uncertainty intervals.

## Incremental expansion

1. Preserve the controlled witnesses as the primary existence proof.
2. Audit public task metadata for whether the production question is
   representable and scorable.
3. Use reset-release generation as a worked application of the contract,
   reporting calls, tasks, duplicate outputs, and inconclusive states without a
   population interpretation.
4. Freeze reset taskpack v0.2 with corrected intent and executable references
   before any new generation.
5. Accept author review, synthetic review, expert review, competing backends,
   and executable perturbations as separately identified evidence layers. No
   one optional layer gates publication of the existential result.

## Exploratory pilot completed

Before the planned powered study, pilot v0.1 froze six prompts and ran one sample
from each of three model configurations. The result and its deliberately narrow
interpretation are documented in [pilot-result.md](pilot-result.md). The pilot
identified reset release as the first replication target and exposed Yosys
frontend coverage as an explicit measurement-system limitation.
