import pytest
from pathlib import Path
from nexforge.compiler.pipeline import compile_file, CompilationError


def test_pump_compiles():
    report = compile_file("domains/pump.yaml")
    assert report.ok
    assert report.ir.timing.schedulable
    assert len(report.ir.safety.contracts) == 3


def test_bad_unit_rejected(tmp_path):
    content = """
metadata: { name: bad, version: "1.0" }
sensors:
  - { name: v, unit: V, min: 0, max: 10, default: 5, hal_channel: ADC_V }
  - { name: t, unit: degC, min: 0, max: 100, default: 25, hal_channel: ADC_T }
actuators: []
physics:
  states:
    - { name: x, unit: "1", initial: 0 }
  equations:
    x: "v + t"
contracts: []
control:
  strategy: PID
  target_sensor: v
  output_actuator: ""
timing: { safety_loop_hz: 10, control_loop_hz: 10, telemetry_hz: 1 }
deployment: { target: mock }
"""
    p = tmp_path / "bad.yaml"
    p.write_text(content)
    with pytest.raises(CompilationError):
        compile_file(p)
