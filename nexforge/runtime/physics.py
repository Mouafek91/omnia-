"""
RK4 physics integrator with proper disturbance handling.
"""
from __future__ import annotations
from ..compiler.ir import PhysicsGraph
from ..compiler.expr import parse_untyped


class PhysicsEngine:
    def __init__(self, graph: PhysicsGraph, name_units: dict = None):
        self.graph = graph
        self.state = {sv.name: sv.initial for sv in graph.states}
        self._deriv_exprs = {d.state: parse_untyped(d.expression) for d in graph.derivatives}
        self._topo = list(graph.topo_order) or [d.state for d in graph.derivatives]

    def step(self, inputs: dict, dt: float, disturbances: dict | None = None) -> dict:
        """
        One RK4 step with instantaneous fault injection.
        Disturbances directly override state BEFORE integration.
        """
        # 1. Apply instantaneous disturbance overrides (e.g., motor stall)
        if disturbances:
            for k, v in disturbances.items():
                if k in self.state:
                    self.state[k] = v

        # 2. RK4 integration
        k1 = self._derivs(inputs)
        saved = dict(self.state)
        for v in self.state: self.state[v] = saved[v] + 0.5 * dt * k1[v]
        k2 = self._derivs(inputs)
        for v in self.state: self.state[v] = saved[v] + 0.5 * dt * k2[v]
        k3 = self._derivs(inputs)
        for v in self.state: self.state[v] = saved[v] + dt * k3[v]
        k4 = self._derivs(inputs)
        for v in self.state:
            self.state[v] = saved[v] + (dt / 6.0) * (k1[v] + 2*k2[v] + 2*k3[v] + k4[v])
        return dict(self.state)

    def _derivs(self, inputs: dict) -> dict:
        ctx = dict(self.state)
        ctx.update(inputs)
        out = {}
        for v in self._topo:
            try:
                out[v] = float(self._deriv_exprs[v].evaluate(ctx))
            except Exception:
                out[v] = 0.0
        return out
