from importlib.util import find_spec
from pathlib import Path
from subprocess import CompletedProcess
from unittest import TestCase, skipIf, skipUnless
from unittest.mock import patch

from svgap.backends.base import BackendUnavailable
from svgap.backends.registry import (
    BackendError,
    available_backends,
    load_backend,
    unavailable_backends,
)
from svgap.backends.lint_verible import VeribleLintBackend
from svgap.backends.lint_verilator import VerilatorLintBackend
from svgap.manifest import load_manifest

HAS_NAJAEDA = find_spec("najaeda") is not None


class BackendRegistryTests(TestCase):
    def test_builtin_backend_is_discoverable(self) -> None:
        self.assertIn("reference-yosys", available_backends())
        self.assertEqual(load_backend("reference-yosys").name, "reference-yosys")
        self.assertEqual(load_backend("formal-yosys").name, "formal-yosys")
        self.assertEqual(
            load_backend("equivalence-yosys").name, "equivalence-yosys"
        )
        self.assertIn("lint-verilator", available_backends())
        self.assertIn("lint-verible", available_backends())

    def test_verilator_warnings_are_evidence_not_structural_failure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(root / "examples/level_crossing/safe/manifest.toml")
        runs = [
            CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="%Warning-WIDTH: design.sv:1: width differs\n",
            ),
            CompletedProcess(args=[], returncode=0, stdout="Verilator 5.050\n", stderr=""),
        ]
        with (
            patch(
                "svgap.backends.lint_verilator.shutil.which",
                return_value="/tool/verilator",
            ),
            patch(
                "svgap.backends.lint_verilator.subprocess.run", side_effect=runs
            ),
        ):
            result = VerilatorLintBackend().check(manifest)
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.findings[0].rule_id, "LINT-VERILATOR-WIDTH")
        self.assertEqual(result.findings[0].severity, "warning")

    def test_verible_style_diagnostics_are_nonstructural_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(root / "examples/level_crossing/safe/manifest.toml")
        runs = [
            CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="design.sv:1:8: module name style [module-filename]\n",
            ),
            CompletedProcess(args=[], returncode=0, stdout="v0.0-test\n", stderr=""),
        ]
        with (
            patch(
                "svgap.backends.lint_verible.shutil.which",
                return_value="/tool/verible-verilog-lint",
            ),
            patch("svgap.backends.lint_verible.subprocess.run", side_effect=runs),
        ):
            result = VeribleLintBackend().check(manifest)
        self.assertEqual(result.status, "pass")
        self.assertEqual(
            result.findings[0].rule_id, "LINT-VERIBLE-MODULE-FILENAME"
        )

    def test_unknown_backend_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(BackendError, "available"):
            load_backend("missing-backend")

    @skipUnless(HAS_NAJAEDA, "optional naja extra is not installed")
    def test_reference_naja_backend_is_discoverable(self) -> None:
        # Capability probe for the najaeda structural backend: it registers via
        # the svgap.backends entry point and loads to its own instance.
        self.assertIn("reference-naja", available_backends())
        backend = load_backend("reference-naja")
        self.assertEqual(backend.name, "reference-naja")
        self.assertEqual(type(backend).__name__, "ReferenceNajaBackend")
        self.assertTrue(callable(getattr(backend, "check", None)))

    @skipIf(HAS_NAJAEDA, "najaeda is installed; the unavailable path cannot fire")
    def test_reference_naja_without_extra_is_unavailable_not_broken(self) -> None:
        # Without the optional extra the backend is neither discoverable nor a
        # plugin error: it is reported as unavailable with an install hint, and
        # loading it names the exact command to run.
        self.assertNotIn("reference-naja", available_backends())
        self.assertIn("pip install 'svgap[naja]'", unavailable_backends().get("reference-naja", ""))
        with self.assertRaisesRegex(BackendError, r"svgap\[naja\]"):
            load_backend("reference-naja")

    def test_backend_unavailable_is_classified_not_an_error(self) -> None:
        # A BackendUnavailable raised at entry-point load time must land in the
        # unavailable map (with its hint preserved), never in the errors map.
        class FakeEntryPoint:
            name = "fake-optional"

            def load(self):
                raise BackendUnavailable("install it with: pip install 'svgap[fake]'")

        with patch(
            "svgap.backends.registry.entry_points", return_value=[FakeEntryPoint()]
        ):
            self.assertNotIn("fake-optional", available_backends())
            self.assertEqual(
                unavailable_backends(),
                {"fake-optional": "install it with: pip install 'svgap[fake]'"},
            )
            with self.assertRaisesRegex(BackendError, r"svgap\[fake\]"):
                load_backend("fake-optional")
