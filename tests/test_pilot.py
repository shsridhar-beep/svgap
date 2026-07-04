from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json
import shutil

from svgap.backends.reference_yosys import ReferenceYosysBackend
from svgap.functional import run_functional
from svgap.manifest import load_manifest
from svgap.pilot import extract_systemverilog, load_task, materialize_candidate, render_manifest
from svgap.provenance import canonical_tree_digest


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

    def test_reset_v02_references_calibrate_every_task(self) -> None:
        pack = ROOT / "taskpacks/reset-replication-v0.2"
        task_dirs = sorted(path for path in (pack / "tasks").iterdir() if path.is_dir())
        self.assertEqual(len(task_dirs), 8)
        for task_dir in task_dirs:
            task = load_task(task_dir)
            for variant, expected in (("safe", "pass"), ("unsafe", "fail")):
                with self.subTest(task=task_dir.name, variant=variant):
                    with TemporaryDirectory() as directory:
                        run = Path(directory)
                        shutil.copy2(task_dir / f"reference-{variant}.sv", run / "design.sv")
                        (run / "manifest.toml").write_text(
                            render_manifest(task, task_dir), encoding="utf-8"
                        )
                        manifest = load_manifest(run / "manifest.toml")
                        self.assertEqual(run_functional(manifest).status, "pass")
                        result = ReferenceYosysBackend().check(manifest)
                        self.assertEqual(result.status, expected, result)
                        if variant == "unsafe":
                            self.assertIn(
                                "REF-RDC-001",
                                {finding.rule_id for finding in result.findings},
                            )

    def test_reset_v02_digest_is_stable(self) -> None:
        pack = ROOT / "taskpacks/reset-replication-v0.2"
        freeze = json.loads((pack / "freeze.json").read_text(encoding="utf-8"))
        self.assertEqual(
            canonical_tree_digest(pack, exclude_names={"freeze.json"}),
            freeze["canonical_digest"],
        )
