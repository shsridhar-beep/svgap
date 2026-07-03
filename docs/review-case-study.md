# Review-paper case-study bridge

The Review should use SV-Gap as a compact example, not as unpublished primary
evidence carrying the paper's thesis.

## Suggested box

**Functional success can be structurally non-identifying.** In hardware design,
two AI-generated RTL implementations may produce identical outputs in a
benchmark simulation while differing in clock- or reset-domain safety. Standard
digital simulation does not reproduce analog metastability, and many public
tasks omit the clock-domain intent needed for structural analysis. A small open
case study therefore evaluates generated RTL twice: once with the benchmark's
functional oracle and again with an explicit structural oracle. The resulting
"functional pass, structural fail" cases illustrate a broader production
lesson: offline outcome metrics may leave latent implementation properties
unobserved. This example motivates layered evaluation rather than claiming that
one additional checker establishes deployment readiness.

Until full-case independent adjudication is complete, the Review should use the
conceptual example without the `14/57` rate. After public archival and locked
independent labels, a compact parenthetical may report the reconciled count with
its denominator and taskpack-conditional qualifier.

## Generalization boundary

The hardware case study supports the general concept of layered validity
oracles. It does not by itself establish prevalence or causal equivalence in
medicine, finance, cybersecurity, or other high-stakes domains. Those domains
require their own production evidence and expert contributions.
