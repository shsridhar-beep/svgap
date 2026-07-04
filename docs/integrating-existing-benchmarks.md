# Integrating an existing functional benchmark

SV-Gap can preserve a benchmark's existing functional verdict instead of
rerunning its testbench. The imported result is bound to the exact candidate
source set by a canonical digest and is then carried into the layered SV-Gap
report.

## 1. Declare the candidate and production intent

Create a normal candidate manifest. Replace `functional.commands` with a
relative import:

```toml
[functional]
import = "functional-result.json"
```

Clock, reset, and crossing declarations describe the production property being
evaluated. They are not inferred from the imported verdict.

## 2. Bind the verdict to the candidate

Compute the digest after the candidate sources are final:

```bash
svgap digest path/to/manifest.toml
```

Create `functional-result.json` using
[`schemas/functional-result-v1.json`](../schemas/functional-result-v1.json):

```json
{
  "schema_version": "1.0",
  "status": "pass",
  "producer": "benchmark-name/revision",
  "candidate_digest": "sha256:...",
  "tool_versions": {"simulator": "version"},
  "evidence": {"tests_passed": 100, "tests_total": 100}
}
```

`producer` should identify the benchmark adapter and revision, not make an
unsupported claim about who generated the RTL. `evidence` may include a public
result URL, run identifier, formal proof digest, or normalized score fields.

## 3. Add the structural layer

```bash
svgap check path/to/manifest.toml
```

SV-Gap verifies the candidate digest before accepting the imported verdict. A
modified source file turns the functional layer into `tool_error` until the
upstream result is regenerated or explicitly rebound.

## 4. Export CI evidence

```bash
svgap export path/to/build/report.json \
  --sarif build/svgap.sarif \
  --html build/svgap.html
```

The working example under [`examples/imported_result`](../examples/imported_result)
uses this flow without executing a functional command.

## Adapter policy

An adapter should preserve the upstream result's semantics. It must not turn a
timeout, missing test, compilation failure, or unavailable result into `pass`.
When the upstream status cannot be mapped safely, use `unknown` or `tool_error`
and retain the original evidence.
