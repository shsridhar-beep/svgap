import json
import shutil
from pathlib import Path
from unittest import TestCase, skipUnless

from svgap.backends.reference_yosys import ReferenceYosysBackend
from svgap.functional import run_functional
from svgap.manifest import load_manifest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/disputed_finding_template"
HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


class DisputedFindingFixtureTests(TestCase):
    def test_expected_finding_file_is_well_formed(self) -> None:
        expected = json.loads((FIXTURE / "expected-finding.json").read_text(encoding="utf-8"))
        for key in ("rule_id", "checker_status", "disposition", "claim", "reproducer"):
            self.assertIn(key, expected)
        self.assertEqual(expected["disposition"], "disputed")

    @skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
    def test_disputed_finding_still_fires_and_is_not_silently_resolved(self) -> None:
        expected = json.loads((FIXTURE / "expected-finding.json").read_text(encoding="utf-8"))

        manifest = load_manifest(FIXTURE / "manifest.toml")
        self.assertEqual(run_functional(manifest).status, "pass")

        result = ReferenceYosysBackend().check(manifest)

        # A recorded dispute documents disagreement with the checker; it must
        # not be a mechanism for making the underlying finding disappear.
        self.assertEqual(result.status, expected["checker_status"])
        self.assertIn(expected["rule_id"], {finding.rule_id for finding in result.findings})
        self.assertEqual(expected["disposition"], "disputed")
