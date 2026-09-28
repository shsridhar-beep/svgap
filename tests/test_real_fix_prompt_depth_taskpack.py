import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from svgap.api import evaluate
from svgap.pilot import load_task, materialize_candidate, resolve_prompt
from svgap.provenance import canonical_tree_digest
from svgap.resources import taskpack_metadata


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "taskpacks/real-fix-prompt-depth-v0.1"
HAS_TOOLS = all(shutil.which(tool) for tool in ("iverilog", "vvp", "yosys"))


class RealFixPromptDepthStructureTests(TestCase):
    def test_pack_is_discoverable_through_public_resource_api(self) -> None:
        metadata = taskpack_metadata("real-fix-prompt-depth-v0.1")
        self.assertEqual(metadata["version"], "0.1")
        self.assertEqual(len(metadata["tasks"]), 24)

    def test_pack_has_stratified_real_fix_sources_and_cumulative_prompts(self) -> None:
        tasks = sorted(path for path in (PACK / "tasks").iterdir() if path.is_dir())
        self.assertEqual(len(tasks), 24)
        categories: dict[str, int] = {}
        sources: set[tuple[str, str, int]] = set()
        for task_dir in tasks:
            task = load_task(task_dir)
            categories[task["category"]] = categories.get(task["category"], 0) + 1
            source = json.loads((task_dir / "source.json").read_text(encoding="utf-8"))
            upstream = source["upstream"]
            sources.add((upstream["org"], upstream["repo"], upstream["pull_request"]))
            prompts = [
                resolve_prompt(task_dir, task, f"level_{level}")[0].read_text(
                    encoding="utf-8"
                )
                for level in range(4)
            ]
            self.assertTrue(all(prompts[level + 1].startswith(prompts[level]) for level in range(3)))
        self.assertEqual(
            categories,
            {"protocol": 8, "synthesis_equivalence": 8, "temporal": 8},
        )
        self.assertEqual(len(sources), 24)

    def test_frozen_digest_is_stable(self) -> None:
        freeze = json.loads((PACK / "freeze.json").read_text(encoding="utf-8"))
        self.assertEqual(
            canonical_tree_digest(PACK, exclude_names={"freeze.json"}),
            freeze["canonical_digest"],
        )


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class RealFixPromptDepthCalibrationTests(TestCase):
    def test_safe_and_unsafe_references_calibrate(self) -> None:
        tasks = sorted(path for path in (PACK / "tasks").iterdir() if path.is_dir())
        for task_dir in tasks:
            for variant, expected in (("safe", "pass"), ("unsafe", "fail")):
                with self.subTest(task=task_dir.name, variant=variant):
                    with TemporaryDirectory() as directory:
                        root = Path(directory)
                        response = root / "response.sv"
                        response.write_text(
                            (task_dir / f"reference-{variant}.sv").read_text(
                                encoding="utf-8"
                            ),
                            encoding="utf-8",
                        )
                        manifest = materialize_candidate(
                            task_dir,
                            response,
                            "calibration",
                            root / "runs",
                            prompt_level="level_0",
                        )
                        report = evaluate(manifest).to_dict()
                        self.assertEqual(report["functional"]["status"], "pass", report)
                        contributing = [
                            item
                            for item in report["oracle_results"]
                            if item["contributes_to_gap"]
                        ]
                        self.assertEqual(len(contributing), 1)
                        self.assertEqual(contributing[0]["status"], expected, report)
