# Run resumable generation and repair campaigns

Campaigns turn one-shot evidence into a controlled experiment: expand a task
matrix, preserve every prompt and response, stop on a real budget, repair with
structured evaluator feedback, resume after interruption, and replay an exact
saved response without another model call.

Start from [`examples/campaign.toml`](https://github.com/shsridhar-beep/svgap/blob/main/examples/campaign.toml):

```toml
schema_version = "1.0"
id = "reset-repair-smoke"
taskpack = "reset-release-v0.2"
tasks = ["reset_counter"]
samples = 1

[generator]
command = "python3 my_generate.py"
label = "my-model-a"
interface_label = "my-lab-harness 1.0"

[execution]
timeout_seconds = 600
seed = 20260928

[repair]
enabled = true
max_attempts = 3
feedback = "diagnostic"

[budget]
max_model_calls = 3
wall_seconds = 1800
```

Set `execution.seed` when the adapter supports deterministic sampling. Every
attempt receives a stable derived seed through `SVGAP_CAMPAIGN_SEED`, alongside
`SVGAP_CAMPAIGN_ID`, `SVGAP_CAMPAIGN_CELL`, and `SVGAP_CAMPAIGN_ATTEMPT`; all
four values are recorded in the ledger. The adapter decides how to map that
seed into its provider or sampler.

The generator contract matches `svgap study run`: read the prompt on stdin,
write the response on stdout, and return nonzero on generation failure. Do not
put secrets in `command`; it is retained as provenance.

```bash
svgap campaign plan examples/campaign.toml
svgap campaign run examples/campaign.toml --output reports/campaign-01
svgap campaign resume reports/campaign-01
svgap campaign replay reports/campaign-01 \
  --cell sample-01/reset_counter --attempt 2
```

`plan` validates the manifest and reports the expanded cells and maximum call
count without invoking a model. `run` refuses a nonempty output directory.
`resume` derives pending work from `campaign-ledger.jsonl`; ledger records are
sequence-numbered, hash-chained, and only appended. `replay` verifies the saved
response digest, re-runs evaluation, and compares the normalized result
signature.

Each attempt retains the exact prompt, raw response, normalized design,
manifest, evaluation report, generation metadata, and oracle artifacts. A cell
stops early only at `contract_status = "closed"`. Otherwise repair continues
until `max_attempts`, `max_model_calls`, or `wall_seconds` is reached.

Feedback levels are intentionally explicit:

- `finding` supplies stable rule IDs and public finding messages;
- `diagnostic` also supplies tool diagnostics and observed coverage;
- `full` supplies the complete report and should be treated as the least
  blinded repair condition.

Use separate campaigns for different feedback conditions. They are research
treatments, not interchangeable model scores. Generated RTL remains untrusted;
use the same isolation boundary described in [Evaluate your model](evaluate-your-model.md).
