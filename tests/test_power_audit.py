from pathlib import Path
from unittest import TestCase

from svgap.power_audit import classify_power_on_task


class PowerOnAuditTests(TestCase):
    def classify(self, specification: str, harness: str = ""):
        return classify_power_on_task(
            task_id="example",
            specification=Path("prompt.txt"),
            specification_text=specification,
            harness_text=harness,
            input_ports=("clk", "rst_n", "data"),
            functional_oracle=True,
        )

    def test_reset_pin_and_output_value_do_not_imply_comprehensive_coverage(self):
        task = self.classify(
            "On reset, output valid must be zero. Then accept data on each clock."
        )
        self.assertTrue(task.sequential_task)
        self.assertTrue(task.reset_behavior_specified)
        self.assertFalse(task.comprehensive_reset_coverage_required)
        self.assertFalse(task.intent_sufficient_for_ref_xprop_001)

    def test_all_operational_state_requirement_is_sufficient(self):
        task = self.classify(
            "On reset, clear every state register. Accept data on each clock."
        )
        self.assertTrue(task.comprehensive_reset_coverage_required)
        self.assertTrue(task.intent_sufficient_for_ref_xprop_001)

    def test_generic_case_inequality_is_not_native_x_scoring(self):
        task = self.classify("A clocked register.", "if (dut.q !== expected) fail();")
        self.assertFalse(task.native_unknown_initial_state_scoring)

    def test_explicit_unknown_and_random_initialization_are_native_scoring(self):
        unknown = self.classify("A clocked register.", "assert (!$isunknown(dut.q));")
        random_init = self.classify(
            "A clocked register.", "run_with_random_initial_state(dut);"
        )
        self.assertTrue(unknown.native_unknown_initial_state_scoring)
        self.assertTrue(random_init.native_unknown_initial_state_scoring)

    def test_explicit_x_comparison_is_native_scoring(self):
        task = self.classify("A clocked register.", "if (dut.q === 1'bx) fail();")
        self.assertTrue(task.native_unknown_initial_state_scoring)

    def test_random_input_values_are_not_random_initial_state(self):
        task = self.classify(
            "A clocked register.", "# Load some initial random values into inputs"
        )
        self.assertFalse(task.native_unknown_initial_state_scoring)

    def test_fsm_initial_state_without_reset_is_not_power_on_intent(self):
        task = self.classify("IDLE is the initial state of the state machine.")
        self.assertFalse(task.power_on_or_initial_state_language_explicit)

    def test_generic_all_bits_cleared_is_not_comprehensive_reset(self):
        task = self.classify("The pending register has all bits cleared by software.")
        self.assertFalse(task.comprehensive_reset_coverage_required)

    def test_uninitialized_register_prohibition_is_not_reset_intent(self):
        task = self.classify(
            "Perform a lint review and address the uninitialized register issue."
        )
        self.assertTrue(task.uninitialized_state_prohibited)
        self.assertFalse(task.intent_sufficient_for_ref_xprop_001)
