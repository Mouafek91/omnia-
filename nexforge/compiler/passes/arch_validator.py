"""
Architecture Validator — enforces the 12 architectural rules.
"""
from __future__ import annotations
from dataclasses import dataclass
from ..ir import CPSIR
from ..expr import parse_untyped, ExpressionError


@dataclass(frozen=True)
class ArchViolation:
    rule: str
    severity: str
    location: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule} @ {self.location}: {self.message}"


class ArchitectureValidator:
    def __init__(self, ir: CPSIR):
        self.ir = ir
        self.violations: list = []

    def _err(self, rule, loc, msg, sev="ERROR"):
        self.violations.append(ArchViolation(rule, sev, loc, msg))

    def validate(self) -> list:
        self._R01_completeness()
        self._R02_unique_names()
        self._R03_contract_references()
        self._R04_physics_references()
        self._R05_actuator_failsafe()
        self._R06_debounce_bounds()
        self._R07_no_physics_cycles()
        self._R08_control_references()
        self._R09_fault_regions_resolve()
        self._R10_temporal_bounds()
        self._R11_sensor_rates()
        self._R12_critical_contracts_have_reason()
        return list(self.violations)

    def _R01_completeness(self):
        ir = self.ir
        if not ir.sensors: self._err("R01", "sensors", "Domain has no sensors")
        if not ir.actuators: self._err("R01", "actuators", "Domain has no actuators")
        if not ir.safety.contracts: self._err("R01", "safety.contracts", "Domain has no contracts")
        if not ir.physics.derivatives: self._err("R01", "physics.derivatives", "No physics equations", "WARNING")

    def _R02_unique_names(self):
        all_names = []
        for s in self.ir.sensors:
            all_names.append((s.name, f"sensors.{s.name}"))
        for a in self.ir.actuators:
            all_names.append((a.name, f"actuators.{a.name}"))
        for sv in self.ir.physics.states:
            all_names.append((sv.name, f"physics.states.{sv.name}"))
            
        seen = {}
        for name, loc in all_names:
            if name in seen:
                prev_loc = seen[name]
                # Allow physics states to share names with sensors (state vs measurement)
                is_sensor_state = ("sensors." in prev_loc and "physics.states." in loc) or \
                                  ("physics.states." in prev_loc and "sensors." in loc)
                if not is_sensor_state:
                    self._err("R02", loc, f"Duplicate name '{name}' (also at {seen[name]})")
                continue
            seen[name] = loc

    def _R03_contract_references(self):
        known = (set(self.ir.sensor_names()) | set(self.ir.actuator_names()) |
                 set(self.ir.state_names()))
        allowed = known | {"_any_critical_veto", "_any_important_veto", 
                           "critical_veto_active", "important_veto_active"}
        for i, c in enumerate(self.ir.safety.contracts):
            for field_name in ("assume", "guarantee"):
                expr = getattr(c, field_name)
                try:
                    names = parse_untyped(expr).free_names
                except ExpressionError as e:
                    self._err("R03", f"contracts[{i}].{field_name}", f"Parse error: {e}")
                    continue
                missing = names - allowed
                if missing:
                    self._err("R03", f"contracts[{i}].{field_name}",
                              f"References undeclared symbols: {sorted(missing)}")

    def _R04_physics_references(self):
        known = (set(self.ir.sensor_names()) | set(self.ir.actuator_names()) |
                 set(self.ir.state_names()))
        for d in self.ir.physics.derivatives:
            try:
                names = parse_untyped(d.expression).free_names
            except ExpressionError as e:
                self._err("R04", f"physics.derivatives.{d.state}", f"Parse error: {e}")
                continue
            missing = names - known
            if missing:
                self._err("R04", f"physics.derivatives.{d.state}",
                          f"References undeclared: {sorted(missing)}")

    def _R05_actuator_failsafe(self):
        for i, a in enumerate(self.ir.actuators):
            if not a.quantity.contains(a.fail_safe_value):
                self._err("R05", f"actuators[{i}].{a.name}",
                          f"fail_safe_value {a.fail_safe_value} outside "
                          f"[{a.quantity.min}, {a.quantity.max}]")

    def _R06_debounce_bounds(self):
        for i, c in enumerate(self.ir.safety.contracts):
            if c.debounce_ms < 0:
                self._err("R06", f"contracts[{i}].{c.name}", "debounce_ms must be ≥ 0")

    def _R07_no_physics_cycles(self):
        from collections import defaultdict, deque
        edges = []
        state_names = set(self.ir.state_names())
        for d in self.ir.physics.derivatives:
            try:
                names = parse_untyped(d.expression).free_names
            except ExpressionError: continue
            for dep in names & state_names:
                if dep != d.state:
                    edges.append((dep, d.state))
        g = defaultdict(list); indeg = defaultdict(int); nodes = set()
        for u, v in edges:
            g[u].append(v); indeg[v] += 1; nodes.add(u); nodes.add(v)
        q = deque(n for n in nodes if indeg[n] == 0)
        seen = 0
        while q:
            n = q.popleft(); seen += 1
            for m in g[n]:
                indeg[m] -= 1
                if indeg[m] == 0: q.append(m)
        if seen < len(nodes):
            self._err("R07", "physics.derivatives", "Circular dependency detected")

    def _R08_control_references(self):
        ctrl = self.ir.control
        if ctrl.target_sensor and ctrl.target_sensor not in self.ir.sensor_names():
            self._err("R08", "control.target_sensor", f"'{ctrl.target_sensor}' not in sensors")
        if ctrl.output_actuator and ctrl.output_actuator not in self.ir.actuator_names():
            self._err("R08", "control.output_actuator", f"'{ctrl.output_actuator}' not in actuators")

    def _R09_fault_regions_resolve(self):
        declared = {r.name for r in self.ir.faults.regions}
        for s in self.ir.sensors:
            if s.fault_region not in declared:
                self._err("R09", f"sensors.{s.name}", f"fault_region '{s.fault_region}' undeclared")
        for a in self.ir.actuators:
            if a.fault_region not in declared:
                self._err("R09", f"actuators.{a.name}", f"fault_region '{a.fault_region}' undeclared")
        for c in self.ir.safety.contracts:
            if c.fault_region not in declared:
                self._err("R09", f"contracts.{c.name}", f"fault_region '{c.fault_region}' undeclared")

    def _R10_temporal_bounds(self):
        for i, c in enumerate(self.ir.safety.contracts):
            for kind in ("assume_temporal", "guarantee_temporal"):
                tb = getattr(c, kind)
                if tb.duration_ms < 0:
                    self._err("R10", f"contracts[{i}].{kind}", "duration_ms must be ≥ 0")

    def _R11_sensor_rates(self):
        min_rate = self.ir.timing.safety_loop_hz / 10.0
        for s in self.ir.sensors:
            if s.quantity.rate_hz < min_rate:
                self._err("R11", f"sensors.{s.name}", f"rate_hz={s.quantity.rate_hz} below min {min_rate:.1f}")

    def _R12_critical_contracts_have_reason(self):
        for i, c in enumerate(self.ir.safety.contracts):
            is_critical = (c.safety_class.value == "CRITICAL" or c.safety_level in ("SIL2", "SIL3", "SIL4"))
            if is_critical and not c.reason_ar:
                self._err("R12", f"contracts[{i}].{c.name}", "Critical contract missing reason_ar")


def validate_architecture(ir: CPSIR) -> list:
    return ArchitectureValidator(ir).validate()