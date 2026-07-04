from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from svgap.adjudication import (
    InstrumenterUnavailable,
    MockPrerecordedInstrumenter,
    ResetReleaseSkewInstrumenter,
    TraceError,
    adjudicate_prerecorded,
    compare_traces,
    derive_seed_bits,
    load_trace,
    run_calibration_suite,
    trace_from_dict,
)
from svgap.cli import main


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples/adjudication_calibration"


class AdjudicationTests(TestCase):
    def test_calibration_suite_covers_all_three_verdicts(self) -> None:
        result = run_calibration_suite(FIXTURES / "suite.json", max_shift=1)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            {item["actual"] for item in result["cases"]},
            {"hazard_demonstrated", "no_divergence_observed", "inconclusive"},
        )

    def test_global_shift_requires_equal_comparison_windows(self) -> None:
        golden = load_trace(FIXTURES / "golden.json")
        shifted = load_trace(FIXTURES / "no-divergence.json")
        self.assertTrue(compare_traces(golden, shifted, max_shift=1).equivalent)
        truncated = shifted.to_dict()
        truncated["samples"] = truncated["samples"][:-1]
        result = compare_traces(golden, trace_from_dict(truncated), max_shift=1)
        self.assertFalse(result.equivalent)

    def test_divergence_is_reproducible(self) -> None:
        golden = load_trace(FIXTURES / "golden.json")
        divergent = load_trace(FIXTURES / "divergence.json")
        result = adjudicate_prerecorded(
            candidate_id="fixture",
            rule_id="FIXTURE-001",
            golden=golden,
            instrumenter=MockPrerecordedInstrumenter({7: divergent}),
            seeds=[7],
            semantics_name="fixture-comparison",
            semantics_version="1.0",
            calibration_status="pass",
            calibration_suite_digest="sha256:fixture",
        )
        self.assertEqual(result["verdict"], "hazard_demonstrated")
        self.assertEqual(result["reproducer"]["seed"], 7)
        self.assertEqual(result["reproducer"]["first_divergence"]["signal"], "count")

    def test_seed_derivation_is_deterministic_and_candidate_bound(self) -> None:
        first = derive_seed_bits("study", "candidate-a", 4, 128)
        self.assertEqual(first, derive_seed_bits("study", "candidate-a", 4, 128))
        self.assertNotEqual(first, derive_seed_bits("study", "candidate-b", 4, 128))

    def test_trace_rejects_empty_values(self) -> None:
        payload = load_trace(FIXTURES / "golden.json").to_dict()
        payload["samples"][0]["values"]["count"] = ""
        with self.assertRaisesRegex(TraceError, "nonempty"):
            trace_from_dict(payload)

    def test_real_instrumenter_is_an_empty_blocked_capability_marker(self) -> None:
        with self.assertRaisesRegex(
            InstrumenterUnavailable, "BLOCKED_PENDING_PATENT_AND_EMPLOYER_REVIEW"
        ):
            ResetReleaseSkewInstrumenter().trace_for_seed(0)
        self.assertEqual(
            main(["adjudicate", "--instrumenter", "reset-release-skew"]), 4
        )

    def test_trace_normalize_cli(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "trace.csv"
            source.write_text(
                "cycle,clock,signal,value\n0,clk,count,0\n1,clk,count,1\n",
                encoding="utf-8",
            )
            output = root / "trace.json"
            code = main(
                [
                    "trace-normalize",
                    str(source),
                    "--trace-id",
                    "fixture",
                    "--candidate-digest",
                    "sha256:fixture",
                    "--observer",
                    "fixture",
                    "--observer-version",
                    "1",
                    "--sampling",
                    "posedge",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text())["signals"], ["count"])
