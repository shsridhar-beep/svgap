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


@dataclass(frozen=True)
class OracleConfig:
    """One independently versioned evidence producer in a schema-v2 manifest."""

    oracle_id: str
    oracle_class: str
    backend: str
    contributes_to_gap: bool = True
    required: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class OracleResult:
    """A checker result annotated with its role in the evidence profile."""

    oracle_id: str
    oracle_class: str
    contributes_to_gap: bool
    required: bool
    status: Status
    backend: str
    backend_version: str
    findings: list[Finding] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_check(
        cls,
        config: OracleConfig,
        result: CheckResult,
        *,
        coverage: dict[str, Any] | None = None,
    ) -> "OracleResult":
        return cls(
            oracle_id=config.oracle_id,
            oracle_class=config.oracle_class,
            contributes_to_gap=config.contributes_to_gap,
            required=config.required,
            status=result.status,
            backend=result.backend,
            backend_version=result.backend_version,
            findings=list(result.findings),
            diagnostics=list(result.diagnostics),
            tool_versions=dict(result.tool_versions),
            coverage=dict(coverage or {}),
        )

    def to_check_result(self) -> CheckResult:
        return CheckResult(
            status=self.status,
            backend=self.backend,
            backend_version=self.backend_version,
            findings=list(self.findings),
            diagnostics=list(self.diagnostics),
            tool_versions=dict(self.tool_versions),
        )


@dataclass
class FunctionalResult:
    status: Status
    commands: list[list[str]] = field(default_factory=list)
    returncodes: list[int] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    tool_versions: dict[str, str] = field(default_factory=dict)
    imported_from: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    schema_version: str
    candidate_id: str
    manifest: str
    functional: FunctionalResult
    structural: CheckResult
    gap_member: bool
    generated_at: str
    oracle_results: list[OracleResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "manifest": self.manifest,
            "functional": asdict(self.functional),
            "gap_member": self.gap_member,
            "generated_at": self.generated_at,
        }
        if self.schema_version == "1.0":
            payload["structural"] = asdict(self.structural)
        else:
            payload["oracle_results"] = [asdict(item) for item in self.oracle_results]
        return payload


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
    clock: str | None = None
    # None means legacy/unspecified intent. Only an explicit False enables
    # REF-RDC-003; True is an explicit waiver for reviewed reset logic.
    allow_combination: bool | None = None


@dataclass(frozen=True)
class CrossingIntent:
    source: str
    destination: str
    protocol: Literal[
        "single_bit",
        "gray",
        "pulse",
        "toggle",
        "handshake",
        "async_fifo",
        "unspecified",
    ]
    min_sync_stages: int | None = None
    return_source: str | None = None
    return_destination: str | None = None


@dataclass(frozen=True)
class StateRequirement:
    signal: str
    reset: str
    value: str | None = None


@dataclass
class Manifest:
    path: Path
    schema_version: str
    candidate_id: str
    top: str
    sources: list[Path]
    functional_commands: list[list[str]]
    functional_import: Path | None
    clocks: list[ClockIntent]
    asynchronous_groups: list[list[str]]
    resets: list[ResetIntent]
    crossings: list[CrossingIntent]
    power_on: Literal["unspecified", "reset_required"]
    init_attributes_are_power_on: bool
    backend: str
    report_path: Path
    oracles: list[OracleConfig] = field(default_factory=list)
    independent_reset_groups: list[list[str]] = field(default_factory=list)
    state_requirements: list[StateRequirement] = field(default_factory=list)
    x_policy: Literal["unspecified", "strict"] = "unspecified"
    memory_power_on: Literal["unspecified", "initialized_or_reset"] = "unspecified"
    cdc_reconvergence: Literal["unspecified", "forbid_independent"] = "unspecified"
