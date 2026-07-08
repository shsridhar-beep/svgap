# Run the Harbor experiment

Most coding-agent evaluations stop when generated code passes its tests. This
eight-task experiment asks a second question about the same RTL: did the agent
wire the circuit in the way the prompt required?

The primary success metric for this project is not page views, package
downloads, or stars. It is a complete, independently produced agent run with
inspectable evidence.

## Choose the smallest useful step

| Step | What it establishes | Time |
|---|---|---:|
| Run the known-good Oracle | Your Harbor and Docker setup can execute the evaluator | Usually a few minutes after the image is available |
| Run a non-Oracle agent | How one agent handled the eight prompts | Depends on the agent and model |
| Report what happened | A public replication receipt, blocker, or counterexample | About 2 minutes |
| Submit the evidence | A validated, content-addressed result that others can inspect | About 10 minutes after a completed run |

## 1. Check the evaluator

```bash
harbor run \
  -d svgap/svgap-reset-release@0.2 \
  -a oracle \
  -o jobs/svgap-oracle \
  --n-concurrent 1
```

All eight tasks should receive `reward = 1`.

## 2. Run an agent

```bash
harbor run \
  -d svgap/svgap-reset-release@0.2 \
  -a YOUR_AGENT \
  -m YOUR_MODEL \
  -o jobs/svgap-agent \
  --n-concurrent 1 \
  --n-attempts 1
```

Generated RTL is untrusted input. Run it on an isolated host without
credentials or sensitive source trees.

## 3. Leave a short public receipt

[Report a completed run, partial run, or setup blocker](https://github.com/shsridhar-beep/svgap/issues/new?template=run_report.yml).

A full evidence contribution is welcome but not required. One sentence about
what passed, what failed, or where setup stopped helps distinguish a research
question from a usability problem. Counterexamples and disagreement with the
reset rule are useful results.

SV-Gap performs no telemetry and uploads nothing automatically. A run becomes
visible to the project only when its researcher chooses to report it, upload a
Harbor job, or open a result pull request.

## 4. Preserve a complete result

```bash
pip install "svgap>=0.3.0a9"

svgap submission from-harbor jobs/svgap-agent/JOB_DIRECTORY \
  --dataset svgap/svgap-reset-release@0.2 \
  --id YOUR-SUBMISSION-ID \
  --title "YOUR TITLE" \
  --provenance-level public \
  --provider YOUR_PROVIDER \
  --contributor "YOUR NAME" \
  --output results/submissions/YOUR-SUBMISSION-ID
```

The importer checks task identity and agreement among the reports, verdicts,
and numeric scores. It then prints the observed result summary and links to the
public run-report and contribution paths.

See [submit a result](submitting-results.md) for provenance choices, private
publication checks, and pull-request instructions.

## Ways to collaborate

- [Report a run or blocker](https://github.com/shsridhar-beep/svgap/issues/new?template=run_report.yml)
- [Inspect the current research pulse](community-pulse.md)
- [Discuss replication or co-design](https://github.com/shsridhar-beep/svgap/discussions/18)
- [Propose another reset-release task family](https://github.com/shsridhar-beep/svgap/issues/7)
- [Challenge a finding or checker result](https://github.com/shsridhar-beep/svgap/issues/new?template=false_result.yml)

The public dataset is a narrow mechanism experiment. It is not silicon
signoff, a population estimate, or a model ranking.
