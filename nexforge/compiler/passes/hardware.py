"""Hardware capability check."""
from __future__ import annotations
from dataclasses import dataclass
from ..ir import CPSIR, HARDWARE_PROFILES


@dataclass
class HardwareCheckResult:
    ok: bool
    errors: list
    warnings: list


def check_hardware(ir: CPSIR):
    errors, warnings = [], []
    profile = HARDWARE_PROFILES.get(ir.deployment.target)
    if profile is None:
        errors.append(f"No profile for {ir.deployment.target}")
        return HardwareCheckResult(False, errors, warnings)

    adc_used = sum(1 for s in ir.sensors if s.hal_channel.upper().startswith("ADC"))
    if adc_used > profile.adc_channels:
        errors.append(f"Need {adc_used} ADC channels, target has {profile.adc_channels}")

    pwm_used = sum(1 for a in ir.actuators if a.hal_channel.upper().startswith("PWM"))
    if pwm_used > profile.pwm_channels:
        errors.append(f"Need {pwm_used} PWM, target has {profile.pwm_channels}")

    if ir.deployment.dual_core and not profile.has_dual_core:
        errors.append(f"Target '{profile.name}' has no dual-core")

    return HardwareCheckResult(len(errors) == 0, errors, warnings)
