# Checker backend SDK

SV-Gap separates the evaluation contract from any one structural checker.
Built-in and third-party backends implement one operation:

```python
check(manifest: Manifest) -> CheckResult
```

## Contract

A backend must expose stable `name` and `version` strings and return:

- `pass` when it completed and emitted no configured failing finding;
- `fail` with one or more inspectable findings;
- `unknown` when required intent or analyzer coverage is insufficient; or
- `tool_error` when execution could not complete.

It must never translate missing intent, unsupported syntax, timeout, or tool
failure into `pass`. Findings use stable rule identifiers, severity, a concise
message, and JSON-serializable evidence. Tool and rule-deck versions belong in
the result.

## Registration

Register a zero-argument backend factory using the `svgap.backends` Python entry
point group:

```toml
[project.entry-points."svgap.backends"]
my-open-checker = "my_svgap_backend:MyBackend"
```

```python
from svgap.model import CheckResult, Manifest

class MyBackend:
    name = "my-open-checker"
    version = "1.0"

    def check(self, manifest: Manifest) -> CheckResult:
        ...
```

After installation, `svgap doctor` lists the backend. Select it in a manifest:

```toml
[structural]
backend = "my-open-checker"
```

Plugins cannot replace a built-in name. The plugin package must document its
tool license, installation requirements, source-location behavior, supported
intent, rule identifiers, timeout behavior, and known false-positive and
false-negative classes.

## Acceptance tests

Every backend contribution should include:

1. a capability probe;
2. at least one passing and failing fixture per rule;
3. missing-intent and unsupported-syntax tests;
4. normalized `unknown` and `tool_error` cases;
5. report-schema validation; and
6. a differential table against the reference backend where scopes overlap.

Commercial-tool adapters may live outside this Apache-2.0 repository. The core
project and its default CI assume only redistributable open-source tools.
