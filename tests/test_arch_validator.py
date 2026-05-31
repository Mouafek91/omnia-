import pytest
from pathlib import Path
from nexforge.compiler.parser import parse_yaml
from nexforge.compiler.passes.arch_validator import validate_architecture


def test_valid_pump_passes():
    ir = parse_yaml("domains/pump.yaml")
    violations = validate_architecture(ir)
    errors = [v for v in violations if v.severity == "ERROR"]
    assert not errors, errors


def test_missing_sensor_reference_caught(tmp_path):
    content = """
metadata: { name: bad, version: "1.0" }
sensors:
  - { name: temp_c, unit: degC, min: 0, max: 100, default: 25, hal_channel: ADC_TEMP }
actuators: []
physics:
  states: []
  equations: {}
contracts:
  - name: phantom
    assume: "pressure_bar > 10"
    guarantee: "pressure_bar < 50"
    reason: "missing sensor"
    reason_ar: "ضغط"
    safety_class: CRITICAL
    safety_level: SIL2
control:
  strategy: PID
  target_sensor: temp_c
  output_actuator: ""
timing: { safety_loop_hz: 10, control_loop_hz: 10, telemetry_hz: 1 }
deployment: { target: mock }
"""
    p = tmp_path / "bad.yaml"
    p.write_text(content, encoding="utf-8")  # ← FIXED
    ir = parse_yaml(p)
    violations = validate_architecture(ir)
    rules = {v.rule for v in violations}
    assert "R03" in rules


def test_duplicate_names_caught(tmp_path):
    content = """
metadata: { name: dup, version: "1.0" }
sensors:
  - { name: x, unit: V, min: 0, max: 10, default: 5, hal_channel: ADC_X }
  - { name: x, unit: V, min: 0, max: 10, default: 5, hal_channel: ADC_Y }
actuators: []
physics: { states: [], equations: {} }
contracts: []
control: { strategy: PID, target_sensor: x, output_actuator: "" }
timing: { safety_loop_hz: 10, control_loop_hz: 10, telemetry_hz: 1 }
deployment: { target: mock }
"""
    p = tmp_path / "dup.yaml"
    p.write_text(content, encoding="utf-8")  # ← FIXED
    ir = parse_yaml(p)
    violations = validate_architecture(ir)
    assert any(v.rule == "R02" for v in violations)
