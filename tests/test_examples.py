from pathlib import Path
from unittest import TestCase, skipUnless
import shutil
import json
import subprocess

from svgap.backends.reference_yosys import (
    ReferenceYosysBackend,
    SeqCell,
    reset_synchronizer_bits,
    same_domain_successors,
    trace_sequential_sources,
)
from svgap.api import evaluate
from svgap.functional import run_functional
from svgap.manifest import load_manifest
from svgap.model import CrossingIntent
from svgap.validation import validate_report_payload


ROOT = Path(__file__).resolve().parents[1]
HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


class ReferenceYosysUtilityTests(TestCase):
    def test_sequential_source_trace_is_linear_through_reconvergence(self) -> None:
        class CountingDrivers(dict):
            calls = 0

            def get(self, key, default=None):
                self.calls += 1
                return super().get(key, default)

        source = SeqCell("source", "$dff", 2, "src", (0,), (1,), (), {})
        drivers = CountingDrivers()
        previous = 1
        for layer in range(12):
            left = 100 + layer * 3
            right = left + 1
            merged = left + 2
            drivers[left] = (f"left_{layer}", "$not", (previous,))
            drivers[right] = (f"right_{layer}", "$not", (previous,))
            drivers[merged] = (f"merge_{layer}", "$and", (left, right))
            previous = merged

        found = trace_sequential_sources(previous, {1: source}, drivers, set())

        self.assertEqual([cell.name for cell, _path in found], ["source"])
        self.assertLessEqual(drivers.calls, len(drivers))


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class ExampleTests(TestCase):
    def test_paired_examples(self) -> None:
        expected_rules = {
            "level_crossing": "REF-CDC-001",
            "comb_crossing": "REF-CDC-002",
            "gray_counter": "REF-CDC-003",
            "pulse_crossing": "REF-CDC-004",
            "toggle_crossing": "REF-CDC-005",
            "handshake_crossing": "REF-CDC-006",
            "cdc_reconvergence": "REF-CDC-007",
            "async_fifo": "REF-CDC-008",
            "synchronizer_depth": "REF-META-001",
            "reset_release": "REF-RDC-001",
            "reset_domain_crossing": "REF-RDC-002",
            "reset_gating": "REF-RDC-003",
            "reset_reconvergence": "REF-RDC-004",
            "power_on_x": "REF-XPROP-001",
            "x_control_masking": "REF-XPROP-002",
            "selective_reset": "REF-XPROP-003",
            "uninitialized_memory": "REF-XPROP-004",
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

    def test_temporal_protocol_and_equivalence_witnesses(self) -> None:
        expected_rules = {
            "temporal_backpressure": "REF-PROT-001",
            "temporal_response": "REF-TEMP-001",
            "temporal_pulse": "REF-TEMP-002",
            "synthesis_directive_equivalence": "REF-EQUIV-001",
            "functional_equivalence": "REF-EQUIV-001",
        }
        for family, expected_rule in expected_rules.items():
            safe = evaluate(
                ROOT / f"examples/{family}/safe/manifest.toml", write_report=False
            )
            unsafe = evaluate(
                ROOT / f"examples/{family}/unsafe/manifest.toml", write_report=False
            )
            validate_report_payload(safe.to_dict())
            validate_report_payload(unsafe.to_dict())
            with self.subTest(family=family, variant="safe"):
                self.assertEqual(safe.functional.status, "pass")
                self.assertFalse(safe.gap_member)
                self.assertEqual(
                    safe.oracle_results[0].status,
                    "pass",
                    safe.oracle_results[0],
                )
                if shutil.which("verilator"):
                    self.assertEqual(safe.oracle_results[1].oracle_class, "lint")
                    self.assertEqual(safe.oracle_results[1].status, "pass")
                    self.assertEqual(safe.oracle_results[1].findings, [])
            with self.subTest(family=family, variant="unsafe"):
                self.assertEqual(unsafe.functional.status, "pass")
                self.assertTrue(unsafe.gap_member)
                self.assertEqual(
                    unsafe.oracle_results[0].status,
                    "fail",
                    unsafe.oracle_results[0],
                )
                self.assertIn(
                    expected_rule,
                    {item.rule_id for item in unsafe.oracle_results[0].findings},
                )
                if shutil.which("verilator"):
                    self.assertEqual(unsafe.oracle_results[1].oracle_class, "lint")
                    self.assertEqual(unsafe.oracle_results[1].status, "pass")
                    self.assertEqual(unsafe.oracle_results[1].findings, [])

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

    def test_power_on_rule_reports_output_evidence(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        result = ReferenceYosysBackend().check(manifest)
        finding = next(item for item in result.findings if item.rule_id == "REF-XPROP-001")
        self.assertIn("data_out", finding.evidence["output_signals"])

    def test_power_on_rule_abstains_without_declared_reset(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        manifest.resets.clear()
        result = ReferenceYosysBackend().check(manifest)
        self.assertEqual(result.status, "unknown")
        self.assertIn("no reset was declared", " ".join(result.diagnostics))

    def test_power_on_rule_is_disabled_when_intent_is_unspecified(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        manifest.power_on = "unspecified"
        result = ReferenceYosysBackend().check(manifest)
        self.assertEqual(result.status, "pass", result)

    def test_power_on_perturbation_separates_witnesses(self) -> None:
        root = ROOT / "examples/power_on_x"
        for variant, expected in (("safe", "0"), ("unsafe", "1")):
            with self.subTest(variant=variant):
                output = root / variant / "build/perturb.vvp"
                output.parent.mkdir(exist_ok=True)
                compile_result = subprocess.run(
                    [
                        "iverilog",
                        "-g2012",
                        f"-Ptb.EXPECTED=1'b{expected}",
                        "-o",
                        str(output),
                        str(root / variant / "design.sv"),
                        str(root / "perturbation_tb.sv"),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
                run_result = subprocess.run(
                    ["vvp", str(output)], capture_output=True, text=True, check=False
                )
                self.assertEqual(run_result.returncode, 0, run_result.stderr)
                self.assertIn("PERTURBATION_PASS", run_result.stdout)
