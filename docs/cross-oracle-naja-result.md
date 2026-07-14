# Cross-oracle check: najaeda structural backend vs. reference-yosys

Run date: 2026-07-14

## Design

`reference-naja` is a second structural backend (see
[docs/backend-sdk.md](backend-sdk.md) and
[docs/reference-naja-backend.md](reference-naja-backend.md)) that reproduces the
`reference-yosys` CDC/RDC rule set on a different toolchain: najaeda's bundled
slang frontend and SNL netlist, with no Yosys or Icarus binary. It implements
REF-CDC-001/002/003 and REF-RDC-001. It does **not** implement REF-XPROP-001
(power-on X), which is out of scope for this comparison.

To test agreement where the two scopes overlap, we ran `reference-naja` fresh
against every candidate in the frozen 72-candidate artifact at
`artifacts/reset-replication-v0.1/`. The reference-yosys structural verdict for
each candidate is already recorded in that artifact (`report.json`'s
`structural` block and the top-level `manifest.json` index), so no Yosys or
Icarus run is needed: this is a comparison against a frozen oracle, not a
re-evaluation. Each candidate's `manifest.toml` names `reference-yosys` as its
backend; the harness bypasses that field and calls `ReferenceNajaBackend`
directly. The check is committed as
`tests/test_reference_naja.py::ReferenceNajaCrossOracleTests`.

The 72 candidates come from eight reset-sensitive tasks, three model
configurations, and three samples per cell. They are a reset-release taskpack,
so the only rule any candidate can trigger is REF-RDC-001; the CDC rules are
exercised by the controlled witness pairs in `tests/test_reference_naja.py`, not
here.

## Result

| Comparison | Count |
|---|---:|
| Candidates | 72 |
| Status agreement | 72 / 72 (100.0%) |
| Rule-set agreement | 72 / 72 (100.0%) |
| Disagreement | 0 / 72 |

Status agreement and rule-set agreement are identical: on every candidate the
two oracles emit exactly the same rule set (empty on the 57 mutual passes,
`{REF-RDC-001}` on the 15 mutual fails). There is no candidate where the two
agree on `pass`/`fail` but disagree on which rule fired.

| yosys → naja | Count | Interpretation |
|---|---:|---|
| pass → pass | 57 | agree (no finding) |
| fail → fail | 15 | agree (REF-RDC-001) |
| pass → fail | 0 | — |
| fail → pass | 0 | — |

**History (kept honest).** Before the wide-vector reset-synchronizer fallback
was ported into `_reset_synchronizer_regs`, this comparison stood at **54 / 72
(75.0%)**, with 18 `pass(yosys) → fail(naja)` disagreements — all one
false-positive class, described below. Porting the fallback resolved all 18 and
regressed none of the 54 that already agreed, giving the 72 / 72 above. The 15
mutual REF-RDC-001 fails and 39 of the mutual passes are unchanged; the 18
formerly-disagreeing candidates moved from `fail(naja)` to `pass(naja)`,
lifting the mutual-pass count from 39 to 57.

## Resolved: the wide-vector reset-synchronizer class

The 18 former disagreements were a single false-positive class, and one the
backend already anticipated. Earlier, the `ReferenceNajaBackend` class docstring
and `_reset_synchronizer_regs` noted that the Yosys reference has an extra "one
wide vector-shift `$adff` cell" reset-synchronizer fallback that was
deliberately **not ported**, on the assumption that "naja lowers explicit
multi-flop reset synchronizers as separate scalar instances in every fixture
observed."

That assumption held for svgap's own example fixtures but not for these
generated candidates. The `openai-frontier-a` candidates write the
reset synchronizer as a single packed vector:

```systemverilog
logic [1:0] reset_sync;
always_ff @(posedge clk or negedge global_reset_n) begin
    if (!global_reset_n) reset_sync <= 2'b00;
    else                 reset_sync <= {reset_sync[0], 1'b1};
end
// downstream registers reset on reset_sync[1]
```

naja lowers `reset_sync` as one 2-bit sequential instance (`..._dffrn__w2`), not
two scalar flops. The original `_reset_synchronizer_regs` required a single-bit
first *and* second stage (`len(q_nets) == 1`), so it never recognized this
one-instance synchronizer, and the synchronizer's own register was then flagged
by REF-RDC-001 as an unmarked async-reset consumer. The `claude-*` candidates
write the same synchronizer as two named scalar flops, which naja lowers as two
scalar instances that the recognizer already accepted — hence the clean model
split.

This was confirmed structurally: for `openai-frontier-a--sample-01/reset_config`
the flagged cell was the 2-bit `reset_sync` register itself, and the downstream
`config_out` register (which resets on the synchronized `reset_sync[1]`, an
internal net rather than a declared reset port) was correctly not flagged. The
design is a textbook async-assert / sync-deassert reset synchronizer;
reference-yosys is right to pass it and reference-naja's earlier fail was a false
positive.

**The fallback is now ported.** `_reset_synchronizer_regs` recognizes the wide
single-instance form directly, reproducing the Yosys structural test
(`d_bits[0] == inactive constant` and `d_bits[1:] == q_bits[:-1]`): a single
multi-bit sequential instance under one shared async reset, whose bit-0 D loads
the reset's inactive constant and whose every higher bit D is the previous bit's
Q. Because naja routes each of those D bits through a transparent `assign` alias
(where Yosys has no such cell), the D nets are resolved through the `assign` glue
before the constant/shift test — reproducing Yosys's resolved-bit view. The match
is deliberately narrow: an ordinary wide async-reset *data* register (whose D
bits resolve to external data, not to the inactive constant or prior Q bits)
fails both the constant-at-bit-0 and the shift-chain checks and is still flagged,
so the recognizer does not wave through any packed register that merely carries
an async reset. This over-acceptance guard is covered by
`ReferenceNajaWideVectorResetTests` in `tests/test_reference_naja.py`.

## Frontend-coverage note: SystemVerilog function `return`

The pilot ([docs/pilot-result.md](pilot-result.md)) recorded two functionally
passing Gray-counter candidates that Yosys 0.66 rejected because they used a
SystemVerilog function with an explicit `return` statement — a construct Yosys's
native Verilog frontend does not parse. Those raw candidates are not in this
checkout (`reports/generated/` is gitignored), so we reproduced the construct in
a minimal isolated snippet: an `automatic` gray-to-binary helper with an
explicit `return`, matching the Gray-counter task's shape.

- **Yosys** (0.67+post here; same frontend limitation as 0.66) rejects it:
  `ERROR: syntax error, unexpected TOK_ID` on the `return` line.
- **najaeda / slang** accepts it, elaborating a top design with the expected
  instances.

This is a positive result: najaeda's slang frontend covers at least this class
of candidate that the Yosys reference reports as `tool_error`. It does not
change any verdict in the table above (none of the 72 frozen candidates use the
construct), but it means the two pilot Gray-counter `tool_error` cases would
plausibly have elaborated under `reference-naja`. The snippet is not committed;
it is reproducible from the description above.

## Defensible claim

> On the frozen 72-candidate reset-replication artifact, the najaeda structural
> backend reproduces the reference-yosys verdict on all 72 candidates
> (rule-for-rule). The one former false-positive class — a packed-vector reset
> synchronizer that naja lowers as a single multi-bit register — is now
> recognized by the ported wide vector-shift fallback, closing the last
> disagreement; before the port the figure was 54/72.

This is a scope-overlap agreement measurement on one frozen taskpack. It is not
a claim that the two backends are interchangeable in general, that 100% is their
asymptotic agreement, or that reference-naja is signoff-grade. It does establish
that on this taskpack they agree exactly, and that the modeling difference that
had separated them is understood down to the netlist and resolved rather than
merely characterized.

## Threats to validity

- One taskpack, all reset-release: the CDC rules (REF-CDC-001/002/003) are not
  exercised by this artifact and are covered only by the controlled witness
  pairs, which are far smaller than 72 candidates.
- The frozen `structural` field is treated as ground truth. It is the
  reference-yosys verdict, itself a narrow structural oracle, not silicon
  signoff; agreement with it is agreement with a reference tool, not with
  physical reality.
- The 72/72 agreement is measured after porting the wide vector-shift fallback,
  which was validated against exactly the packed-vector coding style present in
  this taskpack (all `openai-frontier-a`). A synchronizer written in some third
  style neither taskpack sample exercises — a wider chain, a different injection
  bit, or a non-shift topology — could still fall outside both the scalar and
  the wide recognizer; the recognizer matches the specific Yosys structural test,
  not every conceivable synchronizer. Agreement on this taskpack is exact, but
  it remains conditional on the two coding styles it actually contains.
- The `return`-syntax result uses a reconstructed snippet, not the original
  pilot candidates, which are not in this checkout.
