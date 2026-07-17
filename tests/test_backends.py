from importlib.util import find_spec
from unittest import TestCase, skipIf, skipUnless
from unittest.mock import patch

from svgap.backends.base import BackendUnavailable
from svgap.backends.registry import (
    BackendError,
    available_backends,
    load_backend,
    unavailable_backends,
)

HAS_NAJAEDA = find_spec("najaeda") is not None


class BackendRegistryTests(TestCase):
    def test_builtin_backend_is_discoverable(self) -> None:
        self.assertIn("reference-yosys", available_backends())
        self.assertEqual(load_backend("reference-yosys").name, "reference-yosys")

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
