# Ordinary RTL lint baseline on the 14 reset-gap candidates

Run date: 2026-08-06

## Result

Neither ordinary open-source linter identified the frozen RDC mechanism in any
of the 14 functionally passing `REF-RDC-001` candidates:

| Tool | RDC-specific detection in 14 gaps | Any diagnostic | Non-filename diagnostic |
|---|---:|---:|---:|
| Verilator 5.050, `--lint-only --Wall` | 0 / 14 | 14 / 14 | 0 / 14 |
| Verible v0.0-4121-gc2ec3416, default rules | 0 / 14 | 14 / 14 | 3 / 14 |
| Union | **0 / 14** | 14 / 14 | 3 / 14 |

All 14 candidates parsed successfully in both tools. The apparently universal
diagnostic rate is entirely explained by both linters objecting that the shared
artifact filename `design.sv` does not match each task-specific module name.
That packaging convention is unrelated to reset behavior.

Verible additionally reported `undersized-binary-literal` on three
`openai-frontier-a` `reset_counter` candidates. Each uses `8'b1` instead of an
eight-digit, zero-padded literal. This is a style finding, not detection of raw
asynchronous reset reaching ordinary state.

## Comparator result

The same commands were run on the other 43 candidates that passed both the
functional oracle and the frozen structural oracle:

| Tool | RDC-specific detection | Any diagnostic | Non-filename diagnostic |
|---|---:|---:|---:|
| Verilator | 0 / 43 | 43 / 43 | 15 / 43 |
| Verible | 0 / 43 | 43 / 43 | 0 / 43 |

Verilator emitted `SYNCASYNCNET` on 15 structural-pass comparators and zero gap
members. Manual inspection confirmed that these warnings target
`reset_sync`/`rst_sync`: the synchronizer state is clocked synchronously and its
released output is used in an asynchronous-reset context. The warning therefore
points at the recognized synchronized-reset implementation, not at the unsafe
raw-reset bypass that defines `REF-RDC-001`. It must not be counted as detection
of the gap merely because its name contains “async” and “sync.”

The comparator is descriptive. A frozen structural pass is not an independently
established clean-design label, and the 57 functional passes are not a
representative population sample.

## Method

The protocol was written locally before inspecting candidate lint output. The
primary population was selected mechanically from the frozen artifact as
`functional == pass && structural == fail`; the runner verified all 14 reports
carry `gap_member: true` and the error rule `REF-RDC-001`. The remaining 43
functional passes served as structural-pass comparators.

Only manifest-declared design sources were linted. Testbenches, waivers, project
configuration, and candidate-specific options were excluded. Commands were:

```text
verilator --lint-only --Wall --Wno-fatal --top-module <top> <design sources>
verible-verilog-lint --ruleset=default <design sources>
```

“Detected” required a diagnostic that actually identified a reset-domain
crossing, unsafe asynchronous-reset release/deassertion, raw-reset reachability,
or synchronizer bypass. Syntax, filename, literal-style, and generic
synchronous/asynchronous-use warnings did not qualify. Every unique diagnostic
class was manually checked under that rubric.

## Reproduction and evidence

- Frozen protocol: [`reports/rdc-lint-baseline-v0.1/protocol.md`](https://github.com/shsridhar-beep/svgap/blob/main/reports/rdc-lint-baseline-v0.1/protocol.md)
- Machine-readable records and summaries: [`reports/rdc-lint-baseline-v0.1/results.json`](https://github.com/shsridhar-beep/svgap/blob/main/reports/rdc-lint-baseline-v0.1/results.json)
- Manual diagnostic classification: [`reports/rdc-lint-baseline-v0.1/manual-review.json`](https://github.com/shsridhar-beep/svgap/blob/main/reports/rdc-lint-baseline-v0.1/manual-review.json)
- Raw stdout/stderr: [`reports/rdc-lint-baseline-v0.1/raw/`](https://github.com/shsridhar-beep/svgap/tree/main/reports/rdc-lint-baseline-v0.1/raw)
- Runner: [`scripts/run_rdc_lint_baseline.py`](https://github.com/shsridhar-beep/svgap/blob/main/scripts/run_rdc_lint_baseline.py)

The exact tool versions, executable hashes, candidate source hashes, commands,
return codes, and raw-output paths are recorded in `results.json`.

## Defensible claim

> Under default Verilator 5.050 and Verible v0.0-4121-gc2ec3416 lint
> configurations, neither tool emitted an RDC-specific diagnostic for any of
> the 14 functionally passing candidates detected by SVGAP's frozen
> `REF-RDC-001` oracle.

This shows that the configured SVGAP reset-intent check contributes orthogonal
coverage relative to these two ordinary open-source lint baselines on this
taskpack. It does **not** establish that all lint tools miss the condition.
Commercial lint decks and dedicated CDC/RDC signoff tools are outside this
study, as are tuned rule configurations and other reset task families.

## How the result is represented in SV-Gap

Schema v2 can now run `lint-verilator` or `lint-verible` as an explicit
`oracle_class = "lint"`. The backend coverage metadata records this frozen
0/14 calibration boundary. Lint diagnostics stay tool-attributed
(`LINT-VERILATOR-*` or `LINT-VERIBLE-*`) and do not become `REF-RDC-*`
findings. The recommended profile sets `contributes_to_gap = false`, retaining
the lint result beside structural evidence without allowing it to redefine the
structural-gap metric.
