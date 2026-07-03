from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from svgap.model import CheckResult, Finding, Manifest


@dataclass(frozen=True)
class SeqCell:
    name: str
    cell_type: str
    clock_bit: int | str
    clock_name: str
    d_bits: tuple[int | str, ...]
    q_bits: tuple[int | str, ...]
    arst_bits: tuple[int | str, ...]
    attributes: dict[str, Any]


class ReferenceYosysBackend:
    """Small, auditable structural oracle for controlled research fixtures."""

    name = "reference-yosys"
    version = "0.1"

    def check(self, manifest: Manifest) -> CheckResult:
        tool_versions = {"yosys": yosys_version()}
        build = manifest.path.parent / "build"
        build.mkdir(parents=True, exist_ok=True)
        netlist_path = build / "structural.json"
        script = "\n".join(
            [
                *[f"read_verilog -sv {yosys_quote(path)}" for path in manifest.sources],
                f"hierarchy -check -top {manifest.top}",
                "proc",
                "opt_clean",
                f"write_json {yosys_quote(netlist_path)}",
            ]
        )
        try:
            completed = subprocess.run(
                ["yosys", "-q", "-p", script],
                cwd=manifest.path.parent,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[str(exc)],
                tool_versions=tool_versions,
            )
        if completed.returncode != 0:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[completed.stderr.strip() or completed.stdout.strip()],
                tool_versions=tool_versions,
            )
        try:
            netlist = json.loads(netlist_path.read_text(encoding="utf-8"))
            result = self._analyze(manifest, netlist)
            result.tool_versions = tool_versions
            return result
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"cannot analyze Yosys netlist: {exc}"],
                tool_versions=tool_versions,
            )

    def _analyze(self, manifest: Manifest, netlist: dict[str, Any]) -> CheckResult:
        module = netlist["modules"][manifest.top]
        diagnostics: list[str] = []
        findings: list[Finding] = []

        if not manifest.clocks and not manifest.resets:
            diagnostics.append("no clock or reset intent was declared")
        declared_clock_names = {clock.name for clock in manifest.clocks}
        grouped_clock_names = {
            name for group in manifest.asynchronous_groups for name in group
        }
        unknown_group_names = sorted(grouped_clock_names - declared_clock_names)
        if unknown_group_names:
            diagnostics.append(
                "asynchronous groups reference undeclared clocks: "
                + ", ".join(unknown_group_names)
            )
        if len(manifest.clocks) > 1 and not manifest.asynchronous_groups:
            diagnostics.append("multiple clocks were declared without asynchronous groups")

        port_bits = {
            name: tuple(data.get("bits", ())) for name, data in module.get("ports", {}).items()
        }
        clock_by_bit: dict[int | str, str] = {}
        for clock in manifest.clocks:
            bits = port_bits.get(clock.port, ())
            if len(bits) != 1:
                diagnostics.append(f"clock port {clock.port!r} is missing or not scalar")
            else:
                clock_by_bit[bits[0]] = clock.name

        reset_by_bit = {}
        for reset in manifest.resets:
            bits = port_bits.get(reset.port, ())
            if len(bits) != 1:
                diagnostics.append(f"reset port {reset.port!r} is missing or not scalar")
            else:
                reset_by_bit[bits[0]] = reset

        netnames = module.get("netnames", {})
        names_by_bit: dict[int | str, set[str]] = defaultdict(set)
        for name, data in netnames.items():
            bits = data.get("bits", ())
            for bit in bits:
                names_by_bit[bit].add(name)

        cells = module.get("cells", {})
        seq: list[SeqCell] = []
        comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]] = {}
        comb_outputs_by_input: dict[int | str, list[tuple[int | str, str]]] = defaultdict(list)
        for name, cell in cells.items():
            connections = cell.get("connections", {})
            directions = cell.get("port_directions", {})
            if is_sequential(cell.get("type", "")):
                clk = first(connections.get("CLK", ()))
                seq.append(
                    SeqCell(
                        name=name,
                        cell_type=cell.get("type", ""),
                        clock_bit=clk,
                        clock_name=clock_by_bit.get(clk, "<undeclared>"),
                        d_bits=tuple(connections.get("D", ())),
                        q_bits=tuple(connections.get("Q", ())),
                        arst_bits=tuple(connections.get("ARST", ())),
                        attributes=cell.get("attributes", {}),
                    )
                )
            else:
                inputs = tuple(
                    bit
                    for port, bits in connections.items()
                    if directions.get(port) == "input"
                    for bit in bits
                )
                for port, bits in connections.items():
                    if directions.get(port) == "output":
                        for bit in bits:
                            comb_driver[bit] = (name, cell.get("type", ""), inputs)
                            for input_bit in inputs:
                                comb_outputs_by_input[input_bit].append(
                                    (bit, cell.get("type", ""))
                                )

        if any(cell.clock_name == "<undeclared>" for cell in seq):
            diagnostics.append("one or more state elements use an undeclared or unsupported clock")

        seq_by_q_bit = {bit: cell for cell in seq for bit in cell.q_bits}
        recognized_reset_sync_bits = reset_synchronizer_bits(seq, reset_by_bit)
        seq_d_consumers: dict[int | str, list[SeqCell]] = defaultdict(list)
        for cell in seq:
            for bit in cell.d_bits:
                seq_d_consumers[bit].append(cell)

        crossings: dict[tuple[str, str], dict[str, Any]] = {}
        for dst in seq:
            if dst.clock_name == "<undeclared>":
                continue
            for d_bit in dst.d_bits:
                for src, comb_path in trace_sequential_sources(
                    d_bit, seq_by_q_bit, comb_driver, set()
                ):
                    if src.clock_name in ("<undeclared>", dst.clock_name):
                        continue
                    if not are_asynchronous(
                        src.clock_name, dst.clock_name, manifest.asynchronous_groups
                    ):
                        continue
                    item = crossings.setdefault(
                        (src.name, dst.name),
                        {"src": src, "dst": dst, "bits": set(), "comb": set()},
                    )
                    item["bits"].add(d_bit)
                    item["comb"].update(comb_path)

        for item in crossings.values():
            src: SeqCell = item["src"]
            dst: SeqCell = item["dst"]
            width = len(item["bits"])
            second_stages = same_domain_successors(
                dst, seq_d_consumers, comb_outputs_by_input
            )
            evidence = {
                "source_cell": src.name,
                "source_clock": src.clock_name,
                "destination_cell": dst.name,
                "destination_clock": dst.clock_name,
                "width": width,
                "source_location": source_location(src, manifest),
                "destination_location": source_location(dst, manifest),
            }
            if not second_stages:
                findings.append(
                    Finding(
                        rule_id="REF-CDC-001",
                        severity="error",
                        message="asynchronous crossing is sampled without a recognized second stage",
                        evidence=evidence,
                    )
                )
                continue
            hazardous_comb = sorted(
                name for name, cell_type in item["comb"] if cell_type not in ("$mux", "$pmux")
            )
            if hazardous_comb:
                evidence["combinational_cells"] = hazardous_comb
                findings.append(
                    Finding(
                        rule_id="REF-CDC-002",
                        severity="error",
                        message="combinational logic appears between the source register and synchronizer",
                        evidence=evidence,
                    )
                )
            if width > 1 and not declared_coherent_protocol(
                manifest, src, second_stages, netnames, comb_driver
            ):
                findings.append(
                    Finding(
                        rule_id="REF-CDC-003",
                        severity="error",
                        message="multi-bit asynchronous crossing uses independent synchronizer stages without declared coherence protocol",
                        evidence=evidence,
                    )
                )

        for cell in seq:
            for reset_bit in cell.arst_bits:
                reset = reset_by_bit.get(reset_bit)
                if reset is None or reset.deassertion != "sync":
                    continue
                if set(cell.q_bits) & recognized_reset_sync_bits:
                    continue
                findings.append(
                    Finding(
                        rule_id="REF-RDC-001",
                        severity="error",
                        message="raw asynchronous reset reaches an unmarked state element although synchronous deassertion is required",
                        evidence={
                            "cell": cell.name,
                            "clock": cell.clock_name,
                            "reset": reset.name,
                            "source_location": source_location(cell, manifest),
                        },
                    )
                )

        if diagnostics:
            status = "unknown"
        else:
            status = "fail" if any(f.severity == "error" for f in findings) else "pass"
        return CheckResult(
            status=status,
            backend=self.name,
            backend_version=self.version,
            findings=findings,
            diagnostics=diagnostics,
        )


def yosys_quote(path: Path) -> str:
    value = str(path.resolve())
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError("unsupported control character in RTL path")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_sequential(cell_type: str) -> bool:
    lowered = cell_type.lower()
    return "dff" in lowered and not lowered.startswith("$dffsr")


def first(values: Iterable[int | str]) -> int | str:
    return next(iter(values), "<missing>")


def trace_sequential_sources(
    bit: int | str,
    seq_by_q_bit: dict[int | str, SeqCell],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
    visited: set[int | str],
) -> list[tuple[SeqCell, tuple[tuple[str, str], ...]]]:
    if bit in visited or isinstance(bit, str):
        return []
    if bit in seq_by_q_bit:
        return [(seq_by_q_bit[bit], ())]
    driver = comb_driver.get(bit)
    if driver is None:
        return []
    name, _cell_type, inputs = driver
    found: list[tuple[SeqCell, tuple[tuple[str, str], ...]]] = []
    for input_bit in inputs:
        for source, path in trace_sequential_sources(
            input_bit, seq_by_q_bit, comb_driver, {*visited, bit}
        ):
            found.append((source, ((name, _cell_type), *path)))
    return found


def same_domain_successors(
    cell: SeqCell,
    consumers: dict[int | str, list[SeqCell]],
    comb_outputs_by_input: dict[int | str, list[tuple[int | str, str]]],
) -> list[SeqCell]:
    found: dict[str, SeqCell] = {}
    frontier = list(cell.q_bits)
    visited: set[int | str] = set()
    while frontier:
        bit = frontier.pop()
        if bit in visited:
            continue
        visited.add(bit)
        for consumer in consumers.get(bit, ()):
            if consumer.name != cell.name and consumer.clock_name == cell.clock_name:
                found[consumer.name] = consumer
        frontier.extend(
            output_bit
            for output_bit, cell_type in comb_outputs_by_input.get(bit, ())
            if cell_type in ("$mux", "$pmux")
        )
    return list(found.values())


def are_asynchronous(source: str, destination: str, groups: list[list[str]]) -> bool:
    source_groups = {index for index, group in enumerate(groups) if source in group}
    destination_groups = {index for index, group in enumerate(groups) if destination in group}
    return bool(source_groups and destination_groups and source_groups.isdisjoint(destination_groups))


def declared_coherent_protocol(
    manifest: Manifest,
    source: SeqCell,
    second_stages: list[SeqCell],
    netnames: dict[str, Any],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
) -> bool:
    bits_by_name = {name: set(data.get("bits", ())) for name, data in netnames.items()}
    downstream = {bit for cell in second_stages for bit in cell.q_bits}
    for crossing in manifest.crossings:
        if crossing.protocol != "gray":
            continue
        declared_source = (
            set(source.q_bits)
            if crossing.source == "*"
            else bits_by_name.get(crossing.source, set())
        )
        if not (set(source.q_bits) & declared_source):
            continue
        declared_destination = (
            downstream
            if crossing.destination == "*"
            else bits_by_name.get(crossing.destination, set())
        )
        if not (downstream & declared_destination):
            continue
        source_d_bits = [
            source.d_bits[index]
            for index, q_bit in enumerate(source.q_bits)
            if q_bit in declared_source and index < len(source.d_bits)
        ]
        cone_types = {
            cell_type
            for d_bit in source_d_bits
            for cell_type in combinational_cone_types(d_bit, comb_driver, set())
        }
        if "$xor" in cone_types:
            return True
    return False


def reset_synchronizer_bits(
    seq: list[SeqCell], reset_by_bit: dict[int | str, Any]
) -> set[int | str]:
    """Recognize a conventional two-flop asynchronous-assert reset synchronizer.

    The first one-bit stage loads a constant inactive value; the second stage
    samples the first. Both share the same clock and raw asynchronous reset.
    This deliberately recognizes only the narrow reference structure.
    """
    recognized: set[int | str] = set()
    by_q_bit = {bit: cell for cell in seq for bit in cell.q_bits}
    for cell in seq:
        # Yosys may keep a shift-register synchronizer as one vector $adff.
        # Accept a constant first stage followed only by prior Q bits.
        if (
            len(cell.q_bits) >= 2
            and len(cell.d_bits) == len(cell.q_bits)
            and len(cell.arst_bits) == 1
            and cell.d_bits[0] == inactive_reset_value(cell, reset_by_bit)
            and tuple(cell.d_bits[1:]) == tuple(cell.q_bits[:-1])
        ):
            recognized.update(cell.q_bits)
    for second in seq:
        if len(second.q_bits) != 1 or len(second.d_bits) != 1 or len(second.arst_bits) != 1:
            continue
        first_stage = by_q_bit.get(second.d_bits[0])
        if first_stage is None or first_stage.name == second.name:
            continue
        if (
            len(first_stage.q_bits) != 1
            or len(first_stage.d_bits) != 1
            or len(first_stage.arst_bits) != 1
            or first_stage.clock_bit != second.clock_bit
            or first_stage.arst_bits != second.arst_bits
        ):
            continue
        if first_stage.d_bits[0] != inactive_reset_value(first_stage, reset_by_bit):
            continue
        recognized.update(first_stage.q_bits)
        recognized.update(second.q_bits)
    return recognized


def inactive_reset_value(
    cell: SeqCell, reset_by_bit: dict[int | str, Any]
) -> str | None:
    reset = reset_by_bit.get(first(cell.arst_bits))
    if reset is None:
        return None
    return "1" if reset.active == "low" else "0"


def combinational_cone_types(
    bit: int | str,
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
    visited: set[int | str],
) -> set[str]:
    if bit in visited or isinstance(bit, str):
        return set()
    driver = comb_driver.get(bit)
    if driver is None:
        return set()
    _name, cell_type, inputs = driver
    return {cell_type}.union(
        *(
            combinational_cone_types(input_bit, comb_driver, {*visited, bit})
            for input_bit in inputs
        )
    )


def source_location(cell: SeqCell, manifest: Manifest) -> str:
    location = str(cell.attributes.get("src", ""))
    prefix = str(manifest.path.parent.resolve()) + "/"
    return location.replace(prefix, "")


def yosys_version() -> str:
    try:
        completed = subprocess.run(
            ["yosys", "-V"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    return (completed.stdout.strip() or completed.stderr.strip() or "unknown").splitlines()[0]
