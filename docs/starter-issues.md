# Starter issue drafts

## 1. Add a second open-source SystemVerilog frontend

Evaluate a maintained open-source frontend that accepts the function and enum
syntax currently rejected by Yosys/Icarus. Document its license, normalized
failure states, source-location behavior, and differential results on all
controlled fixtures. Do not silently convert frontend failures into passes.

## 2. Export normalized findings as SARIF and static HTML

Add deterministic SARIF output for CI annotations and a dependency-light static
HTML summary for research artifacts. Preserve `unknown` and `tool_error` as
first-class states and add golden-file tests.

## 3. Import blinded expert adjudication

Implement a command that validates completed review CSVs, joins them to a private
case mapping, reports pre-reconciliation inter-reviewer agreement, and lists all
oracle disagreements. Never expose model identity in reviewer-facing output.

## 4. Build reset taskpack v0.2

Resolve the timer output ambiguity in a new version rather than editing v0.1,
add executable safe/unsafe references for each task, and expand task diversity.
Preserve the v0.1 digest and report both original and sensitivity analyses.
