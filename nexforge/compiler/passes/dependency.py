"""Dependency analysis + Mermaid export."""
from __future__ import annotations
from collections import defaultdict
from ..ir import CPSIR
from ..expr import parse_untyped, ExpressionError


class DependencyGraph:
    def __init__(self):
        self._edges = []
        self._adj = defaultdict(list)
        self._radj = defaultdict(list)

    def add_edge(self, src, dst, kind=""):
        self._edges.append((src, dst, kind))
        self._adj[src].append(dst)
        self._radj[dst].append(src)

    @property
    def nodes(self):
        return set(self._adj) | set(self._radj)

    def influences(self, source):
        visited = set(); stack = [source]
        while stack:
            n = stack.pop()
            for m in self._adj.get(n, []):
                if m not in visited:
                    visited.add(m); stack.append(m)
        return visited

    def to_mermaid(self, title="NexForge Dependency Graph"):
        lines = [f"%% {title}", "graph TD"]
        for src, dst, kind in self._edges:
            label = f"|{kind}|" if kind else ""
            lines.append(f"    {_q(src)} --> {label} {_q(dst)}")
        return "\n".join(lines)


def _q(s):
    clean = s.replace(":", "_").replace(".", "_")
    return f"{clean}[{s}]"


def build_dependency_graph(ir: CPSIR) -> DependencyGraph:
    g = DependencyGraph()
    for d in ir.physics.derivatives:
        try:
            names = parse_untyped(d.expression).free_names
        except ExpressionError:
            continue
        for dep in names:
            g.add_edge(dep, d.state, kind="physics")
    for c in ir.safety.contracts:
        for field_name in ("assume", "guarantee"):
            try:
                names = parse_untyped(getattr(c, field_name)).free_names
            except ExpressionError:
                continue
            for dep in names:
                g.add_edge(dep, f"contract:{c.name}", kind=field_name)
    for d in ir.physics.disturbances:
        g.add_edge(f"disturbance:{d.name}", d.affects, kind="disturbance")
    if ir.control.target_sensor:
        g.add_edge(ir.control.target_sensor, "control", kind="control")
    if ir.control.output_actuator:
        g.add_edge("control", ir.control.output_actuator, kind="control")
    return g


def analyze_dependencies(ir: CPSIR) -> CPSIR:
    """Fill topo_order + depends_on; prune dead equations."""
    from ..ir import PhysicsGraph, Derivative, SafetyGraph, Contract
    from dataclasses import replace
    from .units_helper import build_name_units

    name_units = build_name_units(ir)
    deriv_deps = []
    for d in ir.physics.derivatives:
        try:
            typed = parse_untyped(d.expression)
            deriv_deps.append((d.state, typed.free_names))
        except ExpressionError:
            deriv_deps.append((d.state, frozenset()))

    contract_deps = []
    for c in ir.safety.contracts:
        try:
            a = parse_untyped(c.assume).free_names
            g = parse_untyped(c.guarantee).free_names
            contract_deps.append((c.name, a | g))
        except ExpressionError:
            contract_deps.append((c.name, frozenset()))

    edges = []
    for state, deps in deriv_deps:
        for dep in deps:
            if dep in {d[0] for d in deriv_deps}:
                edges.append((dep, state))

    # Topo sort
    from collections import defaultdict, deque
    g = defaultdict(list)
    indeg = {d[0]: 0 for d in deriv_deps}
    for u, v in edges:
        if u in indeg and v in indeg:
            g[u].append(v); indeg[v] += 1
    q = deque(n for n in indeg if indeg[n] == 0)
    topo = []
    while q:
        n = q.popleft(); topo.append(n)
        for m in g[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    for n in indeg:
        if n not in topo:
            topo.append(n)

    new_derivs = tuple(
        replace(d, depends_on=tuple(deps))
        for d, (state, deps) in zip(ir.physics.derivatives, deriv_deps))
    new_contracts = tuple(
        replace(c, depends_on=tuple(deps))
        for c, (name, deps) in zip(ir.safety.contracts, contract_deps))

    new_physics = replace(ir.physics, derivatives=new_derivs, topo_order=tuple(topo))
    new_safety = replace(ir.safety, contracts=new_contracts)
    return replace(ir, physics=new_physics, safety=new_safety)
