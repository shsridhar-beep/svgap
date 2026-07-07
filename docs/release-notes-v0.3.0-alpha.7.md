# SV-Gap v0.3.0-alpha.7

This release closes the path from a public Harbor run to a reviewable SV-Gap
result contribution.

Researchers can now import a complete job using the pinned Harbor identifier
`svgap/svgap-reset-release@0.2`. A repository checkout is not required. The CLI
uses packaged, trusted task metadata to verify every task digest and then
checks agreement among the retained SV-Gap reports, Harbor verdicts, and
numeric scores.

The public dataset page also explains the experiment for researchers outside
the chip-design domain. It starts with the familiar eval question of whether a
test pass can hide an important mistake, reports the first public run, and
invites replication, counterexamples, rule critiques, and new task ideas.

This remains an alpha release. The reset-release dataset is a narrow mechanism
demonstration, not silicon signoff, a population estimate, or a model ranking.
