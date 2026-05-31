from nexforge.compiler.pipeline import compile_file
from nexforge.backends.python_sim import SimulatorBackend
from nexforge.scenarios.base import LIBRARY
import nexforge.scenarios.builtin

print("Compiling pump domain...")
report = compile_file('domains/pump.yaml')
print(f"IR hash: {report.ir.content_hash()}")

# realtime=False = instant execution
sim = SimulatorBackend(report.ir, duration_s=5.0, realtime=False)

sc = LIBRARY.get("overheating")
print(f"Scenario: {sc.name} - {sc.description}")
for d in sc.disturbances(5.0):
    sim.schedule_disturbance(d.at_seconds, {d.channel: d.value}, duration_s=d.duration_s)

def my_display(frame):
    t = getattr(frame, 'sim_t', 0.0)
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
print("\n✅ Simulation finished.")