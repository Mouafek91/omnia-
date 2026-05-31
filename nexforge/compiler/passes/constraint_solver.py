"""Constraint solver — budget validation."""
from __future__ import annotations
from dataclasses import dataclass
from ..ir import CPSIR, HARDWARE_PROFILES


@dataclass
class BudgetViolation:
    resource: str
    used: float
    limit: float
    unit: str
    message: str


@dataclass
class BudgetReport:
    ok: bool
    violations: list
    breakdown: dict


class ConstraintSolver:
    def __init__(self, ir: CPSIR):
        self.ir = ir
        self.profile = HARDWARE_PROFILES.get(ir.deployment.target)
        self.violations = []
        self.breakdown = {}

    def solve(self):
        if self.profile is None:
            return BudgetReport(False, [BudgetViolation("target", 0, 0, "", "no profile")], {})
        self._timing(); self._ram(); self._cpu(); self._flash()
        return BudgetReport(len(self.violations) == 0, self.violations, self.breakdown)

    def _timing(self):
        t = self.ir.timing
        safety_us = 1_000_000 / t.safety_loop_hz
        wcet = t.wcet_safety_us
        slack = (safety_us - wcet) / safety_us * 100 if safety_us else 0
        self.breakdown["timing"] = {"slack_pct": slack}
        if slack < 20:
            self.violations.append(BudgetViolation(
                "timing_slack", slack, 20.0, "%", f"Only {slack:.1f}% slack"))

    def _ram(self):
        ring = 16 * len(self.ir.sensors) * 4 * 2
        state = len(self.ir.physics.states) * 4
        stacks = 4096 * 3
        heap = 8192
        total = ring + state + stacks + heap
        limit = self.profile.ram_bytes * 0.7
        self.breakdown["ram"] = {"used": total, "limit": limit}
        if total > limit:
            self.violations.append(BudgetViolation("RAM", total, limit, "bytes", "exceeded"))

    def _cpu(self):
        U = self.ir.timing.utilization
        self.breakdown["cpu"] = {"utilization": U}
        if U > 0.78:
            self.violations.append(BudgetViolation("CPU", U, 0.78, "", "RM bound exceeded"))

    def _flash(self):
        est = 50_000 + 2000 * len(self.ir.safety.contracts) + 1000 * len(self.ir.sensors)
        limit = self.profile.flash_bytes * 0.5
        self.breakdown["flash"] = {"estimated": est}
        if est > limit:
            self.violations.append(BudgetViolation("Flash", est, limit, "bytes", "exceeded"))


def solve_constraints(ir: CPSIR):
    return ConstraintSolver(ir).solve()
