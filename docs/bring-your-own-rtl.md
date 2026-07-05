# Bring your own RTL

This tutorial adds SV-Gap to an existing digital RTL evaluation without asking
SV-Gap to infer design intent or replace the functional oracle you already use.
On Ubuntu or Debian, install the open RTL tools and run `svgap doctor` first;
see [Linux install and doctor checks](linux-install-and-doctor.md).

## 1. Start from the evaluated source

Suppose `design.sv` contains a module named `top`. Create a draft beside it:

```bash
svgap init design.sv \
  --top top \
  --candidate-id my-first-candidate \
  --output manifest.toml
```

The draft is intentionally incomplete. A tool cannot safely infer whether two
clocks are asynchronous or whether reset deassertion must be synchronized.

## 2. Attach functional evidence

### Execute your existing test commands

Commands are arrays, not shell strings. This avoids hidden shell expansion.

```toml
[functional]
commands = [
  ["iverilog", "-g2012", "-o", "${SVGAP_BUILD}/sim.vvp", "design.sv", "tb.sv"],
  ["vvp", "${SVGAP_BUILD}/sim.vvp"],
]
```

`${SVGAP_BUILD}` is a candidate-local build directory created by SV-Gap.

### Or import an upstream result

If the benchmark already ran, normalize its result and bind it to the exact RTL
source digest. See [`examples/imported_result`](../examples/imported_result/)
and the [existing-benchmark integration recipe](integrating-existing-benchmarks.md).

## 3. Declare only known intent

For a single-clock design with an active-low asynchronous reset whose release
must be synchronized:

```toml
[structural]
backend = "reference-yosys"

[intent]
asynchronous_groups = []

[[intent.clocks]]
name = "core"
port = "clk"

[[intent.resets]]
name = "power_on_reset"
port = "arst_n"
active = "low"
assertion = "async"
deassertion = "sync"
```

For multiple asynchronous domains, declare groups explicitly:

```toml
[intent]
asynchronous_groups = [["source"], ["destination"]]

[[intent.clocks]]
name = "source"
port = "src_clk"

[[intent.clocks]]
name = "destination"
port = "dst_clk"
```

Do not add an asynchronous relationship merely to silence a finding. If the
relationship is unknown, leave it unresolved and preserve the `unknown` state.

## 4. Validate before executing

```bash
svgap validate manifest.toml
```

An incomplete result names missing evidence. It does not run the design or turn
missing information into a pass.

## 5. Evaluate and explain

```bash
svgap check manifest.toml
svgap explain build/report.json
```

The first command preserves functional and structural outcomes in one versioned
report. The second presents the handoff questions:

```text
ANSWERED
  - Did the supplied functional oracle accept the candidate? yes
FAILED
  - Does the candidate satisfy REF-RDC-001? no
UNANSWERED
  none
NEXT EVIDENCE
  - Review the finding, repair the candidate, run an independent backend,
    or attach an approved adjudication.
```

## 6. Export for CI or review

```bash
svgap export build/report.json \
  --sarif build/svgap.sarif \
  --html build/svgap.html
```

SARIF supports CI annotations. The static HTML report is dependency-free and
can be attached to a research artifact or design review.

## Interpreting the result

- `pass`: the configured backend completed without a configured failing finding.
- `fail`: the backend emitted an inspectable configured finding.
- `unknown`: required intent or supported analysis was insufficient.
- `tool_error`: execution did not complete.

A structural pass is bounded evidence, not silicon signoff. Keep the manifest,
source digest, tool versions, and raw findings with any downstream claim.
