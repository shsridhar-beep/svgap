import shutil
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

import svgap
from svgap.demo import materialize_demo
from svgap.validation import validate_report_payload


HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


class PublicSurfaceTests(TestCase):
    def test_all_exports_resolve(self) -> None:
        for name in svgap.__all__:
            self.assertTrue(hasattr(svgap, name), name)

    def test_version_is_exported(self) -> None:
        self.assertTrue(svgap.__version__)


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class EvaluateTests(TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        materialize_demo(self.root)

    def test_evaluate_accepts_path_and_writes_report(self) -> None:
        report = svgap.evaluate(self.root / "unsafe/manifest.toml")
        self.assertEqual(report.functional.status, "pass")
        self.assertEqual(report.structural.status, "fail")
        self.assertTrue(report.gap_member)
        self.assertTrue((self.root / "unsafe/build/report.json").is_file())

    def test_evaluate_accepts_loaded_manifest(self) -> None:
        manifest = svgap.load_manifest(self.root / "safe/manifest.toml")
        report = svgap.evaluate(manifest)
        self.assertEqual(report.structural.status, "pass")
        self.assertFalse(report.gap_member)

    def test_legacy_programmatic_manifest_without_oracles_still_evaluates(self) -> None:
        manifest = svgap.load_manifest(self.root / "safe/manifest.toml")
        manifest.oracles.clear()
        report = svgap.evaluate(manifest, write_report=False)
        self.assertEqual(report.schema_version, "1.0")
        self.assertEqual(report.structural.status, "pass")

    def test_write_report_false_leaves_no_file(self) -> None:
        report = svgap.evaluate(
            self.root / "unsafe/manifest.toml", write_report=False
        )
        self.assertTrue(report.gap_member)
        self.assertFalse((self.root / "unsafe/build/report.json").exists())

    def test_skip_functional_cannot_be_gap_member(self) -> None:
        report = svgap.evaluate(
            self.root / "unsafe/manifest.toml",
            skip_functional=True,
            write_report=False,
        )
        self.assertEqual(report.functional.status, "not_run")
        self.assertEqual(report.structural.status, "fail")
        self.assertFalse(report.gap_member)

    def test_manifest_label_overrides_recorded_path(self) -> None:
        report = svgap.evaluate(
            self.root / "safe/manifest.toml",
            manifest_label="portable/manifest.toml",
            write_report=False,
        )
        self.assertEqual(report.manifest, "portable/manifest.toml")

    def test_manifest_error_raises(self) -> None:
        with self.assertRaises(svgap.ManifestError):
            svgap.evaluate(self.root / "does-not-exist.toml")

    def test_schema_v2_preserves_structural_and_lint_as_separate_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = svgap.evaluate(
            root / "examples/synchronizer_depth/unsafe/manifest.toml",
            write_report=False,
        )
        self.assertEqual(report.schema_version, "2.0")
        self.assertEqual(report.structural.status, "fail")
        self.assertEqual(
            [item.oracle_class for item in report.oracle_results],
            ["structural", "lint"],
        )
        self.assertTrue(report.gap_member)
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertNotIn("structural", payload)
        self.assertIs(validate_report_payload(payload), payload)
