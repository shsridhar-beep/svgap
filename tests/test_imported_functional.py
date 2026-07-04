import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.functional import run_functional
from svgap.manifest import load_manifest
from svgap.provenance import canonical_file_set_digest


class ImportedFunctionalTests(TestCase):
    def test_imported_result_is_bound_to_candidate_sources(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            design = root / "design.sv"
            design.write_text("module imported(input logic clk); endmodule\n")
            digest = canonical_file_set_digest(root, [design])
            (root / "functional-result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "status": "pass",
                        "producer": "example-benchmark/v1",
                        "candidate_digest": digest,
                        "tool_versions": {"simulator": "example-1.0"},
                        "evidence": {"test_count": 12},
                    }
                )
            )
            (root / "manifest.toml").write_text(
                """schema_version = "1.0"
candidate_id = "imported"
[design]
top = "imported"
sources = ["design.sv"]
[functional]
import = "functional-result.json"
[structural]
backend = "reference-yosys"
[intent]
asynchronous_groups = []
"""
            )
            result = run_functional(load_manifest(root / "manifest.toml"))
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.evidence["candidate_digest"], digest)
        self.assertIn("import_sha256", result.evidence)

    def test_digest_mismatch_is_a_tool_error(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "design.sv").write_text("module imported; endmodule\n")
            (root / "functional-result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "status": "pass",
                        "producer": "example",
                        "candidate_digest": "sha256:" + "0" * 64,
                    }
                )
            )
            (root / "manifest.toml").write_text(
                """schema_version = "1.0"
candidate_id = "imported"
[design]
top = "imported"
sources = ["design.sv"]
[functional]
import = "functional-result.json"
[structural]
backend = "reference-yosys"
[intent]
asynchronous_groups = []
"""
            )
            result = run_functional(load_manifest(root / "manifest.toml"))
        self.assertEqual(result.status, "tool_error")
        self.assertIn("does not match", result.stderr)
