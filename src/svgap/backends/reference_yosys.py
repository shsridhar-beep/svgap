from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from svgap.model import CheckResult, Finding, Manifest, OracleConfig


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
    srst_bits: tuple[int | str, ...] = ()
    arst_value: tuple[str, ...] = ()
    srst_value: tuple[str, ...] = ()


class ReferenceYosysBackend:
    """Small, auditable structural oracle for controlled research fixtures."""

    name = "reference-yosys"
    version = "0.3"

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
                "opt_dff",
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
            netlist = portable_netlist(netlist, manifest.path.parent)
            netlist_path.write_text(
                json.dumps(netlist, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
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

    def coverage(
        self, manifest: Manifest, oracle: OracleConfig | None = None
    ) -> dict[str, Any]:
        return {
            "class": "structural",
            "rules": [
                "REF-CDC-001",
                "REF-CDC-002",
                "REF-CDC-003",
                "REF-CDC-004",
                "REF-CDC-005",
                "REF-CDC-006",
                "REF-CDC-007",
                "REF-CDC-008",
                "REF-META-001",
                "REF-RDC-001",
                "REF-RDC-002",
                "REF-RDC-003",
                "REF-RDC-004",
                "REF-XPROP-001",
                "REF-XPROP-002",
                "REF-XPROP-003",
                "REF-XPROP-004",
            ],
            "declared_clocks": len(manifest.clocks),
            "declared_resets": len(manifest.resets),
            "declared_crossings": len(manifest.crossings),
            "reference_only": True,
            "signoff_grade": False,
        }

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
        bits_by_name = {
            name: set(data.get("bits", ())) for name, data in netnames.items()
        }
        names_by_bit: dict[int | str, set[str]] = defaultdict(set)
        for name, data in netnames.items():
            bits = data.get("bits", ())
            for bit in bits:
                names_by_bit[bit].add(name)

        cells = module.get("cells", {})
        seq: list[SeqCell] = []
        comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]] = {}
        comb_outputs_by_input: dict[int | str, list[tuple[int | str, str]]] = defaultdict(list)
        comb_cells: dict[
            str, tuple[str, tuple[int | str, ...], tuple[int | str, ...]]
        ] = {}
        for name, cell in cells.items():
            connections = cell.get("connections", {})
            directions = cell.get("port_directions", {})
            if is_sequential(cell.get("type", "")):
                clk = first(connections.get("CLK", ()))
                q_bits = tuple(connections.get("Q", ()))
                parameters = cell.get("parameters", {})
                seq.append(
                    SeqCell(
                        name=name,
                        cell_type=cell.get("type", ""),
                        clock_bit=clk,
                        clock_name=clock_by_bit.get(clk, "<undeclared>"),
                        d_bits=tuple(connections.get("D", ())),
                        q_bits=q_bits,
                        arst_bits=tuple(connections.get("ARST", ())),
                        attributes=cell.get("attributes", {}),
                        srst_bits=tuple(connections.get("SRST", ())),
                        arst_value=yosys_parameter_bits(
                            parameters.get("ARST_VALUE"), len(q_bits)
                        ),
                        srst_value=yosys_parameter_bits(
                            parameters.get("SRST_VALUE"), len(q_bits)
                        ),
                    )
                )
            else:
                inputs = tuple(
                    bit
                    for port, bits in connections.items()
                    if directions.get(port) == "input"
                    for bit in bits
                )
                outputs = tuple(
                    bit
                    for port, bits in connections.items()
                    if directions.get(port) == "output"
                    for bit in bits
                )
                comb_cells[name] = (cell.get("type", ""), inputs, outputs)
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
        output_bits = {
            bit
            for data in module.get("ports", {}).values()
            if data.get("direction") == "output"
            for bit in data.get("bits", ())
        }
        initialized_bits = {
            bit
            for data in netnames.values()
            if "init" in data.get("attributes", {})
            for bit in data.get("bits", ())
        }
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
            item["second_stages"] = second_stages
            item["sync_depth"] = synchronizer_depth(
                dst, seq_d_consumers, comb_outputs_by_input
            )
            evidence = {
                "source_cell": src.name,
                "source_clock": src.clock_name,
                "destination_cell": dst.name,
                "destination_clock": dst.clock_name,
                "width": width,
                "recognized_sync_stages": item["sync_depth"],
                "source_location": source_location(src, manifest),
                "destination_location": source_location(dst, manifest),
            }
            declared = matching_crossing_intents(
                manifest, src, dst, second_stages, bits_by_name
            )
            required_depth = max(
                (
                    crossing.min_sync_stages
                    for crossing in declared
                    if crossing.min_sync_stages is not None
                ),
                default=None,
            )
            if required_depth is not None and item["sync_depth"] < required_depth:
                meta_evidence = dict(evidence)
                meta_evidence["required_sync_stages"] = required_depth
                findings.append(
                    Finding(
                        rule_id="REF-META-001",
                        severity="error",
                        message=(
                            "recognized synchronizer depth is below the declared "
                            "metastability containment requirement"
                        ),
                        evidence=meta_evidence,
                    )
                )
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

            for crossing in declared:
                if crossing.protocol == "pulse" and not recognized_pulse_transfer(
                    src,
                    second_stages,
                    crossing,
                    bits_by_name,
                    seq,
                    comb_driver,
                    comb_cells,
                ):
                    findings.append(
                        Finding(
                            rule_id="REF-CDC-004",
                            severity="error",
                            message=(
                                "declared pulse crossing lacks a recognized toggle "
                                "encoder and destination pulse decoder"
                            ),
                            evidence=dict(evidence),
                        )
                    )
                if crossing.protocol == "toggle" and not has_toggle_feedback(
                    src, comb_driver
                ):
                    findings.append(
                        Finding(
                            rule_id="REF-CDC-005",
                            severity="error",
                            message=(
                                "declared toggle crossing lacks recognized source "
                                "toggle feedback"
                            ),
                            evidence=dict(evidence),
                        )
                    )

        for crossing in manifest.crossings:
            if crossing.protocol not in ("handshake", "async_fifo"):
                continue
            main_items = matching_crossing_items(
                crossing, crossings.values(), bits_by_name
            )
            if not main_items:
                continue
            return_items = matching_crossing_items(
                crossing, crossings.values(), bits_by_name, return_side=True
            )
            return_is_synchronized = any(
                item.get("sync_depth", 0) >= (crossing.min_sync_stages or 2)
                for item in return_items
            )
            if crossing.protocol == "handshake" and not return_is_synchronized:
                findings.append(
                    Finding(
                        rule_id="REF-CDC-006",
                        severity="error",
                        message=(
                            "declared handshake crossing lacks a recognized "
                            "synchronized return acknowledgment"
                        ),
                        evidence=crossing_intent_evidence(crossing, main_items),
                    )
                )
            if crossing.protocol == "async_fifo":
                main_gray = all(
                    has_gray_encoding(item["src"], comb_driver)
                    and item.get("sync_depth", 0) >= (crossing.min_sync_stages or 2)
                    for item in main_items
                )
                return_gray = bool(return_items) and all(
                    has_gray_encoding(item["src"], comb_driver)
                    and item.get("sync_depth", 0) >= (crossing.min_sync_stages or 2)
                    for item in return_items
                )
                if not (main_gray and return_gray):
                    evidence = crossing_intent_evidence(crossing, main_items)
                    evidence.update(
                        {
                            "forward_gray_recognized": main_gray,
                            "return_gray_recognized": return_gray,
                        }
                    )
                    findings.append(
                        Finding(
                            rule_id="REF-CDC-008",
                            severity="error",
                            message=(
                                "declared asynchronous FIFO lacks recognized "
                                "bidirectional Gray-pointer synchronization"
                            ),
                            evidence=evidence,
                        )
                    )

        if manifest.cdc_reconvergence == "forbid_independent":
            findings.extend(
                reconvergence_findings(crossings.values(), comb_cells, manifest)
            )

        if manifest.power_on == "reset_required":
            if not manifest.resets:
                diagnostics.append(
                    "power-on intent requires reset coverage but no reset was declared"
                )
            for cell in seq:
                if cell.arst_bits or cell.srst_bits:
                    continue
                if set(cell.q_bits) & recognized_reset_sync_bits:
                    continue
                if (
                    manifest.init_attributes_are_power_on
                    and set(cell.q_bits) <= initialized_bits
                ):
                    continue
                reached = reachable_outputs(
                    cell.q_bits, output_bits, comb_outputs_by_input
                )
                if not reached:
                    continue
                findings.append(
                    Finding(
                        rule_id="REF-XPROP-001",
                        severity="error",
                        message=(
                            "un-reset operational state reaches a module output although "
                            "declared power-on intent requires reset coverage"
                        ),
                        evidence={
                            "cell": cell.name,
                            "clock": cell.clock_name,
                            "output_signals": sorted(
                                {
                                    name
                                    for bit in reached
                                    for name in names_by_bit.get(bit, ())
                                    if bit in output_bits
                                }
                            ),
                            "source_location": source_location(cell, manifest),
                        },
                    )
                )

        if manifest.x_policy == "strict":
            findings.extend(x_control_findings(manifest))

        if manifest.memory_power_on == "initialized_or_reset":
            for memory in uninitialized_memories(module):
                findings.append(
                    Finding(
                        rule_id="REF-XPROP-004",
                        severity="error",
                        message=(
                            "memory lacks a recognized complete initialization "
                            "although deterministic power-on state is required"
                        ),
                        evidence={
                            "memory": memory["name"],
                            "width": memory["width"],
                            "size": memory["size"],
                            "initialized_words": memory["initialized_words"],
                            "source_location": portable_source_location(
                                memory["source_location"], manifest
                            ),
                        },
                    )
                )

        reset_names_by_bit = {
            bit: reset.name for bit, reset in reset_by_bit.items()
        }
        for requirement in manifest.state_requirements:
            signal_bits = tuple(netnames.get(requirement.signal, {}).get("bits", ()))
            if not signal_bits:
                diagnostics.append(
                    f"state requirement signal {requirement.signal!r} is missing"
                )
                continue
            cells_for_signal = [
                cell for cell in seq if set(cell.q_bits) & set(signal_bits)
            ]
            if not cells_for_signal:
                diagnostics.append(
                    f"state requirement signal {requirement.signal!r} is not state"
                )
                continue
            for cell in cells_for_signal:
                reset_values = reset_values_for_cell(
                    cell, reset_names_by_bit, comb_driver
                )
                observed = reset_values.get(requirement.reset)
                reset_present = requirement.reset in reset_values
                value_matches = requirement.value is None or reset_value_matches(
                    requirement.value, signal_bits, cell, observed
                )
                if reset_present and value_matches:
                    continue
                evidence = {
                    "signal": requirement.signal,
                    "cell": cell.name,
                    "required_reset": requirement.reset,
                    "required_value": requirement.value,
                    "observed_value": (
                        "".join(reversed(observed)) if observed else None
                    ),
                    "source_location": source_location(cell, manifest),
                }
                findings.append(
                    Finding(
                        rule_id="REF-XPROP-003",
                        severity="error",
                        message=(
                            "declared operational state lacks its required reset "
                            "coverage or reset value"
                        ),
                        evidence=evidence,
                    )
                )

        seen_rdc2: set[tuple[str, str, str, str]] = set()
        for dst in seq:
            dst_resets = reset_origins_for_cell(
                dst, reset_names_by_bit, comb_driver
            )
            if not dst_resets:
                continue
            for d_bit in dst.d_bits:
                for src, _path in trace_sequential_sources(
                    d_bit, seq_by_q_bit, comb_driver, set()
                ):
                    if src.name == dst.name:
                        continue
                    src_resets = reset_origins_for_cell(
                        src, reset_names_by_bit, comb_driver
                    )
                    independent_pairs = sorted(
                        (source_reset, destination_reset)
                        for source_reset in src_resets
                        for destination_reset in dst_resets
                        if resets_are_independent(
                            source_reset,
                            destination_reset,
                            manifest.independent_reset_groups,
                        )
                    )
                    for source_reset, destination_reset in independent_pairs:
                        key = (
                            src.name,
                            dst.name,
                            source_reset,
                            destination_reset,
                        )
                        if key in seen_rdc2:
                            continue
                        seen_rdc2.add(key)
                        findings.append(
                            Finding(
                                rule_id="REF-RDC-002",
                                severity="error",
                                message=(
                                    "data crosses between independently reset state "
                                    "domains without a recognized isolation protocol"
                                ),
                                evidence={
                                    "source_cell": src.name,
                                    "destination_cell": dst.name,
                                    "source_reset": source_reset,
                                    "destination_reset": destination_reset,
                                    "source_location": source_location(src, manifest),
                                    "destination_location": source_location(
                                        dst, manifest
                                    ),
                                },
                            )
                        )

        seen_reset_paths: set[tuple[str, str, str]] = set()
        for cell in seq:
            for pin_kind, pin_bits in (
                ("asynchronous", cell.arst_bits),
                ("synchronous", cell.srst_bits),
            ):
                for reset_bit in pin_bits:
                    origins = trace_declared_reset_origins(
                        reset_bit, reset_names_by_bit, comb_driver, set()
                    )
                    if len(origins) > 1:
                        key = (cell.name, pin_kind, "reconvergence")
                        if key not in seen_reset_paths:
                            seen_reset_paths.add(key)
                            findings.append(
                                Finding(
                                    rule_id="REF-RDC-004",
                                    severity="error",
                                    message=(
                                        "multiple declared resets reconverge onto one "
                                        "state-element reset pin"
                                    ),
                                    evidence={
                                        "cell": cell.name,
                                        "pin_kind": pin_kind,
                                        "resets": sorted(origins),
                                        "combinational_cells": sorted(
                                            {
                                                name
                                                for path in origins.values()
                                                for name, _cell_type in path
                                            }
                                        ),
                                        "source_location": source_location(
                                            cell, manifest
                                        ),
                                    },
                                )
                            )
                    for reset_name, path in origins.items():
                        reset = next(
                            item for item in manifest.resets if item.name == reset_name
                        )
                        if not path or reset.allow_combination is not False:
                            continue
                        key = (cell.name, pin_kind, reset_name)
                        if key in seen_reset_paths:
                            continue
                        seen_reset_paths.add(key)
                        findings.append(
                            Finding(
                                rule_id="REF-RDC-003",
                                severity="error",
                                message=(
                                    "declared reset reaches a state-element reset pin "
                                    "through unapproved combinational logic"
                                ),
                                evidence={
                                    "cell": cell.name,
                                    "pin_kind": pin_kind,
                                    "reset": reset_name,
                                    "combinational_cells": [
                                        name for name, _cell_type in path
                                    ],
                                    "source_location": source_location(cell, manifest),
                                },
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


def portable_netlist(value: Any, candidate_root: Path) -> Any:
    """Remove the candidate's absolute root from shareable Yosys JSON."""
    root = candidate_root.resolve()
    prefixes = {str(root), root.as_posix()}

    def clean(text: str) -> str:
        for prefix in prefixes:
            text = text.replace(prefix + "/", "").replace(prefix + "\\", "")
        return text

    def walk(item: Any) -> Any:
        if isinstance(item, dict):
            return {clean(str(key)): walk(nested) for key, nested in item.items()}
        if isinstance(item, list):
            return [walk(nested) for nested in item]
        if isinstance(item, str):
            return clean(item)
        return item

    return walk(value)


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


def synchronizer_depth(
    cell: SeqCell,
    consumers: dict[int | str, list[SeqCell]],
    comb_outputs_by_input: dict[int | str, list[tuple[int | str, str]]],
    visited: set[str] | None = None,
) -> int:
    """Return the longest narrow same-clock register chain beginning at cell.

    This is a reference recognizer, not an MTBF calculator. It follows only
    direct register fanout and mux glue, matching ``same_domain_successors``.
    """
    visited = set(visited or ())
    if cell.name in visited:
        return 0
    successors = [
        item
        for item in same_domain_successors(cell, consumers, comb_outputs_by_input)
        if item.name not in visited
    ]
    if not successors:
        return 1
    return 1 + max(
        synchronizer_depth(
            item,
            consumers,
            comb_outputs_by_input,
            {*visited, cell.name},
        )
        for item in successors
    )


def matching_crossing_intents(
    manifest: Manifest,
    source: SeqCell,
    first_stage: SeqCell,
    second_stages: list[SeqCell],
    bits_by_name: dict[str, set[int | str]],
) -> list[Any]:
    destination_bits = set(first_stage.q_bits).union(
        *(set(cell.q_bits) for cell in second_stages)
    )
    matches = []
    for crossing in manifest.crossings:
        source_bits = (
            set(source.q_bits)
            if crossing.source == "*"
            else bits_by_name.get(crossing.source, set())
        )
        declared_destination = (
            destination_bits
            if crossing.destination == "*"
            else bits_by_name.get(crossing.destination, set())
        )
        if set(source.q_bits) & source_bits and destination_bits & declared_destination:
            matches.append(crossing)
    return matches


def matching_crossing_items(
    crossing: Any,
    items: Iterable[dict[str, Any]],
    bits_by_name: dict[str, set[int | str]],
    *,
    return_side: bool = False,
) -> list[dict[str, Any]]:
    source_name = crossing.return_source if return_side else crossing.source
    destination_name = (
        crossing.return_destination if return_side else crossing.destination
    )
    if source_name is None or destination_name is None:
        return []
    matched = []
    for item in items:
        source: SeqCell = item["src"]
        first_stage: SeqCell = item["dst"]
        second_stages: list[SeqCell] = item.get("second_stages", [])
        destination_bits = set(first_stage.q_bits).union(
            *(set(cell.q_bits) for cell in second_stages)
        )
        source_bits = (
            set(source.q_bits)
            if source_name == "*"
            else bits_by_name.get(source_name, set())
        )
        declared_destination = (
            destination_bits
            if destination_name == "*"
            else bits_by_name.get(destination_name, set())
        )
        if set(source.q_bits) & source_bits and destination_bits & declared_destination:
            matched.append(item)
    return matched


def crossing_intent_evidence(
    crossing: Any, items: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "source": crossing.source,
        "destination": crossing.destination,
        "return_source": crossing.return_source,
        "return_destination": crossing.return_destination,
        "source_cells": sorted({item["src"].name for item in items}),
        "destination_cells": sorted({item["dst"].name for item in items}),
    }


def cone_uses_any_bit(
    bit: int | str,
    targets: set[int | str],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
    visited: set[int | str],
) -> bool:
    if bit in targets:
        return True
    if bit in visited or isinstance(bit, str):
        return False
    driver = comb_driver.get(bit)
    if driver is None:
        return False
    return any(
        cone_uses_any_bit(input_bit, targets, comb_driver, {*visited, bit})
        for input_bit in driver[2]
    )


def has_toggle_feedback(
    source: SeqCell,
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
) -> bool:
    source_bits = set(source.q_bits)
    for d_bit in source.d_bits:
        types = combinational_cone_types(d_bit, comb_driver, set())
        if not ({"$xor", "$not"} & types):
            continue
        if cone_uses_any_bit(d_bit, source_bits, comb_driver, set()):
            return True
    return False


def has_gray_encoding(
    source: SeqCell,
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
) -> bool:
    return any(
        "$xor" in combinational_cone_types(d_bit, comb_driver, set())
        for d_bit in source.d_bits
    )


def recognized_pulse_transfer(
    source: SeqCell,
    second_stages: list[SeqCell],
    crossing: Any,
    bits_by_name: dict[str, set[int | str]],
    seq: list[SeqCell],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
    comb_cells: dict[
        str, tuple[str, tuple[int | str, ...], tuple[int | str, ...]]
    ],
) -> bool:
    if not has_toggle_feedback(source, comb_driver) or not second_stages:
        return False
    stable_bits = {bit for cell in second_stages for bit in cell.q_bits}
    delayed_bits = {
        bit
        for stable in stable_bits
        for cell in seq
        if cell.clock_name == second_stages[0].clock_name
        and stable in cell.d_bits
        and not (set(cell.q_bits) & stable_bits)
        for bit in cell.q_bits
    }
    declared_output = (
        None
        if crossing.destination == "*"
        else bits_by_name.get(crossing.destination, set())
    )
    for cell_type, inputs, outputs in comb_cells.values():
        if cell_type != "$xor":
            continue
        if not (set(inputs) & stable_bits and set(inputs) & delayed_bits):
            continue
        if declared_output is None or set(outputs) & declared_output:
            return True
    return False


def reconvergence_findings(
    items: Iterable[dict[str, Any]],
    comb_cells: dict[
        str, tuple[str, tuple[int | str, ...], tuple[int | str, ...]]
    ],
    manifest: Manifest,
) -> list[Finding]:
    by_clock: dict[str, dict[int | str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    labels: dict[str, dict[str, str]] = defaultdict(dict)
    for item in items:
        second_stages: list[SeqCell] = item.get("second_stages", [])
        if not second_stages:
            continue
        token = f"{item['src'].name}->{item['dst'].name}"
        clock = item["dst"].clock_name
        labels[clock][token] = item["src"].name
        for cell in second_stages:
            for bit in cell.q_bits:
                by_clock[clock][bit].add(token)

    found: list[Finding] = []
    emitted: set[tuple[str, str]] = set()
    for clock, taints in by_clock.items():
        changed = True
        while changed:
            changed = False
            for name, (cell_type, inputs, outputs) in comb_cells.items():
                combined = set().union(*(taints.get(bit, set()) for bit in inputs))
                if not combined:
                    continue
                if len(combined) >= 2 and (clock, name) not in emitted:
                    emitted.add((clock, name))
                    found.append(
                        Finding(
                            rule_id="REF-CDC-007",
                            severity="error",
                            message=(
                                "independently synchronized asynchronous paths "
                                "reconverge in destination-domain logic"
                            ),
                            evidence={
                                "cell": name,
                                "cell_type": cell_type,
                                "destination_clock": clock,
                                "crossing_paths": sorted(combined),
                                "source_cells": sorted(
                                    {labels[clock][token] for token in combined}
                                ),
                            },
                        )
                    )
                for output in outputs:
                    before = len(taints[output])
                    taints[output].update(combined)
                    changed = changed or len(taints[output]) != before
    return found


def reachable_outputs(
    start_bits: Iterable[int | str],
    output_bits: set[int | str],
    comb_outputs_by_input: dict[int | str, list[tuple[int | str, str]]],
) -> set[int | str]:
    """Return module outputs in the forward combinational cone of state bits."""
    reached: set[int | str] = set()
    frontier = list(start_bits)
    visited: set[int | str] = set()
    while frontier:
        bit = frontier.pop()
        if bit in visited or isinstance(bit, str):
            continue
        visited.add(bit)
        if bit in output_bits:
            reached.add(bit)
        frontier.extend(
            output_bit for output_bit, _cell_type in comb_outputs_by_input.get(bit, ())
        )
    return reached


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
        if crossing.protocol not in ("gray", "async_fifo"):
            continue
        endpoint_pairs = [(crossing.source, crossing.destination)]
        if crossing.protocol == "async_fifo":
            endpoint_pairs.append(
                (crossing.return_source, crossing.return_destination)
            )
        for source_name, destination_name in endpoint_pairs:
            if source_name is None or destination_name is None:
                continue
            declared_source = (
                set(source.q_bits)
                if source_name == "*"
                else bits_by_name.get(source_name, set())
            )
            if not (set(source.q_bits) & declared_source):
                continue
            declared_destination = (
                downstream
                if destination_name == "*"
                else bits_by_name.get(destination_name, set())
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


def yosys_parameter_bits(value: Any, width: int) -> tuple[str, ...]:
    """Normalize a Yosys binary parameter to Q-connection (LSB-first) order."""
    if not isinstance(value, str) or width <= 0:
        return ()
    normalized = value.lower().replace("z", "x")
    if re.fullmatch(r"[01x]+", normalized) is None:
        return ()
    return tuple(reversed(normalized[-width:].rjust(width, "x")))


def trace_declared_reset_origins(
    bit: int | str,
    reset_names_by_bit: dict[int | str, str],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
    visited: set[int | str],
) -> dict[str, tuple[tuple[str, str], ...]]:
    if bit in reset_names_by_bit:
        return {reset_names_by_bit[bit]: ()}
    if bit in visited or isinstance(bit, str):
        return {}
    driver = comb_driver.get(bit)
    if driver is None:
        return {}
    name, cell_type, inputs = driver
    found: dict[str, tuple[tuple[str, str], ...]] = {}
    for input_bit in inputs:
        origins = trace_declared_reset_origins(
            input_bit, reset_names_by_bit, comb_driver, {*visited, bit}
        )
        for reset_name, path in origins.items():
            candidate = ((name, cell_type), *path)
            if reset_name not in found or len(candidate) < len(found[reset_name]):
                found[reset_name] = candidate
    return found


def reset_origins_for_cell(
    cell: SeqCell,
    reset_names_by_bit: dict[int | str, str],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
) -> set[str]:
    return {
        reset_name
        for bit in (*cell.arst_bits, *cell.srst_bits)
        for reset_name in trace_declared_reset_origins(
            bit, reset_names_by_bit, comb_driver, set()
        )
    }


def reset_values_for_cell(
    cell: SeqCell,
    reset_names_by_bit: dict[int | str, str],
    comb_driver: dict[int | str, tuple[str, str, tuple[int | str, ...]]],
) -> dict[str, tuple[str, ...]]:
    values: dict[str, tuple[str, ...]] = {}
    for pin_bits, value in (
        (cell.arst_bits, cell.arst_value),
        (cell.srst_bits, cell.srst_value),
    ):
        for bit in pin_bits:
            for reset_name in trace_declared_reset_origins(
                bit, reset_names_by_bit, comb_driver, set()
            ):
                values.setdefault(reset_name, value)
    return values


def reset_value_matches(
    expected: str,
    signal_bits: tuple[int | str, ...],
    cell: SeqCell,
    observed: tuple[str, ...] | None,
) -> bool:
    if observed is None or len(expected) != len(signal_bits):
        return False
    expected_lsb_first = tuple(reversed(expected.lower().replace("z", "x")))
    for index, signal_bit in enumerate(signal_bits):
        if signal_bit not in cell.q_bits:
            continue
        q_index = cell.q_bits.index(signal_bit)
        if q_index >= len(observed) or observed[q_index] != expected_lsb_first[index]:
            return False
    return True


def resets_are_independent(
    source: str, destination: str, groups: list[list[str]]
) -> bool:
    source_groups = {index for index, group in enumerate(groups) if source in group}
    destination_groups = {
        index for index, group in enumerate(groups) if destination in group
    }
    return bool(
        source != destination
        and source_groups
        and destination_groups
        and source_groups.isdisjoint(destination_groups)
    )


def _strip_sv_comments_and_strings(text: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code" and current == "/" and following == "/":
            output.extend((" ", " "))
            index += 2
            state = "line_comment"
            continue
        if state == "code" and current == "/" and following == "*":
            output.extend((" ", " "))
            index += 2
            state = "block_comment"
            continue
        if state == "code" and current == '"':
            output.append(" ")
            index += 1
            state = "string"
            continue
        if state == "line_comment":
            output.append("\n" if current == "\n" else " ")
            index += 1
            if current == "\n":
                state = "code"
            continue
        if state == "block_comment":
            if current == "*" and following == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
            else:
                output.append("\n" if current == "\n" else " ")
                index += 1
            continue
        if state == "string":
            if current == "\\" and following:
                output.extend((" ", "\n" if following == "\n" else " "))
                index += 2
            else:
                output.append("\n" if current == "\n" else " ")
                index += 1
                if current == '"':
                    state = "code"
            continue
        output.append(current)
        index += 1
    return "".join(output)


def x_control_findings(manifest: Manifest) -> list[Finding]:
    findings: list[Finding] = []
    token_re = re.compile(r"\b(casex|casez|case|endcase|default)\b|==\?", re.I)
    for source in manifest.sources:
        cleaned = _strip_sv_comments_and_strings(
            source.read_text(encoding="utf-8", errors="replace")
        )
        stack: list[dict[str, Any]] = []
        for match in token_re.finditer(cleaned):
            token = match.group(0).lower()
            line = cleaned.count("\n", 0, match.start()) + 1
            location = f"{source.name}:{line}"
            if token in ("casex", "casez"):
                stack.append({"kind": token, "default": False, "location": location})
                findings.append(
                    Finding(
                        rule_id="REF-XPROP-002",
                        severity="error",
                        message=(
                            f"{token} control flow can mask X/Z selector values "
                            "under strict X policy"
                        ),
                        evidence={"construct": token, "source_location": location},
                    )
                )
            elif token == "case":
                stack.append({"kind": token, "default": False, "location": location})
            elif token == "default" and stack:
                stack[-1]["default"] = True
            elif token == "endcase" and stack:
                case = stack.pop()
                if case["kind"] == "case" and not case["default"]:
                    findings.append(
                        Finding(
                            rule_id="REF-XPROP-002",
                            severity="error",
                            message=(
                                "case control flow has no default branch under "
                                "strict X policy"
                            ),
                            evidence={
                                "construct": "case_without_default",
                                "source_location": case["location"],
                            },
                        )
                    )
            elif token == "==?":
                findings.append(
                    Finding(
                        rule_id="REF-XPROP-002",
                        severity="error",
                        message=(
                            "wildcard equality can mask X/Z control values under "
                            "strict X policy"
                        ),
                        evidence={
                            "construct": "wildcard_equality",
                            "source_location": location,
                        },
                    )
                )
    return findings


def _binary_connection_value(bits: Iterable[int | str]) -> int | None:
    value = 0
    for index, bit in enumerate(bits):
        if bit not in ("0", "1"):
            return None
        if bit == "1":
            value |= 1 << index
    return value


def uninitialized_memories(module: dict[str, Any]) -> list[dict[str, Any]]:
    cells = module.get("cells", {})
    initialized: dict[str, set[int]] = defaultdict(set)
    for cell in cells.values():
        if not str(cell.get("type", "")).startswith("$meminit"):
            continue
        parameters = cell.get("parameters", {})
        memory_id = str(parameters.get("MEMID", "")).lstrip("\\")
        connections = cell.get("connections", {})
        if any(bit != "1" for bit in connections.get("EN", ())):
            continue
        if any(bit not in ("0", "1") for bit in connections.get("DATA", ())):
            continue
        address = _binary_connection_value(connections.get("ADDR", ()))
        words_text = parameters.get("WORDS", "1")
        if address is None or not isinstance(words_text, str):
            continue
        try:
            words = int(words_text, 2)
        except ValueError:
            continue
        initialized[memory_id].update(range(address, address + words))

    missing: list[dict[str, Any]] = []
    for name, memory in module.get("memories", {}).items():
        start = int(memory.get("start_offset", 0))
        size = int(memory.get("size", 0))
        expected = set(range(start, start + size))
        covered = initialized.get(str(name).lstrip("\\"), set())
        if expected and expected <= covered:
            continue
        missing.append(
            {
                "name": name,
                "width": int(memory.get("width", 0)),
                "size": size,
                "initialized_words": len(expected & covered),
                "source_location": str(
                    memory.get("attributes", {}).get("src", "")
                ),
            }
        )
    return missing


def portable_source_location(location: str, manifest: Manifest) -> str:
    prefix = str(manifest.path.parent.resolve()) + "/"
    return location.replace(prefix, "")


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
