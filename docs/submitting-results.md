# Submit a result

SV-Gap accepts immutable generation, diagnosis, and repair evidence profiles.
A submission is a content-addressed directory, not a leaderboard row. It keeps
functional failures, structural failures, unknowns, and tool errors visible.

## Choose a provenance level

| Level | Public record | Comparative use |
|---|---|---|
| `public` | Exact model identifier and optional provider | Eligible within the declared taskpack and evaluator scope |
| `attested_alias` | Stable public configuration label; named submitter retains the private mapping | Eligible, with the disclosure limitation shown on every profile |
| `anonymous_case_study` | Opaque label without an identity attestation | Visible as qualitative evidence; excluded from comparative interpretation |

SV-Gap never asks maintainers to take custody of a withheld checkpoint mapping.
For an attested alias, the submitting researcher or institution retains that
mapping and states what was preserved. The attestation does not independently
verify the hidden identity.

## Create the submission directory

After evaluating a generation study, create an immutable directory from its
`report.json` files:

```bash
svgap submission init reports/generated/my-study/*/*/report.json \
  --id lab-a-reset-v02-01 \
  --title "Lab A reset-release generation profile" \
  --track generation \
  --configuration-label lab-a-frontier-01 \
  --provenance-level attested_alias \
  --attestor "Researcher Name" \
  --attestation "Exact checkpoint and configuration retained privately." \
  --taskpack-id reset-replication \
  --taskpack-version 0.2 \
  --contributor "Researcher Name" \
  --output results/submissions/lab-a-reset-v02-01
```

For diagnosis or repair, pass one or more `result.json` files produced by
`svgap challenge score` or `svgap challenge run`, and set
`--track diagnosis` or `--track repair`. The result's track and public model
label must match the submission metadata. SV-Gap preserves per-check outcomes
instead of coercing them into generation statistics.

For public provenance, replace the alias attestation with
`--provenance-level public --model-id exact-model-id`. For an anonymous case
study, use `--provenance-level anonymous_case_study`; it will be marked
ineligible for comparative interpretation.

## Run the publication-safety gate

Create a private denylist outside the repository. Each non-comment line is a
case-insensitive regular expression for a withheld model identifier, internal
project name, endpoint, or other submission-specific string:

```text
# /private/path/svgap-publication-denylist.txt
internal-checkpoint-[0-9]+
secret-project-codename
```

Validate the evidence, deterministic track-specific summary, hashes,
provenance rules, and publication-safety scan:

```bash
svgap submission validate results/submissions/lab-a-reset-v02-01 \
  --denylist /private/path/svgap-publication-denylist.txt

svgap submission bundle results/submissions/lab-a-reset-v02-01 \
  --denylist /private/path/svgap-publication-denylist.txt \
  --output lab-a-reset-v02-01.tar.gz
```

The private denylist is read during validation and is never copied into the
submission or bundle. Built-in checks also reject credential-like strings,
user-home paths, and common internal endpoints.

## Open the contribution

Open a pull request containing only the new directory under
`results/submissions/`. CI validates the submission and checks the generated
public registry and static evidence profile. Accepted directories are immutable;
corrections use a new submission identifier and link to the superseded record.

Before opening the pull request, synchronize the checked-in registry and pages
with one command from a source checkout:

```bash
python scripts/sync_results.py
```

Commit the generated `results/registry-v1.json`, `docs/results.md`, and profile
page together with the submission. CI prints the same command if these files
are stale.

Acceptance confirms that the submitted artifacts satisfy the public contract,
hashes, configured checks, and project scope. It does not endorse the model,
verify a withheld identity, establish silicon safety, or imply paper authorship.

## Credit and citation

The submitting contributor is named on the generated evidence-profile page and
in the registry. Code and artifact contributions receive repository credit.
Authorship on a paper is a separate decision based on substantive intellectual
contribution, analysis, drafting, and accountability under the target venue's
authorship policy.
