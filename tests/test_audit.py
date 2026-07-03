from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.audit import (
    classify_task,
    is_clock_port,
    parse_markdown_inputs,
    parse_rtllm_inputs,
    parse_verilog_inputs,
)


class AuditTests(TestCase):
    def test_clock_port_names_exclude_enables(self) -> None:
        self.assertTrue(is_clock_port("clock"))
        self.assertTrue(is_clock_port("clk2"))
        self.assertTrue(is_clock_port("dst_clk"))
        self.assertTrue(is_clock_port("aclk"))
        self.assertTrue(is_clock_port("m_axis_aclk"))
        self.assertTrue(is_clock_port("clockA"))
        self.assertFalse(is_clock_port("clk_en"))

    def test_rtllm_input_block(self) -> None:
        text = """Input ports:
        clk_a: source clock
        clk_b: destination clock
        arstn: active-low reset
        data: input data
        Output ports:
        q: output
        """
        self.assertEqual(parse_rtllm_inputs(text), ["clk_a", "clk_b", "arstn", "data"])

    def test_markdown_input_table(self) -> None:
        text = """### Inputs
| Name | Width | Description |
|---|---|---|
| `src_clk` | 1 | source clock |
| `dst_clk` | 1 | destination clock |

### Outputs
| Name | Width | Description |
"""
        self.assertEqual(parse_markdown_inputs(text), ["src_clk", "dst_clk"])

    def test_markdown_bullet_inputs_stop_before_nested_modules(self) -> None:
        text = """**Input signals:**
- `clock`: top clock
- `rst`: reset

**Output signals:**
- `q`: output

Later nested module input clk should not be part of the top interface.
"""
        self.assertEqual(parse_markdown_inputs(text), ["clock", "rst"])

    def test_verilog_comments_do_not_create_ports(self) -> None:
        text = """module demo(
  input logic clk, // Input clock
  input logic system_clk, // Input system clock
  input logic rst
);
endmodule
"""
        self.assertEqual(parse_verilog_inputs(text), ["clk", "system_clk", "rst"])

    def test_verilog_comma_declared_inputs_are_all_preserved(self) -> None:
        text = """module demo(
  input logic src_clk, dst_clk,
  input logic rst_n,
  output logic q
);
endmodule
"""
        self.assertEqual(parse_verilog_inputs(text), ["src_clk", "dst_clk", "rst_n"])

    def test_multiclock_task_is_flagged_for_review(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            task = classify_task(
                task_id="sync",
                specification=Path("design_description.txt"),
                text="Synchronize data from asynchronous clk_a to clk_b.",
                input_ports=("clk_a", "clk_b", "arstn"),
                functional_oracle=True,
                task_root=root,
                constraint_candidates=(),
            )
        self.assertTrue(task.multi_clock)
        self.assertTrue(task.structural_risk_exposed)
        self.assertTrue(task.intent_sufficient_for_reference_audit)
        self.assertTrue(task.manual_review)
        self.assertFalse(task.natively_structurally_scored)
