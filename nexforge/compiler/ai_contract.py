"""
AI Contract Layer — formal boundary for what AI can modify.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ModificationZone(str, Enum):
    DOMAIN_YAML = "domain_yaml"
    SCENARIO_LIBRARY = "scenario_library"
    DOCS = "docs"
    TESTS = "tests"
    RUNTIME_KERNEL = "runtime_kernel"
    COMPILER_PASSES = "compiler_passes"
    IR_SCHEMA = "ir_schema"
    ARCH_VALIDATOR = "arch_validator"
    SAFE_EVAL = "safe_eval"


@dataclass(frozen=True)
class AIContract:
    required_sections: tuple = (
        "metadata", "sensors", "actuators", "physics",
        "contracts", "control", "timing", "deployment",
    )
    minimum_contracts: int = 1
    minimum_critical_contracts: int = 1
    require_reason_ar_on_critical: bool = True
    forbidden_tokens: tuple = (
        "import", "exec", "eval", "open", "compile",
        "getattr", "setattr", "lambda", "class", "def", "global", "__",
    )
    forbidden_zones: tuple = (
        ModificationZone.RUNTIME_KERNEL,
        ModificationZone.COMPILER_PASSES,
        ModificationZone.IR_SCHEMA,
        ModificationZone.ARCH_VALIDATOR,
        ModificationZone.SAFE_EVAL,
    )
    require_units_on_all_sensors: bool = True
    require_failsafe_on_all_actuators: bool = True

    def validate_yaml(self, yaml_dict: dict) -> list:
        violations = []
        for section in self.required_sections:
            if section not in yaml_dict:
                violations.append(f"Missing required section: {section}")
        contracts = yaml_dict.get("contracts", [])
        if len(contracts) < self.minimum_contracts:
            violations.append(f"Need ≥{self.minimum_contracts} contracts")
        critical_count = sum(
            1 for c in contracts
            if c.get("safety_class") == "CRITICAL"
            or c.get("safety_level", "SIL1") in ("SIL2", "SIL3", "SIL4"))
        if critical_count < self.minimum_critical_contracts:
            violations.append(f"Need ≥{self.minimum_critical_contracts} critical contracts")
        if self.require_reason_ar_on_critical:
            for c in contracts:
                is_critical = (c.get("safety_class") == "CRITICAL" or
                               c.get("safety_level", "SIL1") in ("SIL2", "SIL3", "SIL4"))
                if is_critical and not c.get("reason_ar"):
                    violations.append(f"Critical contract '{c.get('name')}' missing reason_ar")
        if self.require_units_on_all_sensors:
            for s in yaml_dict.get("sensors", []):
                if "unit" not in s:
                    violations.append(f"Sensor '{s.get('name')}' missing unit")
        if self.require_failsafe_on_all_actuators:
            for a in yaml_dict.get("actuators", []):
                if "fail_safe_value" not in a:
                    violations.append(f"Actuator '{a.get('name')}' missing fail_safe_value")
        return violations

    def to_markdown(self) -> str:
        return """# NexForge AI Contract

AI may modify **only**:
- `domains/*.yaml` — domain specifications
- `scenarios/` — fault scenarios
- `docs/` — documentation
- `tests/` — test files

AI is **forbidden** from modifying:
- Runtime kernel
- Compiler passes
- IR schema
- Architecture validator
- Safe evaluator

## Required properties

- ≥ 1 contract, ≥ 1 CRITICAL/SIL2+ contract
- All sensors must have a `unit`
- All actuators must have a `fail_safe_value` within range
- All critical contracts must have a `reason_ar`
- All expressions must avoid forbidden tokens

## Forbidden tokens
`import`, `exec`, `eval`, `open`, `compile`, `getattr`, `setattr`,
`lambda`, `class`, `def`, `global`, `__`
"""


CONTRACT = AIContract()
