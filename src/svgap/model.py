from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Status = Literal["pass", "fail", "compile_error", "unknown", "tool_error", "not_run"]


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Literal["error", "warning", "info"]
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    status: Status
    backend: str
    backend_version: str
    findings: list[Finding] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)


@dataclass
class FunctionalResult:
    status: Status
    commands: list[list[str]] = field(default_factory=list)
    returncodes: list[int] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    tool_versions: dict[str, str] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    schema_version: str
    candidate_id: str
    manifest: str
    functional: FunctionalResult
    structural: CheckResult
    gap_member: bool
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClockIntent:
    name: str
    port: str


@dataclass(frozen=True)
class ResetIntent:
    name: str
    port: str
    active: Literal["high", "low"]
    assertion: Literal["async", "sync"]
    deassertion: Literal["async", "sync"]


@dataclass(frozen=True)
class CrossingIntent:
    source: str
    destination: str
    protocol: Literal["single_bit", "gray", "handshake", "unspecified"]


@dataclass
class Manifest:
    path: Path
    schema_version: str
    candidate_id: str
    top: str
    sources: list[Path]
    functional_commands: list[list[str]]
    clocks: list[ClockIntent]
    asynchronous_groups: list[list[str]]
    resets: list[ResetIntent]
    crossings: list[CrossingIntent]
    backend: str
    report_path: Path
