"""Acceptance tests for the najaeda-backed structural oracle.

These mirror the ExampleTests contract in test_examples.py but drive
ReferenceNajaBackend directly. The backend is an in-process, structural-only
checker built on najaeda's bundled slang frontend (no separately installed
Yosys/Icarus binaries), so none of these need the HAS_TOOLS gate that
test_examples.py uses. They do need the optional naja extra; without it the
module import below raises and the whole file is reported as skipped.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest import SkipTest, TestCase, skipUnless

from svgap.backends.base import BackendUnavailable

try:
    from svgap.backends.reference_naja import ReferenceNajaBackend
except BackendUnavailable as exc:  # the optional naja extra is not installed
    raise SkipTest(f"reference-naja backend is unavailable: {exc}") from exc
from svgap.manifest import load_manifest
from svgap.model import CrossingIntent, EvaluationReport, FunctionalResult, Manifest
from svgap.validation import validate_report_payload


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/reset-replication-v0.1"

EXPECTED_RULES = {
    "level_crossing": "REF-CDC-001",
    "comb_crossing": "REF-CDC-002",
    "gray_counter": "REF-CDC-003",
    "reset_release": "REF-RDC-001",
    "power_on_x": "REF-XPROP-001",
}


class ReferenceNajaExampleTests(TestCase):
    def test_paired_examples(self) -> None:
        for family, expected_rule in EXPECTED_RULES.items():
            with self.subTest(family=family, variant="unsafe"):
                unsafe = load_manifest(ROOT / f"examples/{family}/unsafe/manifest.toml")
                result = ReferenceNajaBackend().check(unsafe)
                self.assertEqual(result.status, "fail", result)
                self.assertIn(
                    expected_rule, {finding.rule_id for finding in result.findings}
                )
            with self.subTest(family=family, variant="safe"):
                safe = load_manifest(ROOT / f"examples/{family}/safe/manifest.toml")
                result = ReferenceNajaBackend().check(safe)
                self.assertEqual(result.status, "pass", result)
                self.assertEqual(result.findings, [])

    def test_gray_declaration_does_not_waive_binary_source(self) -> None:
        # A declared gray protocol must not waive a multi-bit crossing whose
        # source register is a plain binary counter (no gray-encoding logic in
        # its fanin cone).
        manifest = load_manifest(ROOT / "examples/gray_counter/unsafe/manifest.toml")
        manifest.crossings.append(
            CrossingIntent(source="src_count", destination="dst_count", protocol="gray")
        )
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "fail")
        self.assertIn("REF-CDC-003", {finding.rule_id for finding in result.findings})

    def test_wildcard_gray_declaration_is_name_independent(self) -> None:
        safe = load_manifest(ROOT / "examples/gray_counter/safe/manifest.toml")
        safe.crossings.clear()
        safe.crossings.append(CrossingIntent(source="*", destination="*", protocol="gray"))
        self.assertEqual(ReferenceNajaBackend().check(safe).status, "pass")

        unsafe = load_manifest(ROOT / "examples/gray_counter/unsafe/manifest.toml")
        unsafe.crossings.append(
            CrossingIntent(source="*", destination="*", protocol="gray")
        )
        result = ReferenceNajaBackend().check(unsafe)
        self.assertEqual(result.status, "fail", result)
        self.assertIn("REF-CDC-003", {finding.rule_id for finding in result.findings})


class ReferenceNajaDiagnosticTests(TestCase):
    def test_new_intent_classes_abstain_instead_of_false_pass(self) -> None:
        manifest = load_manifest(ROOT / "examples/pulse_crossing/safe/manifest.toml")
        backend = ReferenceNajaBackend()
        result = backend.check(manifest)
        self.assertEqual(result.status, "unknown", result)
        self.assertIn("cdc-pulse", " ".join(result.diagnostics))
        self.assertIn(
            "cdc-pulse", backend.coverage(manifest)["unsupported_intent_features"]
        )

    def test_missing_intent_is_unknown(self) -> None:
        # No declared clock or reset intent: the backend must abstain
        # (``unknown``) via its diagnostics path, never silently ``pass``.
        manifest = load_manifest(ROOT / "examples/level_crossing/unsafe/manifest.toml")
        manifest.clocks.clear()
        manifest.resets.clear()
        manifest.asynchronous_groups.clear()
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "unknown")
        self.assertIn("no clock or reset intent", " ".join(result.diagnostics))

    def test_power_on_rule_reports_output_evidence(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        result = ReferenceNajaBackend().check(manifest)
        finding = next(item for item in result.findings if item.rule_id == "REF-XPROP-001")
        self.assertIn("data_out", finding.evidence["output_signals"])

    def test_power_on_rule_abstains_without_declared_reset(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        manifest.resets.clear()
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "unknown")
        self.assertIn("no reset was declared", " ".join(result.diagnostics))

    def test_power_on_rule_is_disabled_when_intent_is_unspecified(self) -> None:
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        manifest.power_on = "unspecified"
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "pass", result)

    def test_power_on_intent_with_init_attributes_is_unknown(self) -> None:
        # init_attributes_are_power_on relies on netlist "init" attributes this
        # backend does not model; it must abstain rather than guess.
        manifest = load_manifest(ROOT / "examples/power_on_x/unsafe/manifest.toml")
        manifest.init_attributes_are_power_on = True
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "unknown", result)
        self.assertEqual(result.findings, [])
        self.assertIn("init_attributes_are_power_on", " ".join(result.diagnostics))

    def test_undeclared_async_group_names_are_inconclusive(self) -> None:
        manifest = load_manifest(ROOT / "examples/level_crossing/unsafe/manifest.toml")
        manifest.asynchronous_groups = [["typo_source"], ["typo_destination"]]
        result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "unknown")
        self.assertIn("undeclared clocks", " ".join(result.diagnostics))

    def test_unparseable_source_is_tool_error(self) -> None:
        # An existing but syntactically invalid source must surface as
        # ``tool_error`` (the except branch in check()), not ``fail``/``pass``.
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "broken.sv"
            source.write_text("module oops( not valid systemverilog !!!\n")
            manifest = _bare_manifest(Path(tmp), top="oops", sources=[source])
            result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "tool_error")
        self.assertTrue(result.diagnostics)
        self.assertIn("elaborate", result.diagnostics[0])

    def test_missing_source_is_tool_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = _bare_manifest(
                Path(tmp), top="oops", sources=[Path(tmp) / "does_not_exist.sv"]
            )
            result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "tool_error")


class ReferenceNajaSchemaTests(TestCase):
    def test_result_conforms_to_report_schema(self) -> None:
        # A structural result must slot into the schema-v1 evaluation report
        # that svgap.validation guards at the CLI and plugin boundaries.
        manifest = load_manifest(ROOT / "examples/level_crossing/unsafe/manifest.toml")
        structural = ReferenceNajaBackend().check(manifest)
        report = EvaluationReport(
            schema_version="1.0",
            candidate_id=manifest.candidate_id,
            manifest=str(manifest.path),
            functional=FunctionalResult(status="not_run"),
            structural=structural,
            gap_member=False,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        payload = json.loads(json.dumps(report.to_dict()))
        # Must not raise ReportValidationError.
        self.assertIs(validate_report_payload(payload), payload)

    def test_findings_evidence_is_json_serializable(self) -> None:
        manifest = load_manifest(ROOT / "examples/comb_crossing/unsafe/manifest.toml")
        structural = ReferenceNajaBackend().check(manifest)
        # Round-trips through JSON without a custom encoder.
        json.dumps([asdict(finding) for finding in structural.findings])
        self.assertTrue(structural.findings)


# A single-clock design whose next-state logic uses the case-equality operator
# `===`, which naja's frontend lowers as a 2-state comparison and reports as
# the `case_comparison_two_state` elaboration warning. Structurally clean:
# one declared clock, no resets, no crossings.
_CASE_EQUALITY_SOURCE = """module case_eq (
    input  logic       clk,
    input  logic [1:0] sel,
    input  logic       a,
    output logic       y
);
    always_ff @(posedge clk) begin
        if (sel === 2'b01) y <= a;
    end
endmodule
"""


def _clock_only_manifest(directory: Path, *, top: str, sources: list[Path]) -> Manifest:
    from svgap.model import ClockIntent

    return Manifest(
        path=directory / "manifest.toml",
        schema_version="1.0",
        candidate_id=top,
        top=top,
        sources=sources,
        functional_commands=[],
        functional_import=None,
        clocks=[ClockIntent(name="core", port="clk")],
        asynchronous_groups=[],
        resets=[],
        crossings=[],
        power_on="unspecified",
        init_attributes_are_power_on=False,
        backend="reference-naja",
        report_path=directory / "report.json",
    )


class ReferenceNajaSideEffectTests(TestCase):
    """Backend runs must not create files in the caller's working directory,
    and relevant frontend warnings must reach the CheckResult as
    warning-severity findings (which never change the verdict)."""

    def test_no_files_created_in_working_directory(self) -> None:
        # Previously each run left naja_sv_diagnostics.log (and, under some
        # najaeda versions, naja_perf.log) in the caller's cwd.
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as scratch_cwd,
        ):
            source = Path(tmp) / "case_eq.sv"
            source.write_text(_CASE_EQUALITY_SOURCE)
            manifest = _clock_only_manifest(Path(tmp), top="case_eq", sources=[source])
            original_cwd = os.getcwd()
            os.chdir(scratch_cwd)
            try:
                result = ReferenceNajaBackend().check(manifest)
                self.assertEqual(os.listdir(scratch_cwd), [])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(result.status, "pass", result)

    def test_frontend_warnings_reach_the_check_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "case_eq.sv"
            source.write_text(_CASE_EQUALITY_SOURCE)
            manifest = _clock_only_manifest(Path(tmp), top="case_eq", sources=[source])
            result = ReferenceNajaBackend().check(manifest)
        warning_findings = [f for f in result.findings if f.severity == "warning"]
        self.assertTrue(warning_findings, result)
        finding = warning_findings[0]
        self.assertEqual(finding.rule_id, "REF-NAJA-FRONTEND-001")
        self.assertEqual(finding.evidence["code"], "case_comparison_two_state")
        self.assertIn("2-state", finding.message)
        # Normalized like every other source_location: relative to the
        # manifest directory, in file:line form.
        self.assertRegex(finding.evidence["source_location"], r"^case_eq\.sv:\d+$")
        # Warning findings are informational: the verdict stays pass, and no
        # error finding is fabricated.
        self.assertEqual(result.status, "pass", result)
        self.assertEqual([f for f in result.findings if f.severity == "error"], [])


# A packed-vector reset synchronizer, self-contained and mirroring the shape of
# the artifact's openai-frontier-a candidates: a `logic [1:0]` first stage that
# shifts a constant `1` up under an async-assert reset, feeding a downstream
# register that releases on the synchronized bit. naja lowers `reset_sync` as one
# `..._dffrn__w2` instance; the ported wide-vector fallback must recognize it so
# this passes (its own register is not a raw async-reset consumer).
_SAFE_WIDE_SYNC = """module wide_reset_sync (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       enable,
    output logic [3:0] count
);
    logic [1:0] reset_sync;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) reset_sync <= 2'b00;
        else        reset_sync <= {reset_sync[0], 1'b1};
    end
    always_ff @(posedge clk or negedge reset_sync[1]) begin
        if (!reset_sync[1]) count <= 0;
        else if (enable)    count <= count + 1'b1;
    end
endmodule
"""

# An ordinary wide async-reset *data* register (not a shift-to-constant chain):
# its D bits are external data, so it must still fail REF-RDC-001 under a declared
# synchronous deassertion. This is the over-acceptance guard for the wide-vector
# recognizer -- it must not wave through any packed register that merely has an
# async reset.
_UNSAFE_WIDE_RAW = """module wide_raw_reset (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [3:0] data_in,
    output logic [3:0] data_out
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) data_out <= 4'b0000;
        else        data_out <= data_in;
    end
endmodule
"""


def _reset_manifest(directory: Path, *, top: str, sources: list[Path]) -> Manifest:
    """A manifest with a single core clock and one async-assert / sync-deassert
    active-low reset, the intent the reset-release witnesses are checked under."""
    from svgap.model import ClockIntent, ResetIntent

    return Manifest(
        path=directory / "manifest.toml",
        schema_version="1.0",
        candidate_id=top,
        top=top,
        sources=sources,
        functional_commands=[],
        functional_import=None,
        clocks=[ClockIntent(name="core", port="clk")],
        asynchronous_groups=[],
        resets=[
            ResetIntent(
                name="power_on_reset",
                port="rst_n",
                active="low",
                assertion="async",
                deassertion="sync",
            )
        ],
        crossings=[],
        power_on="unspecified",
        init_attributes_are_power_on=False,
        backend="reference-naja",
        report_path=directory / "report.json",
    )


class ReferenceNajaWideVectorResetTests(TestCase):
    """The wide packed-vector reset-synchronizer form (naja lowers it as one
    multi-bit `..._dffrn__wN` instance), the ported analog of Yosys's wide
    vector-shift $adff fallback."""

    @skipUnless(ARTIFACT.is_dir(), "frozen reset-replication artifact is required")
    def test_artifact_packed_vector_synchronizer_passes(self) -> None:
        # The real openai-frontier-a candidate whose packed-vector synchronizer
        # was the single false-positive class before the fallback was ported.
        directory = (
            ARTIFACT
            / "candidates"
            / "openai-frontier-a--sample-01"
            / "reset_config"
        )
        result = ReferenceNajaBackend().check(load_manifest(directory / "manifest.toml"))
        self.assertEqual(result.status, "pass", result)
        # Frontend warnings may surface as warning-severity findings on real
        # artifact candidates; the verdict contract is about error findings.
        self.assertEqual(
            [f for f in result.findings if f.severity == "error"], []
        )

    def test_wide_vector_synchronizer_safe_witness_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "wide_reset_sync.sv"
            source.write_text(_SAFE_WIDE_SYNC)
            manifest = _reset_manifest(Path(tmp), top="wide_reset_sync", sources=[source])
            result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "pass", result)
        self.assertEqual(result.findings, [])

    def test_wide_raw_reset_data_register_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "wide_raw_reset.sv"
            source.write_text(_UNSAFE_WIDE_RAW)
            manifest = _reset_manifest(Path(tmp), top="wide_raw_reset", sources=[source])
            result = ReferenceNajaBackend().check(manifest)
        self.assertEqual(result.status, "fail", result)
        self.assertEqual(
            {finding.rule_id for finding in result.findings}, {"REF-RDC-001"}
        )


# Observed cross-oracle agreement against the frozen 72-candidate
# reset-replication artifact (reference-yosys is the frozen verdict): 72/72,
# rule-for-rule (57 mutual passes, 15 mutual REF-RDC-001 fails). This was 54/72
# before the wide-vector reset-synchronizer fallback was ported into
# _reset_synchronizer_regs; the 18 former disagreements were all a single
# false-positive class -- a packed-vector reset synchronizer that naja lowers
# as one multi-bit register -- now recognized (see
# docs/cross-oracle-naja-result.md). With the gap closed there is no residual
# disagreement, and the test below asserts exactly that.
EXPECTED_MIN_AGREEMENTS = 72


@skipUnless(ARTIFACT.is_dir(), "frozen reset-replication artifact is required")
class ReferenceNajaCrossOracleTests(TestCase):
    def test_agreement_and_disagreement_shape(self) -> None:
        index = json.loads((ARTIFACT / "manifest.json").read_text(encoding="utf-8"))
        candidates = index["candidates"]
        agreements = 0
        disagreements = []
        for item in candidates:
            directory = ARTIFACT / "candidates" / item["run_id"] / item["task_id"]
            frozen = json.loads(
                (directory / "report.json").read_text(encoding="utf-8")
            )["structural"]
            frozen_status = frozen["status"]
            frozen_rules = sorted({f["rule_id"] for f in frozen["findings"]})

            result = ReferenceNajaBackend().check(load_manifest(directory / "manifest.toml"))
            # The frozen verdicts carry only error-severity findings; naja's
            # warning-severity frontend findings (REF-NAJA-FRONTEND-001) are
            # informational and excluded from the agreement comparison.
            naja_rules = sorted(
                {f.rule_id for f in result.findings if f.severity == "error"}
            )
            # The frozen verdict is reference-yosys, never reference-naja: a
            # fresh check must bypass manifest.backend, which we do by calling
            # the backend directly rather than through load_backend.
            if result.status == frozen_status and naja_rules == frozen_rules:
                agreements += 1
            else:
                disagreements.append(
                    (item["run_id"], item["task_id"], frozen_status, result.status, naja_rules)
                )

        self.assertGreaterEqual(agreements, EXPECTED_MIN_AGREEMENTS)
        # The wide-vector reset-synchronizer fallback is now ported, so the two
        # oracles agree rule-for-rule on every candidate: no residual
        # disagreement remains.
        self.assertEqual(disagreements, [])


def _bare_manifest(directory: Path, *, top: str, sources: list[Path]) -> Manifest:
    return Manifest(
        path=directory / "manifest.toml",
        schema_version="1.0",
        candidate_id=top,
        top=top,
        sources=sources,
        functional_commands=[],
        functional_import=None,
        clocks=[],
        asynchronous_groups=[],
        resets=[],
        crossings=[],
        power_on="unspecified",
        init_attributes_are_power_on=False,
        backend="reference-naja",
        report_path=directory / "report.json",
    )
