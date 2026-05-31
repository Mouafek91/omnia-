"""Full compiler pipeline v6."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .parser import parse_yaml
from .ir import CPSIR
from .passes.arch_validator import validate_architecture
from .passes.dependency import analyze_dependencies
from .passes.schedulability import check_schedulability
from .passes.hardware import check_hardware
from .passes.constraint_solver import solve_constraints
from .passes.z3_verify import verify_with_z3, VerificationResult
from .passes.statechart import validate_statechart, StatechartError
from .passes.capability_matrix import generate_capabilities


@dataclass
class CompilationReport:
    ir: Optional[CPSIR]
    arch_ok: bool
    schedulable: bool
    hardware_ok: bool
    budget_ok: bool
    z3_result: Optional[VerificationResult]
    errors: list
    warnings: list
    capabilities_md: Optional[str] = None

    @property
    def ok(self) -> bool:
        return (self.arch_ok and self.schedulable and self.hardware_ok and
                self.budget_ok and len(self.errors) == 0 and
                (self.z3_result is None or self.z3_result.ok))


class CompilationError(Exception):
    def __init__(self, report):
        self.report = report
        msg = f"Compilation failed: {len(report.errors)} errors\n"
        msg += "\n".join(f"  ❌ {e}" for e in report.errors)
        if report.warnings:
            msg += "\n" + "\n".join(f"  ⚠️ {w}" for w in report.warnings)
        super().__init__(msg)


def compile_file(path, source_prompt="", generate_caps=True):
    errors = []; warnings = []
    try:
        ir = parse_yaml(path, source_prompt=source_prompt)
    except Exception as e:
        return _fail([f"Parse error: {e}"], warnings)

    arch_violations = validate_architecture(ir)
    errors.extend(str(v) for v in arch_violations if v.severity == "ERROR")
    warnings.extend(str(v) for v in arch_violations if v.severity == "WARNING")
    arch_ok = not any(v.severity == "ERROR" for v in arch_violations)

    try:
        ir = analyze_dependencies(ir)
    except Exception as e:
        errors.append(f"Dependency analysis failed: {e}")

    schedulable = False
    if not errors:
        ir = check_schedulability(ir)
        schedulable = ir.timing.schedulable
        if not schedulable:
            errors.append(f"Task set not schedulable: U={ir.timing.utilization:.3f}")

    hw = check_hardware(ir)
    errors.extend(hw.errors); warnings.extend(hw.warnings)

    budget = solve_constraints(ir)
    if not budget.ok:
        errors.extend(f"Budget: {v.resource}: {v.message}" for v in budget.violations)

    z3_res = verify_with_z3(ir)
    errors.extend(z3_res.errors); warnings.extend(z3_res.warnings)

    try:
        validate_statechart(ir)
    except StatechartError as e:
        errors.append(f"Statechart: {e}")

    caps_md = None
    if generate_caps and not errors:
        try:
            caps_md = generate_capabilities(ir)
        except Exception as e:
            warnings.append(f"Capability matrix failed: {e}")

    report = CompilationReport(
        ir=ir, arch_ok=arch_ok, schedulable=schedulable,
        hardware_ok=hw.ok, budget_ok=budget.ok, z3_result=z3_res,
        errors=errors, warnings=warnings, capabilities_md=caps_md)
    if not report.ok:
        raise CompilationError(report)
    return report


def _fail(errors, warnings):
    report = CompilationReport(
        ir=None, arch_ok=False, schedulable=False, hardware_ok=False,
        budget_ok=False, z3_result=None, errors=errors, warnings=warnings)
    raise CompilationError(report)
