#!/usr/bin/env python3
"""Audit frozen public AI RTL benchmarks for power-on and X coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from svgap.audit import (  # noqa: E402
    file_revision,
    git_revision,
    parse_markdown_inputs,
    parse_rtllm_inputs,
    parse_verilog_inputs,
)
from svgap.power_audit import (  # noqa: E402
    PowerOnBenchmarkAudit,
    classify_power_on_task,
    combine_harness_files,
    write_power_on_audit,
)


def audit_verilog_eval(root: Path) -> PowerOnBenchmarkAudit:
    dataset = root / "dataset_spec-to-rtl"
    tasks = []
    for prompt_path in sorted(dataset.glob("*_prompt.txt")):
        prefix = prompt_path.name.removesuffix("_prompt.txt")
        prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
        inputs = tuple(dict.fromkeys(parse_verilog_inputs(prompt)))
        if not inputs:
            import re

            inputs = tuple(
                dict.fromkeys(
                    re.findall(
                        r"(?im)^\s*-\s*input\s+([A-Za-z_][A-Za-z0-9_]*)", prompt
                    )
                )
            )
        test = dataset / f"{prefix}_test.sv"
        tasks.append(
            classify_power_on_task(
                task_id=prefix,
                specification=prompt_path.relative_to(root),
                specification_text=prompt,
                harness_text=combine_harness_files((test,)),
                input_ports=inputs,
                functional_oracle=test.is_file(),
            )
        )
    return PowerOnBenchmarkAudit("verilog-eval", git_revision(root), tuple(tasks))


def audit_rtllm(root: Path) -> PowerOnBenchmarkAudit:
    descriptions = sorted(
        path
        for category in ("Arithmetic", "Control", "Memory", "Miscellaneous")
        for path in (root / category).glob("**/design_description.txt")
    )
    tasks = []
    for description in descriptions:
        prompt = description.read_text(encoding="utf-8", errors="replace")
        inputs = tuple(dict.fromkeys(parse_rtllm_inputs(prompt)))
        test = description.parent / "testbench.v"
        tasks.append(
            classify_power_on_task(
                task_id=str(description.parent.relative_to(root)),
                specification=description.relative_to(root),
                specification_text=prompt,
                harness_text=combine_harness_files((test,)),
                input_ports=inputs,
                functional_oracle=test.is_file(),
            )
        )
    return PowerOnBenchmarkAudit("rtllm", git_revision(root), tuple(tasks))


def audit_cvdp(dataset_path: Path) -> PowerOnBenchmarkAudit:
    tasks = []
    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            input_data = row.get("input", {})
            prompt = str(input_data.get("prompt", ""))
            context = input_data.get("context", {})
            context_text = (
                "\n".join(str(value) for value in context.values())
                if isinstance(context, dict)
                else str(context)
            )
            specification_text = prompt + "\n" + context_text
            inputs = parse_verilog_inputs(prompt) or parse_markdown_inputs(prompt)
            if not inputs:
                inputs = parse_verilog_inputs(context_text)
            harness = row.get("harness", {})
            files = harness.get("files", {}) if isinstance(harness, dict) else {}
            harness_text = (
                "\n".join(str(value) for value in files.values())
                if isinstance(files, dict)
                else ""
            )
            tasks.append(
                classify_power_on_task(
                    task_id=str(row.get("id", "<missing-id>")),
                    specification=Path(f"{row.get('id', '<missing-id>')}:input.prompt"),
                    specification_text=specification_text,
                    harness_text=harness_text,
                    input_ports=tuple(dict.fromkeys(inputs)),
                    functional_oracle=bool(files),
                )
            )
    return PowerOnBenchmarkAudit(
        "cvdp", file_revision(dataset_path), tuple(tasks)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verilog-eval", type=Path, required=True)
    parser.add_argument("--rtllm", type=Path, required=True)
    parser.add_argument("--cvdp", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "audits")
    args = parser.parse_args()
    audits = (
        audit_verilog_eval(args.verilog_eval.resolve()),
        audit_rtllm(args.rtllm.resolve()),
        audit_cvdp(args.cvdp.resolve()),
    )
    for audit in audits:
        write_power_on_audit(audit, args.output)
        print(json.dumps(audit.summary(), sort_keys=True))


if __name__ == "__main__":
    main()
