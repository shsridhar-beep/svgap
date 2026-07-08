from __future__ import annotations

import hashlib
import json
import re
import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from svgap.provenance import canonical_file_set_digest


def load_task(task_dir: Path) -> dict[str, Any]:
    path = task_dir.resolve() / "task.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for key in ("id", "top", "testbench"):
        if key not in data:
            raise ValueError(f"missing {key!r} in {path}")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", str(data["id"])) is None:
        raise ValueError(f"unsafe task id in {path}: {data['id']!r}")
    return data


def extract_systemverilog(response: str, top: str) -> str:
    fenced = re.findall(r"```(?:systemverilog|verilog|sv)?\s*(.*?)```", response, re.I | re.S)
    candidates = fenced or [response]
    pattern = re.compile(
        rf"\bmodule\s+{re.escape(top)}\b.*?\bendmodule\b", re.S
    )
    for candidate in candidates:
        match = pattern.search(candidate)
        if match:
            return match.group(0).strip() + "\n"
    raise ValueError(f"response does not contain module {top!r}")


def materialize_candidate(
    task_dir: Path,
    response_path: Path,
    model: str,
    output_root: Path,
    run_id: str | None = None,
) -> Path:
    task_dir = task_dir.resolve()
    task = load_task(task_dir)
    raw = response_path.read_text(encoding="utf-8")
    design = extract_systemverilog(raw, str(task["top"]))
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", run_id or model).strip("-") or "unknown-model"
    run_dir = output_root.resolve() / slug / str(task["id"])
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(response_path, run_dir / "raw-response.txt")
    (run_dir / "design.sv").write_text(design, encoding="utf-8")
    prompt_path = task_dir / "prompt.md"
    task_path = task_dir / "task.toml"
    testbench_path = (task_dir / str(task["testbench"])).resolve()
    portable_testbench = run_dir / "task-testbench.sv"
    shutil.copy2(testbench_path, portable_testbench)
    evaluator_paths = sorted((Path(__file__).resolve().parent).rglob("*.py"))
    task_inputs = {
        "prompt.md": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "task.toml": hashlib.sha256(task_path.read_bytes()).hexdigest(),
        "testbench": hashlib.sha256(testbench_path.read_bytes()).hexdigest(),
    }
    metadata = {
        "schema_version": "1.0",
        "task_id": task["id"],
        "model": model,
        "run_id": run_id or model,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "task_inputs": task_inputs,
        "task_inputs_digest": hashlib.sha256(
            json.dumps(task_inputs, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "evaluator_source_digest": canonical_file_set_digest(
            Path(__file__).resolve().parents[2], evaluator_paths
        ),
        "raw_response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "design_sha256": hashlib.sha256(design.encode()).hexdigest(),
    }
    manifest_payload = render_manifest(task, task_dir, testbench="task-testbench.sv")
    (run_dir / "manifest.toml").write_text(manifest_payload, encoding="utf-8")
    metadata["manifest_sha256"] = hashlib.sha256(manifest_payload.encode()).hexdigest()
    (run_dir / "provenance.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return run_dir / "manifest.toml"


def render_manifest(
    task: dict[str, Any], task_dir: Path, *, testbench: str | Path | None = None
) -> str:
    testbench = testbench or (task_dir / str(task["testbench"])).resolve()
    lines = [
        'schema_version = "1.0"',
        f'candidate_id = {toml_string(str(task["id"]))}',
        "[design]",
        f'top = {toml_string(str(task["top"]))}',
        'sources = ["design.sv"]',
        "[functional]",
        "commands = [",
        f'  ["iverilog", "-g2012", "-o", "${{SVGAP_BUILD}}/sim.vvp", "design.sv", {toml_string(str(testbench))}],',
        '  ["vvp", "${SVGAP_BUILD}/sim.vvp"],',
        "]",
        "[structural]",
        'backend = "reference-yosys"',
        "[intent]",
        "asynchronous_groups = " + toml_array(task.get("asynchronous_groups", [])),
    ]
    if "power_on" in task:
        lines.append(f'power_on = {toml_string(str(task["power_on"]))}')
        lines.append(
            "init_attributes_are_power_on = "
            + ("true" if bool(task.get("init_attributes_are_power_on", False)) else "false")
        )
    for clock in task.get("clocks", []):
        lines.extend(
            [
                "[[intent.clocks]]",
                f'name = {toml_string(str(clock["name"]))}',
                f'port = {toml_string(str(clock["port"]))}',
            ]
        )
    for reset in task.get("resets", []):
        lines.extend(["[[intent.resets]]", *[f"{key} = {toml_string(str(reset[key]))}" for key in ("name", "port", "active", "assertion", "deassertion")]])
    for crossing in task.get("crossings", []):
        lines.extend(["[[intent.crossings]]", *[f"{key} = {toml_string(str(crossing[key]))}" for key in ("source", "destination", "protocol")]])
    lines.extend(["[output]", 'report = "report.json"'])
    return "\n".join(lines) + "\n"


def toml_string(value: str) -> str:
    return json.dumps(value)


def toml_array(value: Any) -> str:
    return json.dumps(value)
