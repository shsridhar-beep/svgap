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

Every new rule or backend must document its evidence, limitations, version, and
failure behavior. Inconclusive analysis must return `unknown`, never `pass`.

Please do not contribute proprietary RTL, confidential constraints, model
credentials, or artifacts whose redistribution terms are unclear.
