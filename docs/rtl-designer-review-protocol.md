# Comprehensive independent RTL designer review protocol

Status: frozen before external review.

Reviewer packet SHA-256:
`df961c824be3f7a48ec22312e7449a9ef57b6e523107d5b6a67197925042f83e`.
The packet itself remains private until first-pass labels are locked.

## Purpose

This is the project's single comprehensive human-expert review request. It
evaluates whether SV-Gap's implemented evidence contract helps close a
research-to-production RTL gap. It does not estimate a universal defect rate or
rank models.

Functional benchmark acceptance does not establish every production-relevant
property. CDC, reset release, multi-bit transfer, and power-on policy require
declared intent and distinct evidence. SV-Gap preserves functional outcomes,
reports configured structural questions separately, and distinguishes `pass`,
`fail`, `unknown`, and `tool_error`.

The reviewer assesses technical correctness, intent sufficiency, safe claim
boundaries, evidence usefulness, appropriate abstention, and missing
pre-deployment evidence.

## Review unit and timebox

The packet is designed for one to two hours and contains:

1. five controlled safe/unsafe witness pairs covering every implemented primary
   rule family: `REF-CDC-001`, `REF-CDC-002`, `REF-CDC-003`, `REF-RDC-001`, and
   `REF-XPROP-001`;
2. three blinded generated candidates exercising reset release and the broader
   selective-reset shapes represented by `REF-XPROP-002` and
   `REF-XPROP-003`; and
3. a repository-level production-risk questionnaire.

This diagnostic selection provides breadth across the repository without
turning expert review into full-study annotation. It is deliberately not a
representative sample.

## Judgments

For each controlled pair, the reviewer records whether the pair supports the
stated rule distinction, does not support it, or is uncertain, with technical
evidence and missing qualifications.

For each blinded candidate, the reviewer records `pass`, `violation`, or
`uncertain`, confidence, source-level evidence, and notes. The reviewer judges
the supplied specification and RTL, not model quality or likely silicon
failure.

The repository-level review asks whether:

- the production questions are legitimate and correctly scoped;
- the manifest carries sufficient intent;
- the evaluator abstains in the right situations;
- clean and failing results have safe meanings;
- evidence is actionable for an RTL team;
- key checker failure modes are disclosed;
- important deployment evidence remains explicit; and
- the evidence profile improves the research-to-production handoff.

## Independence and lock

Model identity, sample identity, functional outcomes, automated candidate
outcomes, and private mappings are withheld. Before returning first-pass
answers, the reviewer is instructed not to consult the repository, automated
reports, source-text searches, or other labels. Prior exposure and tool use are
disclosed.

Returned files are timestamped, content-hashed, and retained unchanged before
automated comparison or reconciliation. Later discussion or revised judgments
remain separate from the original review.

## Permitted claims

The review may support statements that one independent RTL designer:

- confirmed, rejected, or qualified specific rule constructions;
- assessed representative applications of the rules;
- identified missing intent, evidence, and abstention conditions;
- evaluated whether the profile maps to production review practice; and
- recommended concrete technical or methodological changes.

It does not support:

- defect prevalence or model-quality estimates;
- population-level false-positive or false-negative rates;
- comprehensive CDC/RDC, reset, X-safety, or silicon signoff;
- expert consensus; or
- claims about unimplemented properties.

## Repository publication sequence

Before labels return, the repository may contain this protocol, rule and
manifest definitions, controlled witnesses, tests, limitations, and the packet
digest. The packet, candidate identities, mappings, and automated candidate
outcomes remain excluded.

After first-pass labels are locked, the repository may add the review scope,
reviewer qualification or agreed anonymous description, disclosure, original
judgments, disagreements, unresolved cases, repository-risk feedback, and any
resulting rule or claim-boundary changes. Candidate RTL is published only after
provenance, authorization, licensing, privacy, and blinding review.
