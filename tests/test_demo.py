from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from svgap.cli import main
from svgap.demo import DemoError, materialize_demo
from svgap.enums import DemoScenario


HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class DemoTests(TestCase):
    def test_demo_rejects_a_file_as_output_directory(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "not-a-directory"
            output.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(DemoError, "not a directory"):
                materialize_demo(output)

    def test_demo_is_a_successful_explanation_of_an_expected_finding(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        self.assertIn("same functional result", output)
        self.assertIn("safe       pass", output)
        self.assertIn("unsafe     pass", output)
        self.assertIn("REF-RDC-001", output)

    def test_demo_is_a_successful_explanation_of_comb_crossing_rule(self)-> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "comb-crossing"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        self.assertIn("same functional result", output)
        self.assertIn("safe       pass", output)
        self.assertIn("unsafe     pass", output)
        self.assertIn("REF-CDC-002", output)
        
    def test_demo_is_a_successful_explanation_of_power_on_rule(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "power-on"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        self.assertIn("same functional result", output)
        self.assertIn("safe       pass", output)
        self.assertIn("unsafe     pass", output)
        self.assertIn("REF-XPROP-001", output)

    def test_demo_works_with_explicit_reset_release_scenario(self)-> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "reset-release"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        self.assertIn("same functional result", output)
        self.assertIn("safe       pass", output)
        self.assertIn("unsafe     pass", output)
        self.assertIn("REF-RDC-001", output)

    def test_demo_explicit_reset_release_is_same_as_default_fallback_scenario(self) -> None:
        stream1= io.StringIO()
        with redirect_stdout(stream1):
            code1 = main(["demo", "--scenario", "reset-release"])
        self.assertEqual(code1, 0)
        stream2 = io.StringIO()
        with redirect_stdout(stream2):
            code2 = main(["demo"])
        self.maxDiff = None
        self.assertEqual(code2, 0)
        self.assertEqual(stream1.getvalue(), stream2.getvalue())

    def test_demo_scenario_all_runs_every_scenario(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "all"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        for scenario in DemoScenario:
            self.assertIn(scenario.value, output)
        self.assertIn("overall: pass", output)

    def test_demo_scenario_all_json_reports_each_scenario(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "all", "--json"])
        self.assertEqual(code, 0)
        summary = json.loads(stream.getvalue())
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(set(summary["scenarios"]), {scenario.value for scenario in DemoScenario})
        for scenario in DemoScenario:
            self.assertEqual(summary["scenarios"][scenario.value]["status"], "pass")

    def test_demo_can_preserve_machine_readable_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"
            with redirect_stdout(io.StringIO()):
                code = main(["demo", "--output", str(output), "--json"])
            self.assertEqual(code, 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "pass")
            self.assertEqual(summary["safe"]["structural"], "pass")
            self.assertEqual(summary["unsafe"]["structural"], "fail")
            self.assertTrue((output / "safe/build/report.json").is_file())
            self.assertTrue((output / "unsafe/build/report.json").is_file())


class DemoScenarioListTests(TestCase):
    def test_demo_scenario_list_does_not_require_demo_tools(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["demo", "--scenario", "list"])
        self.assertEqual(code, 0)
        output = stream.getvalue()
        self.assertIn("reset-release", output)
        self.assertIn("comb-crossing", output)
        self.assertIn("power-on", output)
