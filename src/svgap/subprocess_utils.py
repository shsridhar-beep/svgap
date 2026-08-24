from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path


def run_captured(
    command: Sequence[str],
    *,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run a tool with captured text output and a wall-clock process-tree limit.

    On POSIX, every invocation starts in a new session. If the timeout expires,
    the entire process group is killed before its pipes are collected. This
    prevents a grandchild that inherited stdout or stderr from keeping
    ``communicate()`` blocked after the direct child has been terminated.
    """

    popen_options: dict[str, object] = {}
    if os.name == "posix":
        popen_options["start_new_session"] = True
    elif os.name == "nt":  # pragma: no cover - exercised on Windows runners
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **popen_options,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_process_group(process)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            process.args,
            timeout,
            output=stdout if stdout else exc.output,
            stderr=stderr if stderr else exc.stderr,
        ) from None

    return subprocess.CompletedProcess(
        process.args,
        process.returncode,
        stdout,
        stderr,
    )


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except OSError:
            pass
    if process.poll() is None:
        process.kill()
