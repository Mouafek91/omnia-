"""Runtime safety engine — zero-alloc hot path."""
from __future__ import annotations
from dataclasses import dataclass
from array import array
from ..compiler.ir import CPSIR, SafetyClass, TemporalOp
from ..compiler.expr import parse_and_type
from .temporal import TemporalEngine


@dataclass
class SafetyReport:
    veto: bool
    veto_reason: str | None
    violated_contract: str | None
    veto_critical: bool
    n_violated: int


class SafetyEngine:
    def __init__(self, ir: CPSIR):
        self.ir = ir
        self.contracts = ir.safety.contracts
        self._n = len(self.contracts)
        name_units = {}
        for s in ir.sensors: name_units[s.name] = s.quantity.unit
        for a in ir.actuators: name_units[a.name] = a.quantity.unit
        for sv in ir.physics.states: name_units[sv.name] = sv.unit
        self._assume_exprs = [parse_and_type(c.assume, name_units) for c in self.contracts]
        self._guarantee_exprs = [parse_and_type(c.guarantee, name_units) for c in self.contracts]
        self._temporal = TemporalEngine(self._n)
        self._last_trigger_ms = array("q", [0] * self._n)
        self._report = SafetyReport(False, None, None, False, 0)

    def evaluate(self, readings, now_ms):
        r = self._report
        r.veto = False; r.veto_reason = None
        r.violated_contract = None; r.veto_critical = False; r.n_violated = 0
        any_critical = False
        first_reason = None
        first_contract = None
        for i, c in enumerate(self.contracts):
            try: assume_holds = bool(self._assume_exprs[i].evaluate(readings))
            except Exception: assume_holds = False
            if not assume_holds: continue
            try: guarantee_holds = bool(self._guarantee_exprs[i].evaluate(readings))
            except Exception: guarantee_holds = False
            self._temporal.tick(i, guarantee_holds, now_ms)
            if guarantee_holds: continue
            if c.debounce_ms > 0:
                if now_ms - self._last_trigger_ms[i] < c.debounce_ms: continue
                self._last_trigger_ms[i] = now_ms
            r.n_violated += 1
            if first_reason is None:
                first_reason = f"{c.name}: {c.reason}"
                first_contract = c.name
            if c.safety_class == SafetyClass.CRITICAL or c.safety_level in ("SIL2", "SIL3", "SIL4"):
                any_critical = True
        r.veto = r.n_violated > 0
        r.veto_reason = first_reason
        r.violated_contract = first_contract
        r.veto_critical = any_critical
        return r
