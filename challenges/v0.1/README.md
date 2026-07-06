# Frontier-model challenge v0.1

This pack evaluates three capabilities that matter when generated digital RTL
moves from a research result toward a production team:

1. **Generation:** produce a candidate whose submitted functional and structural
   evidence is determinate and passing.
2. **Diagnosis:** distinguish answered, failed, and unanswered production
   questions, and name the evidence needed to resolve uncertainty.
3. **Repair:** remove a declared structural finding while preserving functional
   acceptance and avoiding new rule failures.

The scorer returns a profile of checks, not a blended scalar. This makes the
reason for failure legible. Example submissions and deliberately small synthetic
reports demonstrate the contract; they are not model-performance results.

```bash
svgap challenge score challenges/v0.1/generation/task.json \
  challenges/v0.1/generation/example-submission.json --json
svgap challenge score challenges/v0.1/diagnosis/task.json \
  challenges/v0.1/diagnosis/example-submission.json --json
svgap challenge score challenges/v0.1/repair/task.json \
  challenges/v0.1/repair/example-submission.json --json
```

All tracks are limited to digital RTL and the configured open-source evaluation
evidence. A passing profile is not silicon signoff.

## Run diagnosis and repair with any model harness

Commands receive the frozen prompt on stdin and return the response on stdout:

```bash
svgap challenge run diagnosis \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --run-id diagnosis-01 \
  --output reports/generated/diagnosis-01

svgap challenge run repair \
  --command "python3 my_generate.py" \
  --label my-model-a \
  --run-id repair-01 \
  --output reports/generated/repair-01
```

The diagnosis runner normalizes JSON responses and scores exact question
coverage, evidence, and uncertainty resolution. The repair runner evaluates the
unsafe input and returned RTL, then scores target removal, functional
preservation, backend consistency, and new-rule regressions. Free-form
diagnosis prose is mechanically checked for presence, not semantic truth; a
stronger claim requires independent adjudication.
