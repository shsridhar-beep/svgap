import os
import subprocess
import sys
import time
from unittest import TestCase, skipUnless

from svgap.subprocess_utils import run_captured


class SubprocessUtilsTests(TestCase):
    @skipUnless(os.name == "posix", "process-group timeout is POSIX-specific")
    def test_timeout_reaps_grandchild_that_inherits_output_pipes(self) -> None:
        child = (
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(2)'])"
        )
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            run_captured([sys.executable, "-c", child], timeout=0.1)
        self.assertLess(time.monotonic() - started, 1.5)
