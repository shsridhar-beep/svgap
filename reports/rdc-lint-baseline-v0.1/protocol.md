# RDC lint baseline v0.1 protocol

Frozen: 2026-08-06, before running either linter on any study candidate.

## Question

Do ordinary open-source RTL lint tools identify the reset-domain-crossing
condition in any of the 14 candidates that passed the frozen functional oracle
and failed `REF-RDC-001` in `reset-replication-v0.1`?

## Population and comparator

The primary population is selected mechanically from
`artifacts/reset-replication-v0.1/manifest.json`:

```text
functional == "pass" and structural == "fail"
```

This yields the frozen 14 gap members. The runner verifies that each selected
candidate's `report.json` has `gap_member: true` and an error-severity
`REF-RDC-001` finding.

As a secondary comparator, the same commands are run on the other 43 candidates
with `functional == "pass" and structural == "pass"`. The comparator is used
only to contextualize generic diagnostic prevalence; it does not turn the
frozen corpus into a representative population sample.

## Tools and commands

The design sources declared by each candidate's `manifest.toml` are linted.
Testbenches are excluded. No project lint configuration, suppression file, or
waiver is applied.

Verilator semantic/style lint baseline:

```text
verilator --lint-only --Wall --Wno-fatal --top-module <top> <design sources>
```

Verible style/syntax lint baseline:

```text
verible-verilog-lint --ruleset=default <design sources>
```

Tool versions are captured at execution time. The intended frozen versions are
Verilator 5.050 and Verible v0.0-4121-gc2ec3416.

## Endpoints

### Primary endpoint: RDC-specific detection

A tool detects the frozen condition only if a diagnostic itself identifies at
least one of the following:

- a reset-domain crossing;
- unsafe asynchronous-reset release or deassertion;
- a raw asynchronous reset reaching ordinary state despite a synchronous
  deassertion requirement;
- bypass of a reset synchronizer; or
- an equivalent reset-synchronization defect.

Diagnostics are classified from their primary message lines, not source-context
snippets. A syntax error, style finding, unused signal, width warning, generic
async/sync signal warning, or any other unrelated diagnostic is **not** an
RDC-specific detection.

The automated classifier uses deliberately narrow reset/RDC phrases. Every
unique diagnostic class and every automated positive must be manually reviewed
against this definition before reporting the final endpoint.

### Secondary endpoints

- candidates with any diagnostic;
- total diagnostic count and diagnostic classes per tool;
- diagnostic prevalence in the 14 gap members versus the 43 structural-pass
  comparators; and
- lint parse/elaboration failures.

These secondary endpoints measure ordinary lint noisiness and possible
discrimination. They are not substitutes for the primary endpoint.

## Interpretation boundary

This is a two-tool, default-configuration open-source baseline on one frozen
reset taskpack. A null result does not establish that all linters, commercial
lint decks, or dedicated CDC/RDC tools miss these cases. A positive generic
warning does not establish detection of the RDC mechanism.

