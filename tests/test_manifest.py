from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.manifest import ManifestError, load_manifest


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(TestCase):
    def test_loads_example_manifest(self) -> None:
        manifest = load_manifest(ROOT / "examples/level_crossing/safe/manifest.toml")
        self.assertEqual(manifest.top, "level_crossing")
        self.assertEqual([clock.name for clock in manifest.clocks], ["source", "destination"])
        self.assertEqual(manifest.asynchronous_groups, [["source"], ["destination"]])
        self.assertEqual(manifest.power_on, "unspecified")
        self.assertFalse(manifest.init_attributes_are_power_on)

    def test_power_on_intent_is_loaded(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/safe/manifest.toml")
        self.assertEqual(manifest.power_on, "reset_required")
        self.assertFalse(manifest.init_attributes_are_power_on)

    def test_invalid_power_on_intent_is_rejected(self) -> None:
        source = (ROOT / "examples/power_on_x/safe/manifest.toml").read_text()
        source = source.replace('power_on = "reset_required"', 'power_on = "magic"')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (root / "design.sv").write_text("module power_on_x; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_report_cannot_escape_manifest_directory(self) -> None:
        source = (ROOT / "examples/level_crossing/safe/manifest.toml").read_text()
        source = source.replace('report = "build/report.json"', 'report = "../../escape.json"')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module level_crossing; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_unknown_schema_version_is_rejected(self) -> None:
        source = (ROOT / "examples/level_crossing/safe/manifest.toml").read_text()
        source = source.replace('schema_version = "1.0"', 'schema_version = "99"')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module level_crossing; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_source_cannot_escape_manifest_directory(self) -> None:
        source = (ROOT / "examples/level_crossing/safe/manifest.toml").read_text()
        source = source.replace('sources = ["design.sv"]', 'sources = ["../design.sv"]')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "manifest.toml"
            path.parent.mkdir()
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module level_crossing; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_malformed_intent_table_has_clean_manifest_error(self) -> None:
        source = (ROOT / "examples/level_crossing/safe/manifest.toml").read_text()
        source = source.replace("[[intent.clocks]]", "[[intent.clocks]]\nunexpected = 1", 1)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text(
                "module level_crossing; endmodule\n", encoding="utf-8"
            )
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_reset_missing_port_is_rejected(self) -> None:
        source = (ROOT / "examples/reset_release/safe/manifest.toml").read_text()
        source = source.replace('port = "arst_n"\n', "")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module reset_release; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_reset_unknown_assertion_is_rejected(self) -> None:
        source = (ROOT / "examples/reset_release/safe/manifest.toml").read_text()
        source = source.replace('assertion = "async"', 'assertion = "eventually"')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module reset_release; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_reset_unknown_deassertion_is_rejected(self) -> None:
        source = (ROOT / "examples/reset_release/safe/manifest.toml").read_text()
        source = source.replace('deassertion = "sync"', 'deassertion = "eventually"')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module reset_release; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_reset_referencing_undeclared_clock_is_rejected(self) -> None:
        source = (ROOT / "examples/reset_release/safe/manifest.toml").read_text()
        source = source.replace(
            'deassertion = "sync"\n', 'deassertion = "sync"\nclock = "no_such_clock"\n'
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module reset_release; endmodule\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_reset_referencing_declared_clock_loads(self) -> None:
        source = (ROOT / "examples/reset_release/safe/manifest.toml").read_text()
        source = source.replace('deassertion = "sync"\n', 'deassertion = "sync"\nclock = "core"\n')
        with TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (Path(directory) / "design.sv").write_text("module reset_release; endmodule\n")
            manifest = load_manifest(path)
            self.assertEqual(manifest.resets[0].clock, "core")

    def test_functional_import_and_commands_are_mutually_exclusive(self) -> None:
        source = (ROOT / "examples/level_crossing/safe/manifest.toml").read_text()
        source = source.replace(
            "[functional]\n", '[functional]\nimport = "functional-result.json"\n'
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.toml"
            path.write_text(source, encoding="utf-8")
            (root / "design.sv").write_text("module level_crossing; endmodule\n")
            (root / "functional-result.json").write_text("{}\n")
            with self.assertRaises(ManifestError):
                load_manifest(path)
