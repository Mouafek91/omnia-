from nexforge.compiler.pipeline import compile_file
from nexforge.backends.python_sim import SimulatorBackend
from nexforge.scenarios.base import LIBRARY
import nexforge.scenarios.builtin
import sys

print("Compiling pump domain...")
report = compile_file('domains/pump.yaml')
print(f"IR hash: {report.ir.content_hash()}")

sim = SimulatorBackend(report.ir, duration_s=10.0, realtime=True)

sc = LIBRARY.get("sensor_stuck")
print(f"Scenario: {sc.name} - {sc.description}")
for d in sc.disturbances(10.0):
    sim.schedule_disturbance(d.at_seconds, {d.channel: d.value}, duration_s=3.0)

_first_ts = None

def my_display(frame):
    global _first_ts
    if _first_ts is None:
        _first_ts = frame.timestamp_ms
    t = (frame.timestamp_ms - _first_ts) / 1000.0
    state = frame.state
    flow = frame.sensors.get('flow_lpm', 0.0)
    current = frame.sensors.get('current_a', 0.0)
    temp = frame.sensors.get('temp_c', 0.0)
    veto = "VETO" if frame.veto else "OK"
    reason = frame.veto_reason or ""
    print(f"[t={t:5.2f}s] {veto:5s} | {state:10s} | flow={flow:5.1f} | I={current:5.1f}A | T={temp:5.1f}C | {reason}")

_original_handler = sim.on_telemetry
def chained_handler(frame):
    _original_handler(frame)
    my_display(frame)

sim.on_telemetry = chained_handler

print("Running simulation...\n")
sim.run()
print("\nSimulation finished.")