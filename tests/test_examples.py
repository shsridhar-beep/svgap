from pathlib import Path
from unittest import TestCase, skipUnless
import shutil
import json

from svgap.backends.reference_yosys import (
    ReferenceYosysBackend,
    SeqCell,
    reset_synchronizer_bits,
    same_domain_successors,
)
from svgap.functional import run_functional
from svgap.manifest import load_manifest
from svgap.model import CrossingIntent


ROOT = Path(__file__).resolve().parents[1]
HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class ExampleTests(TestCase):
    def test_paired_examples(self) -> None:
        expected_rules = {
            "level_crossing": "REF-CDC-001",
            "comb_crossing": "REF-CDC-002",
            "gray_counter": "REF-CDC-003",
            "reset_release": "REF-RDC-001",
        }
        for family, expected_rule in expected_rules.items():
            with self.subTest(family=family, variant="unsafe"):
                unsafe = load_manifest(ROOT / f"examples/{family}/unsafe/manifest.toml")
                self.assertEqual(run_functional(unsafe).status, "pass")
                result = ReferenceYosysBackend().check(unsafe)
                self.assertEqual(result.status, "fail", result)
                self.assertIn(expected_rule, {finding.rule_id for finding in result.findings})
            with self.subTest(family=family, variant="safe"):
                safe = load_manifest(ROOT / f"examples/{family}/safe/manifest.toml")
                self.assertEqual(run_functional(safe).status, "pass")
                result = ReferenceYosysBackend().check(safe)
                self.assertEqual(result.status, "pass", result)
                self.assertEqual(result.findings, [])

    def test_imported_functional_result_example(self) -> None:
        manifest = load_manifest(ROOT / "examples/imported_result/manifest.toml")
        functional = run_functional(manifest)
        self.assertEqual(functional.status, "pass")
        self.assertIsNotNone(functional.imported_from)
        self.assertIn("import_sha256", functional.evidence)
        self.assertEqual(ReferenceYosysBackend().check(manifest).status, "pass")

    def test_gray_declaration_does_not_waive_binary_source(self) -> None:
        manifest = load_manifest(ROOT / "examples/gray_counter/unsafe/manifest.toml")
        manifest.crossings.append(
            CrossingIntent(
                source="src_count", destination="dst_count", protocol="gray"
            )
        )
        result = ReferenceYosysBackend().check(manifest)
        self.assertEqual(result.status, "fail")
        self.assertIn("REF-CDC-003", {finding.rule_id for finding in result.findings})

    def test_wildcard_gray_declaration_is_name_independent(self) -> None:
        manifest = load_manifest(ROOT / "examples/gray_counter/safe/manifest.toml")
        manifest.crossings.clear()
        manifest.crossings.append(
            CrossingIntent(source="*", destination="*", protocol="gray")
        )
        result = ReferenceYosysBackend().check(manifest)
        self.assertEqual(result.status, "pass", result)

        unsafe = load_manifest(ROOT / "examples/gray_counter/unsafe/manifest.toml")
        unsafe.crossings.append(
            CrossingIntent(source="*", destination="*", protocol="gray")
        )
        result = ReferenceYosysBackend().check(unsafe)
        self.assertEqual(result.status, "fail", result)
        self.assertIn("REF-CDC-003", {finding.rule_id for finding in result.findings})

    def test_undeclared_async_group_names_are_inconclusive(self) -> None:
        manifest = load_manifest(ROOT / "examples/level_crossing/unsafe/manifest.toml")
        ReferenceYosysBackend().check(manifest)
        netlist = json.loads(
            (manifest.path.parent / "build/structural.json").read_text(encoding="utf-8")
        )
        manifest.asynchronous_groups = [["typo_source"], ["typo_destination"]]
        result = ReferenceYosysBackend()._analyze(manifest, netlist)
        self.assertEqual(result.status, "unknown")
        self.assertIn("undeclared clocks", " ".join(result.diagnostics))

    def test_register_cannot_be_its_own_second_stage(self) -> None:
        cell = SeqCell("stage", "$dffe", 2, "dst", (10,), (10,), (), {})
        self.assertEqual(same_domain_successors(cell, {10: [cell]}, {}), [])

    def test_wrong_release_constant_is_not_reset_synchronizer(self) -> None:
        manifest = load_manifest(ROOT / "examples/reset_release/safe/manifest.toml")
        reset = manifest.resets[0]
        fake = SeqCell("fake", "$adff", 2, "core", ("0", 11), (11, 12), (3,), {})
        self.assertEqual(reset_synchronizer_bits([fake], {3: reset}), set())

    def test_attribute_cannot_waive_operational_reset_state(self) -> None:
        manifest = load_manifest(ROOT / "examples/reset_release/unsafe/manifest.toml")
        ReferenceYosysBackend().check(manifest)
        netlist = json.loads(
            (manifest.path.parent / "build/structural.json").read_text(encoding="utf-8")
        )
        netlist["modules"][manifest.top]["netnames"]["count"].setdefault(
            "attributes", {}
        )["svgap_reset_sync"] = "1"
        result = ReferenceYosysBackend()._analyze(manifest, netlist)
        self.assertEqual(result.status, "fail")
        self.assertIn("REF-RDC-001", {finding.rule_id for finding in result.findings})
