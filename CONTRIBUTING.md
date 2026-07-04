# Contributing

SV-Gap is aimed at applied AI researchers, RTL engineers, and verification
engineers moving generated hardware from demonstrations toward products.

Good first contributions include:

- a paired safe/unsafe fixture for an existing rule;
- a task manifest with explicit clock/reset intent;
- an adapter for a publicly accessible checker;
- a benchmark-result normalizer;
- a reproduced model run with immutable generation metadata;
- an expert adjudication that explains a false positive or false negative.

The project is backend- and evidence-neutral: a contribution may challenge the
reference oracle. See [GOVERNANCE.md](GOVERNANCE.md), the
[backend SDK](docs/backend-sdk.md), and the
[existing-benchmark recipe](docs/integrating-existing-benchmarks.md).

## Development setup

Install Python 3.11+, Yosys, and Icarus Verilog, then:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m svgap doctor
.venv/bin/python -m unittest discover -s tests -v
```

Pull requests run the same suite on GitHub Actions. Keep generated reports,
provider transcripts, blinded mappings, and credentials out of commits; the
repository `.gitignore` excludes the standard local locations.

## Evaluation changes

Every new rule or backend must document its evidence, limitations, version, and
failure behavior. Inconclusive analysis must return `unknown`, never `pass`.

Please do not contribute proprietary RTL, confidential constraints, model
credentials, or artifacts whose redistribution terms are unclear.

Taskpacks and backends must stay within the project's
[digital RTL scope boundary](docs/scope-boundary.md). Analog and mixed-signal
design or verification contributions are out of scope.
