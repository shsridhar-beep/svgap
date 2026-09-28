from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Status = Literal["pass", "fail", "compile_error", "unknown", "tool_error", "not_run"]
ContractStatus = Literal["closed", "open", "incomplete", "tool_error"]


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
    artifacts: dict[str, Any] = field(default_factory=dict)
    observed_coverage: dict[str, Any] = field(default_factory=dict)


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
    artifacts: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_check(
        cls,
        config: OracleConfig,
        result: CheckResult,
        *,
        coverage: dict[str, Any] | None = None,
    ) -> "OracleResult":
        combined_coverage = dict(coverage or {})
        observed = dict(result.observed_coverage)
        observed.setdefault("executed", True)
        combined_coverage["observed"] = observed
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
            coverage=combined_coverage,
            artifacts=dict(result.artifacts),
        )

    def to_check_result(self) -> CheckResult:
        return CheckResult(
            status=self.status,
            backend=self.backend,
            backend_version=self.backend_version,
            findings=list(self.findings),
            diagnostics=list(self.diagnostics),
            tool_versions=dict(self.tool_versions),
            artifacts=dict(self.artifacts),
            observed_coverage=dict(self.coverage.get("observed", {})),
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
    contract_status: ContractStatus | None = None

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
            structural = asdict(self.structural)
            # Internal extension fields are represented by v2 oracle results.
            # Keeping them out of schema v1 preserves its byte-level contract.
            structural.pop("artifacts", None)
            structural.pop("observed_coverage", None)
            payload["structural"] = structural
        else:
            payload["oracle_results"] = [asdict(item) for item in self.oracle_results]
            if self.contract_status is not None:
                payload["contract_status"] = self.contract_status
        return payload


def configured_contract_status(
    functional: FunctionalResult, oracle_results: list[OracleResult]
) -> ContractStatus:
    """Summarize whether every required configured contract has usable evidence."""

    if functional.status == "tool_error":
        return "tool_error"
    if functional.status in {"fail", "compile_error"}:
        return "open"
    if functional.status != "pass":
        return "incomplete"

    required = [item for item in oracle_results if item.required]
    if any(item.status == "fail" for item in required):
        return "open"
    if any(item.status == "tool_error" for item in required):
        return "tool_error"
    if any(item.status == "unknown" for item in required) or not required:
        return "incomplete"
    if any(
        item.coverage.get("observed", {}).get("requirements_met") is False
        for item in required
    ):
        return "incomplete"
    return "closed"


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
