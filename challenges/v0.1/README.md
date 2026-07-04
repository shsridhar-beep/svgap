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
svgap challenge-score challenges/v0.1/generation/task.json \
  challenges/v0.1/generation/example-submission.json --json
svgap challenge-score challenges/v0.1/diagnosis/task.json \
  challenges/v0.1/diagnosis/example-submission.json --json
svgap challenge-score challenges/v0.1/repair/task.json \
  challenges/v0.1/repair/example-submission.json --json
```

All tracks are limited to digital RTL and the configured open-source evaluation
evidence. A passing profile is not silicon signoff.
