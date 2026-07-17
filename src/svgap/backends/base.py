from __future__ import annotations

from typing import Protocol

from svgap.model import CheckResult, Manifest


class CheckerBackend(Protocol):
    name: str
    version: str

    def check(self, manifest: Manifest) -> CheckResult: ...


class BackendUnavailable(ImportError):
    """An optional backend's dependencies are not installed.

    Raised at import time by backend modules that guard an optional
    dependency. The registry reports these separately from broken plugins:
    the backend is simply not installed, and the exception message must
    carry the actionable install hint (e.g. ``pip install 'svgap[naja]'``).
    """
