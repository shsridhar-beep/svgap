# Pilot research protocol

## Question

Can a conventional functional RTL oracle assign the same successful outcome to
implementations that differ on declared production-relevant structural rules?

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

## Planned expansion

1. Audit public task metadata for structural identifiability.
2. Freeze 16 independently reviewed CDC/RDC generation tasks.
3. Generate five samples from each of four model families.
4. Preserve prompts, model versions, sampling parameters, raw RTL, logs, and
   checker versions.
5. Expert-adjudicate primary findings and report unknown/tool-error rates.

## Exploratory pilot completed

Before the planned powered study, pilot v0.1 froze six prompts and ran one sample
from each of three model configurations. The result and its deliberately narrow
interpretation are documented in [pilot-result.md](pilot-result.md). The pilot
identified reset release as the first replication target and exposed Yosys
frontend coverage as an explicit measurement-system limitation.
