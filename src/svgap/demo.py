from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any

from svgap.enums import DemoScenario

ASSET_NAMES = (
    "tb.sv",
    "safe/design.sv",
    "safe/manifest.toml",
    "unsafe/design.sv",
    "unsafe/manifest.toml",
)


class DemoError(RuntimeError):
    pass


def materialize_demo(destination: Path, scenario: DemoScenario = DemoScenario.RESET_RELEASE) -> Path:
    destination = destination.resolve()
    if destination.exists() and not destination.is_dir():
        raise DemoError(f"demo output path is not a directory: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise DemoError(f"demo output directory is not empty: {destination}")

    scenario_dir_path = scenario.value.replace("-", "_")
    root = files("svgap").joinpath("demo_assets", scenario_dir_path)
    for relative in ASSET_NAMES:
        source = root.joinpath(relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def require_demo_tools() -> None:
    missing = [name for name in ("yosys", "iverilog", "vvp") if shutil.which(name) is None]
    if missing:
        raise DemoError(
            "demo requires open RTL tools: " + ", ".join(missing) + "; run `svgap doctor`"
        )


def build_demo_summary(
    safe_report: dict[str, Any], unsafe_report: dict[str, Any]
) -> dict[str, Any]:
    safe_findings = [item["rule_id"] for item in safe_report["structural"]["findings"]]
    unsafe_findings = [
        item["rule_id"] for item in unsafe_report["structural"]["findings"]
    ]
    expected = (
        safe_report["functional"]["status"] == "pass"
        and unsafe_report["functional"]["status"] == "pass"
        and safe_report["structural"]["status"] == "pass"
        and unsafe_report["structural"]["status"] == "fail"
        and "REF-RDC-001" in unsafe_findings
    )
    return {
        "schema_version": "1.0",
        "demo": "reset-release-functional-equivalence",
        "status": "pass" if expected else "fail",
        "safe": {
            "functional": safe_report["functional"]["status"],
            "structural": safe_report["structural"]["status"],
            "findings": safe_findings,
        },
        "unsafe": {
            "functional": unsafe_report["functional"]["status"],
            "structural": unsafe_report["structural"]["status"],
            "findings": unsafe_findings,
        },
        "result": (
            "The same functional oracle accepts both candidates, while declared "
            "reset-release intent and the structural oracle distinguish them."
        ),
        "claim_boundary": (
            "This controlled witness demonstrates non-identification under the "
            "supplied functional oracle; it is not a defect-rate estimate or silicon signoff."
        ),
    }


def render_demo_summary(summary: dict[str, Any], output: Path | None) -> str:
    safe = summary["safe"]
    unsafe = summary["unsafe"]
    lines = [
        "SV-Gap demo - same functional result, different production evidence",
        "",
        "candidate  functional  structural  findings",
        f"safe       {safe['functional']:<10}  {safe['structural']:<10}  "
        + (", ".join(safe["findings"]) or "none"),
        f"unsafe     {unsafe['functional']:<10}  {unsafe['structural']:<10}  "
        + (", ".join(unsafe["findings"]) or "none"),
        "",
        summary["result"],
        "",
        "The functional pass answers: did the supplied testbench accept the RTL?",
        "It does not answer: does reset release satisfy the declared structural intent?",
        "",
        "Claim boundary: " + summary["claim_boundary"],
    ]
    if output is not None:
        lines.extend(["", f"Artifacts: {output.resolve()}"])
    return "\n".join(lines) + "\n"


def write_demo_summary(summary: dict[str, Any], destination: Path) -> Path:
    path = destination / "summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
