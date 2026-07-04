from unittest import TestCase

from svgap.backends.registry import BackendError, available_backends, load_backend


class BackendRegistryTests(TestCase):
    def test_builtin_backend_is_discoverable(self) -> None:
        self.assertIn("reference-yosys", available_backends())
        self.assertEqual(load_backend("reference-yosys").name, "reference-yosys")

    def test_unknown_backend_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(BackendError, "available"):
            load_backend("missing-backend")
