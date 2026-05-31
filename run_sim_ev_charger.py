from nexforge.compiler.pipeline import compile_file
from nexforge.backends.python_sim import SimulatorBackend
import sys

print("⚙️ Compiling EV Charger domain...")
report = compile_file('domains/ev_charger.yaml')
print(f"✅ IR hash: {report.ir.content_hash()}")

sim = SimulatorBackend(report.ir, duration_s=8.0, realtime=False)

# Inject a sequence of real-world EV charging faults
fault_schedule = [
    {"at": 3.0, "channel": "plug_connected", "value": 0.0, "dur": 2.0},  # Unsafe disconnect
    {"at": 5.5, "channel": "ground_leakage_a", "value": 0.06, "dur": 1.5} # Ground fault
]

for f in fault_schedule:
    sim.schedule_disturbance(f["at"], {f["channel"]: f["value"]}, duration_s=f["dur"])

_first_ts = None

def my_display(frame):
    global _first_ts
    if _first_ts is None: _first_ts = frame.timestamp_ms
    t = (frame.timestamp_ms - _first_ts) / 1000.0
    state = frame.state
    current = frame.sensors.get('current_a', 0.0)
    temp = frame.sensors.get('temp_connector_c', 0.0)
    leakage = frame.sensors.get('ground_leakage_a', 0.0)
    plug = frame.sensors.get('plug_connected', 1.0)
    veto = "VETO" if frame.veto else "OK"
    reason = frame.veto_reason or ""
    print(f"[t={t:5.2f}s] {veto:5s} | {state:10s} | I={current:4.1f}A | T={temp:5.1f}C | L={leakage:.3f}A | P={'ON' if plug else 'OFF'} | {reason}")

_original_handler = sim.on_telemetry
def chained_handler(frame):
    _original_handler(frame)
    my_display(frame)

sim.on_telemetry = chained_handler

print("🚀 Running EV Charger simulation with fault injection...\n")
sim.run()
print("\n✅ Simulation finished.")