# Third-party tools and data

SV-Gap invokes external tools but does not vendor them in v0.1.

| Component | Purpose | Distribution model |
|---|---|---|
| Yosys | RTL elaboration and JSON netlist generation | External executable; ISC license |
| Icarus Verilog | Functional simulation for bundled witnesses | External executable; GPL-2.0-or-later |
| najaeda | RTL elaboration (bundled slang frontend) and SNL netlist analysis for the `reference-naja` structural backend | Python package installed with SV-Gap via pip; Apache-2.0 license |
| jsonschema | Development/CI validation of JSON reports | Optional Python dependency; MIT license |
| OSS CAD Suite | Pinned container distribution of Yosys, Icarus, and supporting open tools | External release archive; component licenses are inventoried by YosysHQ |
| Debian/Python container | Runtime base for the reproducible convenience image | External OCI image; component licenses retained in the image |

Checker backends and benchmark adapters must document their licenses
independently. A repository being publicly readable is not sufficient evidence
that its code or dataset may be redistributed.

SV-Gap does not depend on inaccessible or non-redistributable checker code. The
public OpenCDC project was reviewed as prior art but is not used because its
checker is currently documented as planned rather than implemented.

The benchmark audit reads external VerilogEval and RTLLM repositories under
their MIT licenses. It also reads the CVDP dataset, whose non-code content is CC
BY 4.0, original code is Apache-2.0, and derivative components retain the
licenses enumerated in CVDP's NOTICE. No benchmark source dataset is vendored.

Generated RTL artifacts identify the model provider and exact requested model as
provenance. They do not include provider software, weights, or raw transcripts.
The project applies Apache-2.0 only to rights owned or controlled by the artifact
releaser; provider names do not imply endorsement.

The optional synthetic-adjudication study likewise invokes authenticated model
clients that are not open-source EDA dependencies. The public runner is
provider-adapter code; users can replace those adapters, but an exact replay of
the locked panel requires access to the named model endpoints. Core `svgap`
installation and evaluation do not require either client.
