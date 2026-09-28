import base64
import json
from pathlib import Path
import shlex
import shutil
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from svgap.campaign import (
    CampaignError,
    plan_campaign,
    replay_campaign,
    resume_campaign,
    run_campaign,
)
from svgap.resources import taskpack_root


HAS_TOOLS = all(shutil.which(tool) for tool in ("yosys", "iverilog", "vvp"))


def campaign_text(command: str, *, budget: int = 2) -> str:
    pack = taskpack_root("reset-release-v0.2")
    return f'''schema_version = "1.0"
id = "repair-test"
taskpack = {json.dumps(str(pack))}
tasks = ["reset_counter"]
samples = 1

[generator]
command = {json.dumps(command)}
label = "test-model"
interface_label = "unit-test"

[repair]
enabled = true
max_attempts = 2
feedback = "diagnostic"

[budget]
max_model_calls = {budget}
'''


class CampaignPlanTests(TestCase):
    def test_plan_expands_cells_and_budget(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "campaign.toml"
            manifest.write_text(
                campaign_text(f'{sys.executable} -c "print(1)"'), encoding="utf-8"
            )
            plan = plan_campaign(manifest)
            self.assertEqual(plan["cell_count"], 1)
            self.assertEqual(plan["maximum_model_calls"], 2)
            self.assertEqual(plan["cells"][0]["cell"], "sample-01/reset_counter")

    def test_unknown_campaign_fields_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "campaign.toml"
            manifest.write_text(
                campaign_text("true") + "\nunsupported = true\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(CampaignError, "unsupported .*fields"):
                plan_campaign(manifest)


@skipUnless(HAS_TOOLS, "Yosys and Icarus Verilog are required")
class CampaignRunTests(TestCase):
    def test_repair_resume_and_exact_replay(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            task = taskpack_root("reset-release-v0.2") / "tasks/reset_counter"
            unsafe = (task / "reference-unsafe.sv").read_text(encoding="utf-8")
            safe = (task / "reference-safe.sv").read_text(encoding="utf-8")
            generator = root / "generator.py"
            generator.write_text(
                "import base64, sys\n"
                "prompt = sys.stdin.read()\n"
                f"unsafe = base64.b64decode({base64.b64encode(unsafe.encode()).decode()!r}).decode()\n"
                f"safe = base64.b64decode({base64.b64encode(safe.encode()).decode()!r}).decode()\n"
                "print(safe if 'Evaluation feedback' in prompt else unsafe)\n",
                encoding="utf-8",
            )
            manifest = root / "source-campaign.toml"
            manifest.write_text(
                campaign_text(
                    f"{shlex.quote(sys.executable)} {shlex.quote(str(generator))}"
                ),
                encoding="utf-8",
            )
            output = root / "run"
            summary = run_campaign(manifest, output)
            self.assertEqual(summary["model_calls"], 2)
            self.assertEqual(summary["repair_attempts"], 1)
            self.assertEqual(summary["closed_cells"], 1)
            self.assertEqual(summary["contract_statuses"], {"closed": 1, "open": 1})

            events = [
                json.loads(line)
                for line in (output / "campaign-ledger.jsonl").read_text().splitlines()
            ]
            attempts = [item for item in events if item["event"] == "attempt_completed"]
            self.assertEqual([item["phase"] for item in attempts], ["initial", "repair"])
            self.assertNotEqual(attempts[0]["seed"], attempts[1]["seed"])
            self.assertEqual(attempts[0]["contract_status"], "open")
            self.assertEqual(attempts[1]["contract_status"], "closed")
            self.assertTrue(all(item["record_sha256"] for item in events))
            self.assertEqual(resume_campaign(output)["model_calls"], 2)

            replay = replay_campaign(
                output, cell="sample-01/reset_counter", attempt=2
            )
            self.assertTrue(replay["result_matches"])
            self.assertTrue((output / replay["report_path"]).is_file())

    def test_model_call_budget_stops_before_unfunded_repair(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            task = taskpack_root("reset-release-v0.2") / "tasks/reset_counter"
            unsafe = (task / "reference-unsafe.sv").read_text(encoding="utf-8")
            encoded = base64.b64encode(unsafe.encode()).decode()
            command = (
                f'{sys.executable} -c "import base64; '
                f"print(base64.b64decode('{encoded}').decode())\""
            )
            manifest = root / "campaign.toml"
            manifest.write_text(campaign_text(command, budget=1), encoding="utf-8")
            summary = run_campaign(manifest, root / "run")
            self.assertEqual(summary["model_calls"], 1)
            self.assertEqual(summary["completed_cells"], 0)
            self.assertEqual(summary["stopped_reason"], "model_call_budget")
