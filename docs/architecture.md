# Architecture

SV-Gap separates experiment orchestration from structural analysis.

```text
candidate manifest
  |-- RTL sources
  |-- functional commands or imported result
  |-- clock/reset/crossing intent
  `-- checker backend
          |
          v
 normalized EvaluationReport
  |-- functional status and evidence
  |-- structural status and findings
  |-- tool/backend versions
  `-- gap membership
```

## Manifest boundary

The manifest is the reproducibility boundary. Relative file paths resolve from
the manifest directory. Clock relationships are never inferred as asynchronous
merely because two clock names differ; the evaluator must declare asynchronous
groups explicitly.

## Backend boundary

A backend implements one operation:

```python
check(manifest) -> CheckResult
```

It must return one of `pass`, `fail`, `unknown`, or `tool_error`, stable rule
identifiers, evidence, and its own version. A backend must return `unknown` when
required intent is absent. It must not silently reinterpret tool failure as a
clean result.

## Built-in reference oracle

The reference oracle elaborates RTL to Yosys JSON and walks register/data
relationships. It is intentionally limited to controlled structural shapes:

- `REF-CDC-001`: asynchronous register crossing without a recognized second
  destination stage;
- `REF-CDC-002`: combinational logic immediately before a recognized
  synchronizer;
- `REF-CDC-003`: independently synchronized multi-bit crossing without a
  declared Gray-code protocol and a recognizable XOR-based source transform;
- `REF-RDC-001`: raw asynchronous reset on unmarked state when the manifest
  requires synchronous deassertion.
- `REF-XPROP-001`: un-reset state reaches a module output when the manifest
  declares that operational state requires reset coverage at power-on.

These rules demonstrate the evaluation contract. They are not a signoff rule
deck. External backends may provide much broader coverage without changing the
manifest/report concepts.
