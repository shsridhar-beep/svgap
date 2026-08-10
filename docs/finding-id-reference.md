# Finding ID reference

Every reference-backend result carries findings identified by a stable
`rule_id` such as `REF-CDC-001`. This page is the single lookup table for
what each current finding ID detects, its severity, and which backend(s)
emit it.

| Finding ID | Detects | Severity | Backends | Defined in |
|---|---|---|---|---|
| `REF-CDC-001` | Asynchronous register crossing sampled without a recognized second synchronizer stage | `error` | reference-yosys, reference-naja | [Architecture](architecture.md#built-in-reference-oracle) |
| `REF-CDC-002` | Combinational logic between the source register and the synchronizer | `error` | reference-yosys, reference-naja | [Architecture](architecture.md#built-in-reference-oracle) |
| `REF-CDC-003` | Multi-bit asynchronous crossing using independent synchronizer stages without a declared coherence protocol | `error` | reference-yosys, reference-naja | [Architecture](architecture.md#built-in-reference-oracle) |
| `REF-RDC-001` | Raw asynchronous reset reaching an unmarked state element that requires synchronous deassertion | `error` | reference-yosys, reference-naja | [Architecture](architecture.md#built-in-reference-oracle) |
| `REF-XPROP-001` | Un-reset operational state reaches a module output although the manifest declares power-on reset coverage | `error` | reference-yosys, reference-naja | [Reference naja backend](reference-naja-backend.md#supported-rules), [Category expansion: X-optimism and metastability](category-expansion-xprop-metastability.md#ref-xprop-001-un-reset-operational-state) |
| `REF-NAJA-FRONTEND-001` | najaeda frontend diagnostic (e.g. `case_comparison_two_state`) surfaced as a finding instead of dropped | `warning` | reference-naja only | [Reference naja backend](reference-naja-backend.md#frontend-warnings-and-working-directory-hygiene) |

Warning-severity findings never change a check's `pass`/`fail` verdict; only
`error`-severity findings do (see [Evidence policy](methodology.md#evidence-policy)).

`REF-META-001` and `REF-XPROP-002` are proposed rules described in
[Category expansion: X-optimism and metastability](category-expansion-xprop-metastability.md#new-rules).
They are design-stage only — no backend in this repository emits them yet —
so they are not listed above.
