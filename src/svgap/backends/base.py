from __future__ import annotations

from typing import Protocol

from svgap.model import CheckResult, Manifest


class CheckerBackend(Protocol):
    name: str
    version: str

    def check(self, manifest: Manifest) -> CheckResult: ...
