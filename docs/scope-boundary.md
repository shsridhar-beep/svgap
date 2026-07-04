# Scope boundary

SV-Gap is a broadly applicable framework for evaluating the handoff from
frontier model research artifacts to production-oriented digital design
evidence. Its executable scope is digital RTL and digital verification.

## In scope

- intent-carrying evaluation contracts;
- functional-result provenance and import;
- CDC/RDC structural evaluation of digital RTL;
- explicit `pass`, `fail`, `unknown`, and `tool_error` outcomes;
- digital trace comparison and generic adjudication contracts;
- generation, diagnosis, and repair studies for frontier models;
- open-source digital EDA backends and adapters; and
- evidence needed for a digital-design production handoff.

## Explicitly out of scope

- analog or mixed-signal design generation;
- transistor-level, SPICE, or continuous-time simulation;
- analog-block modeling or verification;
- PLL, ADC, DAC, regulator, sensor, settling, noise, or calibration behavior;
- mixed-signal interface signoff; and
- claims about analog-design capability.

References to metastability or recovery/removal timing explain why a digital
functional oracle cannot identify a CDC/RDC structural property. They do not
expand the project into analog design or analog verification.

Contributor taskpacks and research claims must remain within this boundary.
