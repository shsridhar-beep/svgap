from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, FrozenSet, Optional, Tuple

from najaeda import naja

from svgap.model import CheckResult, Finding, Manifest

# ---------------------------------------------------------------------------
# Raw naja load boundary (mirrors naja-scope's src/naja_scope/loader.py).
# svgap depends on najaeda directly here -- this is a self-contained port,
# not an import of naja-scope.
# ---------------------------------------------------------------------------


def _get_top_db():
    if naja.NLUniverse.get() is None:
        naja.NLUniverse.create()
    universe = naja.NLUniverse.get()
    if universe.getTopDB() is None:
        db = naja.NLDB.create(universe)
        universe.setTopDB(db)
    return universe.getTopDB()


def _reset_universe() -> None:
    universe = naja.NLUniverse.get()
    if universe is not None:
        universe.destroy()


def _load_systemverilog(files: list[str], top: str) -> None:
    db = _get_top_db()
    temp_flist = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".f", delete=False, encoding="utf-8"
        ) as f:
            temp_flist = f.name
            f.write(f"--top {top}\n")
        db.loadSystemVerilog(
            files,
            keep_assigns=True,
            flist=temp_flist,
            keep_ast_link=False,
            diagnostics_report_path=None,
        )
    finally:
        if temp_flist and os.path.exists(temp_flist):
            os.remove(temp_flist)


def _najaeda_version() -> str:
    try:
        return version("najaeda")
    except PackageNotFoundError:
        return "unknown"


# ---------------------------------------------------------------------------
# Raw SNL identity/label helpers (mirrors naja-scope's src/naja_scope/snl.py
# inst_segment / friendly_label; adapted for these flat, single-module
# fixtures -- no hierarchy path is needed).
# ---------------------------------------------------------------------------

DIR_INPUT = naja.SNLTerm.Direction.Input
DIR_OUTPUT = naja.SNLTerm.Direction.Output

_ROLE_NAMES = {
    getattr(naja.SNLTermRole, name): name
    for name in dir(naja.SNLTermRole)
    if not name.startswith("_")
}


def _role_str(role) -> Optional[str]:
    name = _ROLE_NAMES.get(role)
    if name is None or name == "Other":
        return None
    return name


_SANITIZE_RE = re.compile(r"\W+")


def _inst_segment(inst) -> str:
    name = inst.getName()
    return name if name else f"#{inst.getID()}"


def _friendly_label(inst) -> str:
    name = inst.getName()
    if name:
        return name
    model = inst.getModel().getName() or "u"
    base = model[5:] if model.startswith("naja_") else model
    for it in inst.getInstTerms():
        if it.getBitTerm().getDirection() != DIR_OUTPUT:
            continue
        net = it.getNet()
        if net is None:
            continue
        net_name = net.getName()
        if not net_name:
            continue
        net_name = _SANITIZE_RE.sub("_", net_name).strip("_")
        if net_name:
            return f"{net_name}_{base}"
    return base


def _source_loc(obj) -> Optional[str]:
    if obj is None or not hasattr(obj, "hasSourceLoc"):
        return None
    try:
        if not obj.hasSourceLoc():
            return None
        file, line, _column, _end_line, _end_column = obj.getSourceLoc()
    except Exception:
        return None
    if not file:
        return None
    return f"{file}:{line}"


def _source_location(inst, manifest: Manifest) -> str:
    loc = _source_loc(inst)
    if loc is None:
        return ""
    # naja/slang's source location records the file path relative to the
    # calling process's current working directory (a slang diagnostics-engine
    # convention), not relative to the manifest directory the way Yosys's
    # (always-absolute) `src` attribute is -- normalise via an absolute path
    # before stripping the manifest prefix, so the result is independent of
    # the caller's cwd.
    file_part, _, rest = loc.partition(":")
    absolute = str(Path(file_part).resolve())
    prefix = str(manifest.path.parent.resolve()) + "/"
    if absolute.startswith(prefix):
        file_part = absolute[len(prefix):]
    return f"{file_part}:{rest}" if rest else file_part


# ---------------------------------------------------------------------------
# Sequential-cell model: one entry per raw naja sequential leaf instance
# (`naja_dff`/`naja_dffrn` and their wide `__wN` forms). A wide instance is
# already the multi-bit register as a whole -- the direct analog of Yosys's
# (inherently vectorized) SeqCell, so no extra bit-grouping is needed here.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SeqReg:
    inst: Any
    label: str
    clock_name: str
    d_nets: Tuple[Any, ...]
    q_nets: Tuple[Any, ...]
    reset_net: Optional[Any]


def _bit_terms_by_role(inst, role: str):
    """(bit_index_or_None, net) pairs for every InstTerm of `inst` whose bit
    term has the given pin role, ordered by bit index (scalar pins sort as
    a single (None, net) entry)."""
    out = []
    for it in inst.getInstTerms():
        bt = it.getBitTerm()
        if _role_str(bt.getRole()) != role:
            continue
        try:
            bit = bt.getBit()
        except Exception:
            bit = None
        out.append((bit, it.getNet()))
    out.sort(key=lambda pair: (pair[0] is None, pair[0]))
    return out


def _build_seq_regs(design, clock_by_net_id: dict) -> list[SeqReg]:
    seq_regs = []
    for inst in design.getInstances():
        model = inst.getModel()
        if not model.isSequential():
            continue
        d_pairs = _bit_terms_by_role(inst, "DataInput")
        q_pairs = _bit_terms_by_role(inst, "DataOutput")
        clock_nets = [n for _bit, n in _bit_terms_by_role(inst, "Clock")]
        reset_nets = [n for _bit, n in _bit_terms_by_role(inst, "AsyncReset")]
        clock_name = "<undeclared>"
        if clock_nets and clock_nets[0] is not None:
            clock_name = clock_by_net_id.get(clock_nets[0], "<undeclared>")
        seq_regs.append(
            SeqReg(
                inst=inst,
                label=_inst_segment(inst),
                clock_name=clock_name,
                d_nets=tuple(n for _bit, n in d_pairs),
                q_nets=tuple(n for _bit, n in q_pairs),
                reset_net=reset_nets[0] if reset_nets else None,
            )
        )
    return seq_regs


# ---------------------------------------------------------------------------
# Backward/forward walks -- the raw-naja replacement for reference_yosys.py's
# comb_driver + trace_sequential_sources + same_domain_successors +
# combinational_cone_types, built directly on net/instTerm driver lookups
# rather than a prebuilt id->driver map (the naja equivalent, an
# SNLEquipotential/driver walk, is cheap to do on demand for these flat,
# single-module designs).
# ---------------------------------------------------------------------------


def _driving_inst_term(net):
    """The sole output-direction InstTerm driving `net`, or None (primary
    input / unconnected -- a dead end, exactly like Yosys's comb_driver.get()
    returning None for a bit with no cell driver)."""
    if net is None:
        return None
    for it in net.getInstTerms():
        if it.getDirection() == DIR_OUTPUT:
            return it
    return None


def _input_nets(inst) -> list:
    nets = []
    for it in inst.getInstTerms():
        if it.getDirection() == DIR_INPUT:
            n = it.getNet()
            if n is not None:
                nets.append(n)
    return nets


def _trace_sequential_sources(
    net, seq_by_qnet: dict, visited: FrozenSet[Any]
) -> list[Tuple[SeqReg, Tuple[Tuple[str, str], ...]]]:
    """Bit-level backward walk from `net`, mirroring reference_yosys.py's
    trace_sequential_sources(): only branches that actually reach a
    sequential source contribute comb-cell path entries. `assign` glue
    instances (naja's explicit net-aliasing leaves -- Yosys has no equivalent
    cell for a plain continuous assignment) are transparent: crossed but
    never recorded, since they carry no real logic.

    `visited`/the various `*_by_*net` maps below key directly on the net
    object (not `id(net)`): naja's Python wrappers are transient and can be
    garbage-collected and have their `id()` reused once no Python reference
    is held, but the wrapper's `__eq__`/`__hash__` are tied to the underlying
    SNL object identity, so the object itself is the safe map key."""
    if net is None or net in visited:
        return []
    if net.isConstant():
        return []
    driver = _driving_inst_term(net)
    if driver is None:
        return []
    inst = driver.getInstance()
    model = inst.getModel()
    seqreg = seq_by_qnet.get(net)
    if model.isSequential():
        return [(seqreg, ())] if seqreg is not None else []
    transparent = model.isAssign()
    new_visited = visited | {net}
    found: list[Tuple[SeqReg, Tuple[Tuple[str, str], ...]]] = []
    for input_net in _input_nets(inst):
        for source, path in _trace_sequential_sources(input_net, seq_by_qnet, new_visited):
            if transparent:
                found.append((source, path))
            else:
                found.append((source, ((_inst_segment(inst), model.getName()), *path)))
    return found


def _same_domain_successors(
    reg: SeqReg, seq_by_dnet: dict, visited: Optional[set] = None
) -> list[SeqReg]:
    """Forward walk from `reg`'s Q nets, mirroring same_domain_successors():
    only continues through `naja_mux*` selects and `assign` glue (Yosys's
    $mux/$pmux allowance), stopping at (and recording) any consumer register
    in the same clock domain."""
    found: dict[str, SeqReg] = {}
    visited = visited if visited is not None else set()
    frontier = list(reg.q_nets)
    while frontier:
        net = frontier.pop()
        if net is None or net in visited:
            continue
        visited.add(net)
        for it in net.getInstTerms():
            if it.getDirection() != DIR_INPUT:
                continue
            inst = it.getInstance()
            model = inst.getModel()
            consumer = seq_by_dnet.get(net)
            if consumer is not None and consumer.inst != reg.inst and consumer.clock_name == reg.clock_name:
                found[consumer.label] = consumer
                continue
            if model.isAssign() or model.getName().startswith("naja_mux"):
                for out_it in inst.getInstTerms():
                    if out_it.getDirection() == DIR_OUTPUT:
                        out_net = out_it.getNet()
                        if out_net is not None:
                            frontier.append(out_net)
    return list(found.values())


def _cone_types(net, visited: FrozenSet[Any]) -> set:
    """Full fanin closure of leaf models, stopping at sequential
    boundaries or dead ends -- mirrors combinational_cone_types(), which
    (unlike trace_sequential_sources) records every branch regardless of
    whether it reaches a sequential source."""
    if net is None or net in visited:
        return set()
    if net.isConstant():
        return set()
    driver = _driving_inst_term(net)
    if driver is None:
        return set()
    inst = driver.getInstance()
    model = inst.getModel()
    if model.isSequential():
        return set()
    new_visited = visited | {net}
    types = set() if model.isAssign() else {model}
    for input_net in _input_nets(inst):
        types |= _cone_types(input_net, new_visited)
    return types


def _is_mux(model_name: str) -> bool:
    return model_name.startswith("naja_mux")


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class ReferenceNajaBackend:
    """Structural oracle equivalent to ReferenceYosysBackend, built on raw
    naja (`from najaeda import naja`) instead of shelling out to Yosys.

    Known naja-specific modeling gaps vs. the Yosys reference, all confirmed
    empirically against svgap's own example fixtures (najaeda 0.7.11):

    * Synchronous-reset polarity: `if (!rst_n)` lowers, via slang, to an
      explicit `not_1` gate feeding a `naja_muxN` select pin. Yosys's `proc`
      pass instead folds the polarity into which mux input is the reset
      value, with no separate NOT cell. This never affects a finding here:
      the polarity NOT's own fanin always dead-ends at the reset port (no
      sequential driver), so it never contributes a comb-path entry under
      the trace-only-successful-branches algorithm below -- no special-
      casing needed.
    * Continuous net aliases (`wire x = y;`) lower to an explicit `assign`
      leaf instance in naja; Yosys has no equivalent cell for a plain
      alias. `assign` is treated as transparent glue in both the backward
      and forward walks (crossed but never recorded), matching Yosys's
      hazard semantics, since it carries no real logic.
    * `SNLDesign.getTruthTable()` cannot distinguish XOR/AND/OR/NAND/NOR/
      XNOR from each other for naja's *generic* N-ary gate family, since the
      C++ `SNLTruthTable` stores these via a `GenericType` tag rather than
      an explicit bit mask. XOR identification below uses `SNLDesign.isXor()`
      instead, which naja resolves from that tag directly. Mux has no
      equivalent `isMux()`, so it still falls back to naja's stable NLDB0
      primitive naming (`naja_mux2`, ...), the same kind of cell-type-string
      identity Yosys's `$mux` check already relies on.
    """

    name = "reference-naja"
    version = "0.1"

    def check(self, manifest: Manifest) -> CheckResult:
        tool_versions = {"najaeda": _najaeda_version()}
        _reset_universe()
        try:
            _load_systemverilog([str(p) for p in manifest.sources], top=manifest.top)
        except Exception as exc:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"cannot elaborate SystemVerilog: {exc}"],
                tool_versions=tool_versions,
            )
        try:
            universe = naja.NLUniverse.get()
            design = universe.getTopDesign()
            if design is None:
                raise RuntimeError("no top design after elaboration")
            result = self._analyze(manifest, design)
            result.tool_versions = tool_versions
            return result
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            return CheckResult(
                status="tool_error",
                backend=self.name,
                backend_version=self.version,
                diagnostics=[f"cannot analyze naja netlist: {exc}"],
                tool_versions=tool_versions,
            )

    def _analyze(self, manifest: Manifest, design) -> CheckResult:
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

        clock_by_net: dict = {}
        for clock in manifest.clocks:
            net = _scalar_port_net(design, clock.port)
            if net is None:
                diagnostics.append(f"clock port {clock.port!r} is missing or not scalar")
            else:
                clock_by_net[net] = clock.name

        reset_by_net: dict = {}
        for reset in manifest.resets:
            net = _scalar_port_net(design, reset.port)
            if net is None:
                diagnostics.append(f"reset port {reset.port!r} is missing or not scalar")
            else:
                reset_by_net[net] = reset

        seq_regs = _build_seq_regs(design, clock_by_net)
        if any(reg.clock_name == "<undeclared>" for reg in seq_regs):
            diagnostics.append("one or more state elements use an undeclared or unsupported clock")

        seq_by_qnet = {q: reg for reg in seq_regs for q in reg.q_nets}
        seq_by_dnet = {d: reg for reg in seq_regs for d in reg.d_nets}
        recognized_reset_sync = _reset_synchronizer_regs(seq_regs, reset_by_net)

        crossings: dict[Tuple[str, str], dict[str, Any]] = {}
        for dst in seq_regs:
            if dst.clock_name == "<undeclared>":
                continue
            for d_net in dst.d_nets:
                for src, comb_path in _trace_sequential_sources(d_net, seq_by_qnet, frozenset()):
                    if src is None or src.clock_name in ("<undeclared>", dst.clock_name):
                        continue
                    if not _are_asynchronous(src.clock_name, dst.clock_name, manifest.asynchronous_groups):
                        continue
                    item = crossings.setdefault(
                        (src.label, dst.label),
                        {"src": src, "dst": dst, "bits": set(), "comb": set()},
                    )
                    item["bits"].add(d_net)
                    item["comb"].update(comb_path)

        for item in crossings.values():
            src: SeqReg = item["src"]
            dst: SeqReg = item["dst"]
            width = len(item["bits"])
            second_stages = _same_domain_successors(dst, seq_by_dnet)
            evidence = {
                "source_cell": src.label,
                "source_label": _friendly_label(src.inst),
                "source_clock": src.clock_name,
                "destination_cell": dst.label,
                "destination_label": _friendly_label(dst.inst),
                "destination_clock": dst.clock_name,
                "width": width,
                "source_location": _source_location(src.inst, manifest),
                "destination_location": _source_location(dst.inst, manifest),
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
                label for label, model_name in item["comb"] if not _is_mux(model_name)
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
            if width > 1 and not _declared_coherent_protocol(manifest, src, second_stages):
                findings.append(
                    Finding(
                        rule_id="REF-CDC-003",
                        severity="error",
                        message="multi-bit asynchronous crossing uses independent synchronizer stages without declared coherence protocol",
                        evidence=evidence,
                    )
                )

        for reg in seq_regs:
            if reg.reset_net is None:
                continue
            reset = reset_by_net.get(reg.reset_net)
            if reset is None or reset.deassertion != "sync":
                continue
            if reg.inst in recognized_reset_sync:
                continue
            findings.append(
                Finding(
                    rule_id="REF-RDC-001",
                    severity="error",
                    message="raw asynchronous reset reaches an unmarked state element although synchronous deassertion is required",
                    evidence={
                        "cell": reg.label,
                        "label": _friendly_label(reg.inst),
                        "clock": reg.clock_name,
                        "reset": reset.name,
                        "source_location": _source_location(reg.inst, manifest),
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


def _scalar_port_net(design, name: str):
    try:
        term = design.getTerm(name)
    except Exception:
        return None
    if term is None:
        return None
    try:
        if term.getWidth() != 1:
            return None
    except Exception:
        pass
    try:
        return term.getNet()
    except Exception:
        return None


def _are_asynchronous(source: str, destination: str, groups: list[list[str]]) -> bool:
    source_groups = {index for index, group in enumerate(groups) if source in group}
    destination_groups = {index for index, group in enumerate(groups) if destination in group}
    return bool(source_groups and destination_groups and source_groups.isdisjoint(destination_groups))


def _bus_bits(design, name: str) -> set:
    try:
        net = design.getNet(name)
    except Exception:
        net = None
    if net is None:
        return set()
    try:
        return set(net.getBits())
    except Exception:
        return {net}


def _declared_coherent_protocol(manifest: Manifest, source: SeqReg, second_stages: list[SeqReg]) -> bool:
    top_design = naja.NLUniverse.get().getTopDesign()
    downstream = {q for reg in second_stages for q in reg.q_nets}
    for crossing in manifest.crossings:
        if crossing.protocol != "gray":
            continue
        declared_source = (
            set(source.q_nets) if crossing.source == "*" else _bus_bits(top_design, crossing.source)
        )
        if not (set(source.q_nets) & declared_source):
            continue
        declared_destination = (
            downstream if crossing.destination == "*" else _bus_bits(top_design, crossing.destination)
        )
        if not (downstream & declared_destination):
            continue
        source_d_nets = [
            d
            for q, d in zip(source.q_nets, source.d_nets)
            if q in declared_source
        ]
        cone_types: set = set()
        for d_net in source_d_nets:
            cone_types |= _cone_types(d_net, frozenset())
        if any(model.isXor() for model in cone_types):
            return True
    return False


def _reset_synchronizer_regs(seq_regs: list[SeqReg], reset_by_net: dict) -> set:
    """Recognize a conventional two-flop asynchronous-assert reset
    synchronizer: a single-bit first stage whose D is tied to the reset's
    *inactive* constant value, feeding a single-bit second stage's D
    directly (no combinational logic in between), both sharing the same
    async reset net. Mirrors reset_synchronizer_bits(); the Yosys reference's
    extra "one wide vector-shift $adff cell" fallback has no analog here --
    naja lowers explicit multi-flop reset synchronizers as separate scalar
    instances in every fixture observed, so it is not ported.

    Evaluated (najaeda 0.7.12) and rejected: strengthening this via the new
    model-level `SNLDesign.getAsyncResetTerms()`/`getSyncResetTerms()`/etc.
    role accessors, confirming a flop's reset pin is really in the
    async-reset role class before trusting `reset_net`. `reset_net` here is
    already sourced exclusively from term-level `SNLTermRole.AsyncReset`
    (see `_bit_terms_by_role(inst, "AsyncReset")` in `_build_seq_regs`) --
    equally sound (both trace back to the same primitive's own role
    annotation, not a name guess), and empirically identical: for every
    AsyncReset-tagged bit term observed in this repo's fixtures, that exact
    term object is also a member of its model's own `getAsyncResetTerms()`
    list. The model-level accessor would re-confirm a fact already
    established via an equally sound term-level path, not add one -- so it
    is not adopted here."""
    recognized: set = set()
    by_qnet = {q: reg for reg in seq_regs for q in reg.q_nets}
    for second in seq_regs:
        if len(second.q_nets) != 1 or len(second.d_nets) != 1 or second.reset_net is None:
            continue
        first = by_qnet.get(second.d_nets[0])
        if first is None or first.inst == second.inst:
            continue
        if (
            len(first.q_nets) != 1
            or len(first.d_nets) != 1
            or first.reset_net is None
            or first.reset_net != second.reset_net
        ):
            continue
        reset = reset_by_net.get(first.reset_net)
        if reset is None:
            continue
        d_net = first.d_nets[0]
        inactive_ok = d_net.isConstant1() if reset.active == "low" else d_net.isConstant0()
        if not inactive_ok:
            continue
        recognized.add(first.inst)
        recognized.add(second.inst)
    return recognized
