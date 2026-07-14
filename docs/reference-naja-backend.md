# `reference-naja` structural backend

`reference-naja` is a second built-in structural checker that reproduces the
`reference-yosys` CDC/RDC oracle on a different toolchain. It is registered under
the `svgap.backends` entry point as `reference-naja` and selected in a manifest
with:

```toml
[structural]
backend = "reference-naja"
```

This page documents what [docs/backend-sdk.md](backend-sdk.md) requires of any
contributed backend: license, install requirements, source-location behavior,
supported rules, timeout behavior, and known false-positive / false-negative
classes.

## License

The backend depends on **najaeda** (the Python distribution of the
[Naja](https://github.com/najaeda/naja) SNL/EDA project), which is
**Apache-2.0**. This is compatible with SV-Gap's own Apache-2.0 license. najaeda
is listed in [THIRD_PARTY.md](../THIRD_PARTY.md).

## Install requirements

This is the practical differentiator from `reference-yosys`. `reference-naja`
needs **no external binary**: najaeda is a pure `pip install` dependency
(floored at `najaeda>=0.7.13` in `pyproject.toml`) and bundles its own slang
SystemVerilog frontend and SNL netlist engine. There is no Yosys and no Icarus
Verilog in this backend's path.

- `reference-yosys` shells out to the `yosys` executable and, for functional
  checks, `iverilog`/`vvp`; those are external system packages.
- `reference-naja` runs entirely in-process against `from najaeda import naja`.

Installing SV-Gap installs najaeda, so `svgap doctor` lists `reference-naja`
with no further setup. (Functional simulation is unaffected and still uses
Icarus; this backend only replaces the *structural* oracle.)

The version floor is `0.7.13` specifically because the backend uses
`SNLDesign.isMux()`, added in that release, instead of an earlier
`naja_mux*` name-prefix heuristic.

## Source-location behavior

Findings carry a `source_location` in `file:line` form derived from najaeda's
SNL source-location metadata (slang's diagnostics-engine convention), when
available. najaeda records the path relative to the *calling process's* current
working directory, unlike Yosys's always-absolute `src` attribute. The backend
normalizes this to an absolute path and then strips the manifest directory
prefix, so the emitted location is relative to the manifest directory and
independent of the caller's cwd (matching the candidate-relative locations the
rest of SV-Gap emits). If najaeda has no source location for an instance, the
field is an empty string rather than a fabricated location.

## Supported rules

| Rule | Covered |
|---|---|
| REF-CDC-001 (async crossing without recognized second stage) | yes |
| REF-CDC-002 (combinational logic before synchronizer) | yes |
| REF-CDC-003 (multi-bit crossing without coherence protocol) | yes |
| REF-RDC-001 (raw async reset into a sync-deassertion element) | yes |
| REF-XPROP-001 (power-on X) | **no — not implemented** |

REF-XPROP-001 is explicitly out of scope for `reference-naja`. A manifest that
depends on power-on X analysis should use `reference-yosys`. The backend does
not silently pass power-on intent; it simply does not model that rule, and the
`power_on_x` witness family is therefore excluded from its test matrix.

Missing or insufficient intent is reported as `unknown` (never `pass`), and an
elaboration or analysis failure is reported as `tool_error` (never `pass`),
matching the SDK contract.

## Timeout behavior

**Known gap: the backend has no timeout.** `check()` calls
`db.loadSystemVerilog(...)` (slang elaboration) and the in-process netlist
analysis synchronously, with no wall-clock bound. A pathological or extremely
large source could therefore run unbounded. In practice the flat, single-module
CDC/RDC fixtures elaborate in milliseconds, but callers that run untrusted or
unbounded input should impose their own external timeout. `reference-yosys` has
the same characteristic (it does not time-bound the `yosys` subprocess either),
so this is not a regression relative to the built-in backend, but it is a real
limitation to close before running this backend on adversarial input.

## Known false-positive and false-negative classes

These are surfaced from the `ReferenceNajaBackend` class docstring and its
`_reset_synchronizer_regs` note so they live in the documentation, not only in
code comments.

- **Wide-vector reset synchronizer — resolved (was a measured false positive).**
  naja lowers a packed-vector reset synchronizer (`logic [1:0] reset_sync; ...`)
  as a single multi-bit sequential instance. `_reset_synchronizer_regs` now
  recognizes this wide single-instance form — a bit-0 inactive-constant load
  followed by a strict per-bit shift chain under one shared async reset, with
  each D bit resolved through its `assign` alias first — at parity with Yosys's
  "wide vector-shift `$adff` cell" fallback. Before this fallback was ported the
  wide form was flagged under REF-RDC-001 and was the single disagreement class
  in the [cross-oracle comparison](cross-oracle-naja-result.md): 18 of 72 frozen
  candidates, all one model configuration's coding style. With the fallback
  ported that comparison is 72/72 (it was 54/72). The match is deliberately
  narrow: an ordinary wide async-reset *data* register (whose D bits are external
  data, not a shift-to-constant chain) is still flagged. Designs that write the
  synchronizer as named scalar flops are recognized by the scalar path, as before.

- **Synchronous-reset polarity NOT gate — benign.** `if (!rst_n)` lowers, via
  slang, to an explicit NOT gate feeding a mux select, where Yosys's `proc` pass
  folds the polarity into the mux inputs with no NOT cell. This never changes a
  finding: the polarity NOT's fanin dead-ends at the reset port (no sequential
  driver), so it contributes no combinational-path entry under the
  trace-only-successful-branches walk.

- **Continuous net alias (`assign`) transparency.** `wire x = y;` lowers to an
  explicit `assign` leaf instance in naja (Yosys has no equivalent cell). The
  backend treats `assign` as transparent glue in both the backward and forward
  walks (crossed but never recorded), matching Yosys's hazard semantics, since
  it carries no real logic. A divergence here would be a false
  negative/positive; none has been observed, but it is a modeling assumption
  worth stating.

- **XOR vs. generic N-ary gate truth-table ambiguity.**
  `SNLDesign.getTruthTable()` cannot distinguish XOR/AND/OR/NAND/NOR/XNOR for
  naja's *generic* N-ary gate family (they share a `GenericType` tag rather than
  an explicit bit mask). The backend uses `SNLDesign.isXor()` for the Gray/XOR
  coherence check (REF-CDC-003) instead of a truth-table match. If a future naja
  release changed how that family is tagged, the Gray-protocol waiver logic
  would need re-validation.

## Tests

- `tests/test_reference_naja.py` — the four controlled safe/unsafe witness pairs
  and their rule IDs, the gray-declaration and wildcard-gray cases,
  missing-intent (`unknown`), unparseable/missing source (`tool_error`),
  report-schema validation, and the cross-oracle differential against the frozen
  72-candidate artifact.
- `tests/test_backends.py` — the capability probe (registry discovery and
  `load_backend`).
