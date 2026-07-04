#!/usr/bin/env python3
"""Build the immutable reset-replication v0.2 taskpack from reviewed inputs."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from svgap.provenance import canonical_tree_digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "taskpacks/reset-replication-v0.1/tasks"
DEFAULT_OUTPUT = ROOT / "taskpacks/reset-replication-v0.2"


TASKS = {
    "reset_config": {
        "reset": "global_reset_n",
        "header": "input logic clk, input logic global_reset_n,\n                    input logic write_en, input logic [3:0] config_in,\n                    output logic [3:0] config_out",
        "body": "if (!RESET) config_out <= 4'h0;\n    else if (write_en) config_out <= config_in;",
    },
    "reset_counter": {
        "reset": "arst_n",
        "header": "input logic clk, input logic arst_n, input logic enable,\n                     output logic [7:0] count",
        "body": "if (!RESET) count <= 8'h00;\n    else if (enable) count <= count + 1'b1;",
    },
    "reset_credits": {
        "reset": "async_reset_n",
        "header": "input logic clk, input logic async_reset_n,\n                     input logic consume, input logic replenish,\n                     output logic [3:0] credits",
        "body": "if (!RESET) credits <= 4'h0;\n    else if (replenish && !consume) credits <= credits + 1'b1;\n    else if (consume && !replenish && credits != 0) credits <= credits - 1'b1;",
    },
    "reset_events": {
        "reset": "ext_rst_n",
        "header": "input logic clk, input logic ext_rst_n, input logic event_valid,\n                    output logic [7:0] event_count",
        "body": "if (!RESET) event_count <= 8'h00;\n    else if (event_valid) event_count <= event_count + 1'b1;",
    },
    "reset_fsm": {
        "reset": "reset_n",
        "header": "input logic clk, input logic reset_n, input logic start,\n                 output logic busy, output logic done",
        "declarations": "logic [1:0] phase;",
        "body": """if (!RESET) begin
      phase <= 2'd0; busy <= 1'b0; done <= 1'b0;
    end else begin
      done <= 1'b0;
      case (phase)
        2'd0: if (start) begin phase <= 2'd1; busy <= 1'b1; end
        2'd1: phase <= 2'd2;
        2'd2: begin phase <= 2'd0; busy <= 1'b0; done <= 1'b1; end
        default: begin phase <= 2'd0; busy <= 1'b0; done <= 1'b0; end
      endcase
    end""",
    },
    "reset_status": {
        "reset": "rst_n",
        "header": "input logic clk, input logic rst_n, input logic set_fault,\n                    input logic clear_fault, output logic fault_latched",
        "body": "if (!RESET) fault_latched <= 1'b0;\n    else if (clear_fault) fault_latched <= 1'b0;\n    else if (set_fault) fault_latched <= 1'b1;",
    },
    "reset_timer": {
        "reset": "por_n",
        "header": "input logic clk, input logic por_n, input logic load,\n                   input logic [3:0] load_value, output logic expired",
        "declarations": "logic [3:0] remaining;",
        "body": """if (!RESET) begin
      remaining <= 4'h0; expired <= 1'b0;
    end else if (load) begin
      remaining <= load_value; expired <= (load_value == 0);
    end else if (remaining > 1) begin
      remaining <= remaining - 1'b1; expired <= 1'b0;
    end else if (remaining == 1) begin
      remaining <= 0; expired <= 1'b1;
    end""",
    },
    "reset_watchdog": {
        "reset": "system_rst_n",
        "header": "input logic clk, input logic system_rst_n, input logic kick,\n                      output logic timeout",
        "declarations": "logic [2:0] quiet_cycles;",
        "body": """if (!RESET) begin
      quiet_cycles <= 0; timeout <= 1'b0;
    end else if (kick) begin
      quiet_cycles <= 0; timeout <= 1'b0;
    end else if (quiet_cycles == 3) begin
      quiet_cycles <= quiet_cycles; timeout <= 1'b1;
    end else begin
      quiet_cycles <= quiet_cycles + 1'b1; timeout <= 1'b0;
    end""",
    },
}


TIMER_PROMPT = """Produce a production-oriented SystemVerilog implementation of:

```systemverilog
module reset_timer(input logic clk, input logic por_n, input logic load,
                   input logic [3:0] load_value, output logic expired);
```

Loading captures `load_value`; the timer counts down once per clock and asserts
`expired` when the count reaches zero. Both the internal count and `expired`
must reset to zero. `por_n` comes from an asynchronous power-on source.
Assertion is asynchronous, but the reset seen by functional sequential state
must be released synchronously to `clk`. The design must be portable
synthesizable RTL.

Output the module only.
"""


def render_reference(task_id: str, task: dict[str, str], safe: bool) -> str:
    raw_reset = task["reset"]
    declarations = task.get("declarations", "")
    reset_signal = "local_reset_n" if safe else raw_reset
    body = task["body"].replace("RESET", reset_signal)
    support = ""
    if safe:
        support = f"""logic reset_meta_n, reset_sync_n;
wire local_reset_n = {raw_reset} & reset_sync_n;

always_ff @(posedge clk or negedge {raw_reset}) begin
  if (!{raw_reset}) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

"""
    return f"""module {task_id}({task['header']});
{declarations}
{support}always_ff @(posedge clk or negedge {reset_signal}) begin
  {body}
end
endmodule
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    tasks_output = output / "tasks"
    for task_id, task in TASKS.items():
        source = SOURCE / task_id
        target = tasks_output / task_id
        target.mkdir(parents=True)
        shutil.copy2(source / "task.toml", target / "task.toml")
        shutil.copy2(source / "tb.sv", target / "tb.sv")
        prompt = TIMER_PROMPT if task_id == "reset_timer" else (source / "prompt.md").read_text()
        (target / "prompt.md").write_text(prompt, encoding="utf-8")
        (target / "reference-safe.sv").write_text(
            render_reference(task_id, task, True), encoding="utf-8"
        )
        (target / "reference-unsafe.sv").write_text(
            render_reference(task_id, task, False), encoding="utf-8"
        )
    (output / "README.md").write_text(
        """# Reset-release replication v0.2

This confirmatory taskpack preserves the eight behavior families from v0.1,
fixes the reset-timer output ambiguity, and adds executable safe and unsafe
reference implementations for every task. It tests the same `REF-RDC-001`
property; no new structural category is introduced.

The taskpack is a mechanism-demonstration instrument. Generation calls are
reported as calls, exact duplicate normalized outputs are disclosed, and no
result is interpreted as population prevalence or a model ranking.

`freeze.json` records a deterministic digest. Its repository commit and release
tag provide the external timestamp; the file does not call itself a
preregistration.
""",
        encoding="utf-8",
    )
    (output / "protocol.md").write_text(
        "# Reset-release replication v0.2 protocol\n\n## Research role\n\nThis taskpack tests whether the SV-Gap contract makes one recurring\nresearch-to-production mismatch explicit. It is a confirmatory mechanism\ndemonstration, not a prevalence study or model leaderboard.\n\n## Frozen unit\n\n- Eight task families.\n- One prompt, functional testbench, and declared reset intent per task.\n- One safe and one unsafe executable reference per task.\n- One structural property: `REF-RDC-001`.\n- No repair or candidate-dependent prompt changes.\n\nThe reference calibration must pass before generation: both references pass the\nfunctional test, the safe reference passes structurally, and the unsafe\nreference fails with `REF-RDC-001`.\n\n## Generation record\n\nBefore a run, publish or otherwise externally timestamp the taskpack digest and\nrecord:\n\n- exact requested model and provider interface version;\n- configuration parameters exposed by the provider;\n- number of independent calls per model-task cell;\n- tool-use and conversational-continuation policy;\n- generation start and completion timestamps; and\n- failures that occur before an RTL candidate is returned.\n\nDo not infer an unreported seed or resolved model identifier. Record unavailable\nfields as unavailable.\n\n## Outcomes\n\nThe primary demonstration outcome is the count of functionally accepted\ncandidates with a `REF-RDC-001` finding. Also report:\n\n- every functional and structural status;\n- counts by task and generation configuration;\n- exact duplicate normalized RTL outputs;\n- tool versions and taskpack/evaluator digests; and\n- candidate-level evidence for every structural finding.\n\nCalls are generation events, not independent draws from a universal\npopulation. Percentages may summarize this taskpack but must not be described\nas prevalence.\n\n## Comparison with v0.1\n\nKeep v0.1 immutable. Report v0.2 beside it and identify the material design\nchanges:\n\n- the timer prompt now specifies that both internal count and `expired` reset\n  to zero;\n- every task has executable safe and unsafe references;\n- reference calibration is an automated release gate; and\n- duplicate-output disclosure is part of the frozen analysis.\n\nDo not pool v0.1 and v0.2 into one rate. A stable result across versions is a\nreplication of the mechanism under two taskpack contracts, not a larger\npopulation sample.\n\n## Review\n\nAuthor inspection, synthetic review, independent expert review, or competing\nbackends may be attached as separate evidence layers. None is a prerequisite\nfor publishing the executable taskpack or its existential result. Any evidence\nlayer must identify its reviewer/oracle, version, blinding status, and scope.\n",
        encoding="utf-8",
    )
    digest = canonical_tree_digest(output, exclude_names={"freeze.json"})
    (output / "freeze.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "canonical_digest": digest,
                "digest_excludes": ["freeze.json"],
                "tasks": len(TASKS),
                "reference_variants_per_task": 2,
                "property": "REF-RDC-001",
                "status": "repository freeze candidate; external timestamp is the release tag",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"tasks       {len(TASKS)}")
    print(f"digest      {digest}")
    print(f"output      {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
