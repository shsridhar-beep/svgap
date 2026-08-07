# Contributing

SV-Gap is aimed at applied AI researchers, RTL engineers, and verification
engineers moving generated hardware from demonstrations toward products.

You do not need to start with code. If you have one public, non-confidential
question about why a functional RTL result is insufficient for a production
handoff, use the
[collaboration intake](https://github.com/shsridhar-beep/svgap/issues/new?template=collaboration.yml).
The maintainer will map it to the smallest useful experiment or explain which
capability is missing before you invest in a pull request.
If GitHub sign-in is a blocker, use the maintainer email in
[SUPPORT.md](SUPPORT.md); do not send confidential material.

## AI-assisted contributions

AI-assisted contributions are welcome. The submitting contributor must review
the change, disclose substantial automation, verify tests and licensing, and
take responsibility for the result. Unreviewed bulk-generated submissions,
fabricated evidence, and contributions containing confidential material may be
closed.

The accountable submitting person should remain the Git commit author. Record
material AI assistance in the pull request and contributor disclosure rather
than presenting a tool identity as an independently accountable researcher.

Contribution method is not a substitute for technical review. The same
evidence, reproducibility, scope, and claim-boundary requirements apply to
human-written and AI-assisted changes.

## Response and credit

The maintainer aims to acknowledge scoped research proposals, result
submissions, and reproducible oracle disputes within two working days. If a
decision needs more evidence, the thread should name the missing evidence and
next decision point.

Accepted code and artifact contributions receive repository credit and retain
their recorded authorship. Paper authorship is a separate decision based on
substantive intellectual contribution, analysis, drafting, and accountability
under the target venue's policy; opening a pull request does not by itself
promise co-authorship.

Repository credit identifies the account recorded in the accepted commit
history; it is not a claim that the project independently verified the account
holder's legal identity, affiliation, or human-versus-automated operating mode.
Material AI assistance is disclosed separately in
[CONTRIBUTORS.md](CONTRIBUTORS.md).

Good first contributions include:

- a paired safe/unsafe fixture for an existing rule;
- a task manifest with explicit clock/reset intent;
- an adapter for a publicly accessible checker;
- a benchmark-result normalizer;
- a reproduced model run with immutable generation metadata;
- an expert adjudication that explains a false positive or false negative.

The project is backend- and evidence-neutral: a contribution may challenge the
reference oracle. See [GOVERNANCE.md](GOVERNANCE.md), the
[backend SDK](docs/backend-sdk.md), the
[existing-benchmark recipe](docs/integrating-existing-benchmarks.md), and
[disputed-finding fixtures](docs/disputed-finding-fixtures.md) for how to
file a reproducible disagreement.

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

## Docker Development Environment Setup

You can use this setup compared to above if you do not want to modify your host system.

The container will have all tools and software such as Yosys, IVerilog etc ready for dev and testing.

`make dev-up`, `make dev-shell`, and `make dev-test` wrap the steps below into
one command each: bring the container up, open a shell inside it, or install
the editable venv and run the test suite non-interactively.

```bash
docker compose up -d

#Get into the container. This would take you into the /workspace directory where you'll see the contents
#of the repo from host.
docker compose exec svgap-dev bash

#If you type in `which svgap` you'd find it in the system installation dir (/sr/local/bin/svgap)which
#points to the src during container build at /opt/svgap. We do not want to modify this for dev and testing.
#So do the following from within the container from the /workspace dir for a first time/fresh repo download
#you can use any name for the env, but make sure it is inside .venv so that it is gitignored.
python -m venv .venv

#Activate the venv(from within container)
source .venv/bin/activate

# Install dependencies for dev and keep it editable so you can test your changes. (from within container)
python -m pip install -e ".[dev]"

# Now you can use the svgap command witin container and run tests as normal.
svgap doctor
svgap demo
which svgap #should return the path that is within the activated virtual env
.venv/bin/python -m unittest discover -s tests -v
```

## Evaluation changes

Every new rule or backend must document its evidence, limitations, version, and
failure behavior. Inconclusive analysis must return `unknown`, never `pass`.

Please do not contribute proprietary RTL, confidential constraints, model
credentials, or artifacts whose redistribution terms are unclear.

Taskpacks and backends must stay within the project's
[digital RTL scope boundary](docs/scope-boundary.md). Analog and mixed-signal
design or verification contributions are out of scope.
