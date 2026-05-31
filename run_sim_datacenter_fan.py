from nexforge.compiler.pipeline import compile_file
from nexforge.backends.python_sim import SimulatorBackend
import sys

print("⚙️ Compiling Data Center Fan domain...")
report = compile_file('domains/datacenter_fan.yaml')
print(f"✅ IR hash: {report.ir.content_hash()}")

sim = SimulatorBackend(report.ir, duration_s=10.0, realtime=False)

# Realistic fault sequence: bearing wear → imbalance → stall
fault_schedule = [
    {"at": 4.0, "channel": "vibration_mm_s", "value": 12.0, "dur": 2.0},  # Imbalance event
    {"at": 7.0, "channel": "rpm", "value": 150.0, "dur": 1.5}           # Partial stall
]

for f in fault_schedule:
    sim.schedule_disturbance(f["at"], {f["channel"]: f["value"]}, duration_s=f["dur"])

_first_ts = None

def my_display(frame):
    global _first_ts
    if _first_ts is None: _first_ts = frame.timestamp_ms
    t = (frame.timestamp_ms - _first_ts) / 1000.0
    state = frame.state
    rpm = frame.sensors.get('rpm', 0.0)
    temp_m = frame.sensors.get('temp_motor_c', 0.0)
    temp_b = frame.sensors.get('temp_bearing_c', 0.0)
    current = frame.sensors.get('current_a', 0.0)
    vib = frame.sensors.get('vibration_mm_s', 0.0)
    veto = "VETO" if frame.veto else "OK"
    reason = frame.veto_reason or ""
    print(f"[t={t:5.2f}s] {veto:5s} | {state:10s} | RPM={rpm:5.0f} | I={current:3.1f}A | Tm={temp_m:5.1f}C | Tb={temp_b:5.1f}C | V={vib:4.1f}mm/s | {reason}")

_original_handler = sim.on_telemetry
def chained_handler(frame):
    _original_handler(frame)
    my_display(frame)

sim.on_telemetry = chained_handler

print("🚀 Running Data Center Fan simulation with fault injection...\n")
sim.run()
print("\n✅ Simulation finished.")