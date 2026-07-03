from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.manifest import load_manifest
from svgap.pilot import extract_systemverilog, load_task, materialize_candidate


ROOT = Path(__file__).resolve().parents[1]


class PilotTests(TestCase):
    def test_extracts_named_module_from_fence(self) -> None:
        raw = "prose\n```systemverilog\nmodule wanted; endmodule\n```"
        self.assertEqual(extract_systemverilog(raw, "wanted"), "module wanted; endmodule\n")

    def test_materializes_reproducible_candidate(self) -> None:
        task = ROOT / "taskpacks/pilot-v0.1/tasks/level_crossing"
        design = (ROOT / "examples/level_crossing/safe/design.sv").read_text()
        with TemporaryDirectory() as directory:
            response = Path(directory) / "response.txt"
            response.write_text(design)
            manifest_path = materialize_candidate(
                task, response, "test/model", Path(directory) / "runs", "run-01"
            )
            manifest = load_manifest(manifest_path)
            self.assertEqual(manifest.top, "level_crossing")
            self.assertTrue((manifest_path.parent / "provenance.json").is_file())
            self.assertEqual(manifest_path.parent.parent.name, "run-01")

    def test_reset_replication_pack_is_complete(self) -> None:
        root = ROOT / "taskpacks/reset-replication-v0.1/tasks"
        task_dirs = sorted(path for path in root.iterdir() if path.is_dir())
        self.assertEqual(len(task_dirs), 8)
        for task_dir in task_dirs:
            with self.subTest(task=task_dir.name):
                task = load_task(task_dir)
                self.assertTrue((task_dir / "prompt.md").is_file())
                self.assertTrue((task_dir / str(task["testbench"])).is_file())
                self.assertEqual(len(task.get("resets", [])), 1)
