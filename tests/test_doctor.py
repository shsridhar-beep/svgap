import io
from unittest import TestCase
from unittest.mock import patch

from svgap.cli import doctor


class DoctorRemediationTests(TestCase):
    def run_missing(self, system: str) -> tuple[int, str]:
        output = io.StringIO()
        with (
            patch("svgap.cli.shutil.which", return_value=None),
            patch("svgap.cli.platform.system", return_value=system),
            patch("svgap.cli.discover_backends", return_value=({"reference-yosys": object()}, {})),
            patch("sys.stdout", output),
        ):
            code = doctor()
        return code, output.getvalue()

    def test_macos_missing_tools_print_install_and_container_paths(self) -> None:
        code, output = self.run_missing("Darwin")
        self.assertEqual(code, 1)
        self.assertIn("brew install yosys icarus-verilog", output)
        self.assertIn("docker run --rm ghcr.io/shsridhar-beep/svgap", output)
        self.assertIn("linux-install-and-doctor", output)

    def test_linux_missing_tools_print_supported_package_managers(self) -> None:
        code, output = self.run_missing("Linux")
        self.assertEqual(code, 1)
        self.assertIn("apt-get install -y yosys iverilog", output)
        self.assertIn("dnf install -y yosys iverilog", output)
        self.assertIn("pacman -S yosys iverilog", output)

    def test_windows_directs_users_to_supported_environment(self) -> None:
        code, output = self.run_missing("Windows")
        self.assertEqual(code, 1)
        self.assertIn("Docker Desktop or WSL2", output)

    def test_unavailable_optional_backend_is_informational_not_a_failure(self) -> None:
        # A backend whose optional extra is not installed prints an install
        # hint but must not fail doctor: the default install is healthy.
        output = io.StringIO()
        with (
            patch("svgap.cli.shutil.which", side_effect=lambda tool: f"/tools/{tool}"),
            patch("svgap.cli.subprocess.run") as run,
            patch(
                "svgap.cli.discover_backends",
                return_value=({"reference-yosys": object()}, {}),
            ),
            patch(
                "svgap.cli.unavailable_backends",
                return_value={"reference-naja": "install it with: pip install 'svgap[naja]'"},
            ),
            patch("sys.stdout", output),
        ):
            run.return_value.stdout = "Yosys 0.66"
            code = doctor()
        self.assertEqual(code, 0)
        self.assertIn("optional   reference-naja", output.getvalue())
        self.assertIn("pip install 'svgap[naja]'", output.getvalue())

    def test_plugin_error_remains_a_failure_when_tools_exist(self) -> None:
        output = io.StringIO()
        with (
            patch("svgap.cli.shutil.which", side_effect=lambda tool: f"/tools/{tool}"),
            patch("svgap.cli.subprocess.run") as run,
            patch(
                "svgap.cli.discover_backends",
                return_value=({"reference-yosys": object()}, {"broken": "load failed"}),
            ),
            patch("sys.stdout", output),
        ):
            run.return_value.stdout = "Yosys 0.66"
            code = doctor()
        self.assertEqual(code, 1)
        self.assertIn("plugin     broken: load failed", output.getvalue())
