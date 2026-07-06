import base64
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from svgap.resources import taskpack_metadata, taskpack_root
from svgap.study_runner import evaluate_saved_responses, run_study, select_study_shape


HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


def command_for(text: str) -> str:
    encoded = base64.b64encode(text.encode()).decode()
    return (
        f'{sys.executable} -c "import base64; '
        f'print(base64.b64decode(\'{encoded}\').decode())"'
    )


class TaskpackResourceTests(TestCase):
    def test_reset_release_taskpack_is_discoverable(self) -> None:
        metadata = taskpack_metadata("reset-release-v0.2")
        self.assertEqual(metadata["version"], "0.2")
        self.assertEqual(metadata["smoke_task"], "reset_counter")
        self.assertEqual(len(metadata["tasks"]), 8)
        self.assertTrue(metadata["canonical_digest"].startswith("sha256:"))

    def test_default_shape_is_one_task_one_sample(self) -> None:
        tasks, samples, mode = select_study_shape("reset-release-v0.2")
        self.assertEqual(tasks, ["reset_counter"])
        self.assertEqual(samples, 1)
        self.assertEqual(mode, "smoke")

    def test_full_shape_is_frozen_protocol(self) -> None:
        tasks, samples, mode = select_study_shape("reset-release-v0.2", full=True)
        self.assertEqual(len(tasks), 8)
        self.assertEqual(samples, 3)
        self.assertEqual(mode, "full")


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class StudyRunnerTests(TestCase):
    def safe_response(self) -> str:
        return (
            taskpack_root("reset-release-v0.2")
            / "tasks/reset_counter/reference-safe.sv"
        ).read_text(encoding="utf-8")

    def test_smoke_study_writes_profile_and_portable_report(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "study"
            result = run_study(
                "reset-release-v0.2",
                command=command_for(self.safe_response()),
                label="example-model",
                interface_label="test-harness",
                output=output,
            )
            self.assertEqual(result["report_count"], 1)
            self.assertEqual(result["functional_pass"], 1)
            self.assertEqual(result["gap_members"], 0)
            self.assertTrue((output / "study-summary.json").is_file())
            self.assertTrue((output / "evidence-profile.html").is_file())
            report_path = next(output.glob("*/*/report.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["manifest"].startswith("/"))
            self.assertNotIn("/Users/", report_path.read_text(encoding="utf-8"))
            self.assertNotIn("/home/", report_path.read_text(encoding="utf-8"))

    def test_generate_then_evaluate_saved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated"
            result = run_study(
                "reset-release-v0.2",
                command=command_for(self.safe_response()),
                label="example-model",
                interface_label="test-harness",
                output=generated,
                generate_only=True,
            )
            self.assertEqual(result["responses"], 1)
            evaluated = evaluate_saved_responses(
                "reset-release-v0.2",
                responses=generated / "_responses",
                output=root / "evaluated",
            )
            self.assertEqual(evaluated["report_count"], 1)
