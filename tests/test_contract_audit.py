from pathlib import Path
from unittest import TestCase

from svgap.contract_audit import (
    ContractBenchmarkAudit,
    classify_contract_task,
    combined_contract_summary,
)


class ContractAuditTests(TestCase):
    def classify(self, specification: str, harness: str = "", names: tuple[str, ...] = ()):
        return classify_contract_task(
            task_id="fixture",
            specification=Path("prompt.txt"),
            specification_text=specification,
            harness_text=harness,
            harness_names=names,
            functional_oracle=True,
            public_reference_rtl=True,
        )

    def test_bounded_latency_without_property_is_visible_lower_bound(self) -> None:
        task = self.classify(
            "Assert done exactly two cycles after start.",
            "await RisingEdge(dut.clk); assert dut.done.value == 1",
        )
        self.assertTrue(task.bounded_temporal_contract)
        self.assertTrue(task.temporal_contract_explicit)
        self.assertTrue(task.finite_trace_temporal_scoring)
        self.assertTrue(task.temporal_contract_without_property_or_formal)
        self.assertFalse(task.native_temporal_assertion_scoring)

    def test_sva_and_formal_are_separate_from_finite_testing(self) -> None:
        task = self.classify(
            "Valid must remain asserted until ready.",
            "assert property (@(posedge clk) valid && !ready |=> $stable(data));\n"
            "sby -f protocol.sby",
            ("protocol.sby",),
        )
        self.assertTrue(task.persistence_temporal_contract)
        self.assertTrue(task.native_temporal_assertion_scoring)
        self.assertTrue(task.formal_temporal_scoring)
        self.assertFalse(task.temporal_contract_without_property_or_formal)

    def test_comment_word_until_is_not_sva_scoring(self) -> None:
        task = self.classify(
            "Use a ready/valid handshake.",
            "# Wait until the handshake\nawait RisingEdge(dut.clk)\nassert dut.ready.value",
        )
        self.assertTrue(task.protocol_or_ordering_contract)
        self.assertFalse(task.native_temporal_assertion_scoring)

    def test_equivalence_contract_requires_actual_equivalence_tool(self) -> None:
        task = self.classify(
            "Reduce cell area while preserving functional equivalence with the original.",
            "yosys -c synth.tcl",
        )
        self.assertTrue(task.synthesis_contract_explicit)
        self.assertTrue(task.equivalence_contract_explicit)
        self.assertTrue(task.synthesis_scoring)
        self.assertTrue(task.equivalence_contract_without_formal_equivalence)
        self.assertFalse(task.formal_equivalence_scoring)

    def test_eqy_is_formal_equivalence_scoring(self) -> None:
        task = self.classify(
            "Preserve the behavior of the reference design.",
            "eqy -f compare.eqy",
            ("compare.eqy",),
        )
        self.assertTrue(task.equivalence_contract_explicit)
        self.assertTrue(task.formal_equivalence_scoring)
        self.assertFalse(task.equivalence_contract_without_formal_equivalence)

    def test_generic_sequential_language_is_not_temporal_contract(self) -> None:
        task = self.classify("Implement a synchronous counter with a clock input.")
        self.assertFalse(task.temporal_contract_explicit)

    def test_combined_summary_reports_lower_bounds_not_just_raw_matches(self) -> None:
        temporal = self.classify(
            "Done must assert exactly two cycles after start.",
            "await RisingEdge(dut.clk); assert dut.done.value",
        )
        equivalence = self.classify(
            "Synthesize for reduced cell area while preserving functional equivalence.",
            "yosys -c synth.tcl",
        )
        summary = combined_contract_summary(
            (ContractBenchmarkAudit("fixture", "revision", (temporal, equivalence)),)
        )
        self.assertEqual(summary["temporal_property_gap_lower_bound"], 1)
        self.assertEqual(summary["synthesis_equivalence_gap_lower_bound"], 1)
