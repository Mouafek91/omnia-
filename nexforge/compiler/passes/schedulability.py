"""Rate-Monotonic schedulability analysis."""
from __future__ import annotations
import math
from dataclasses import replace
from ..ir import CPSIR


def estimate_wcets(ir: CPSIR) -> dict:
    n_sensors = len(ir.sensors)
    n_contracts = len(ir.safety.contracts)
    n_derivs = len(ir.physics.derivatives)
    n_actuators = len(ir.actuators)
    SENSOR = 8; ACTUATOR = 5; CONTRACT = 15; DERIV = 25; OVERHEAD = 50
    safety = OVERHEAD + n_sensors * SENSOR + n_contracts * CONTRACT + n_actuators * ACTUATOR
    control = OVERHEAD + n_derivs * DERIV + 2 * ACTUATOR
    telemetry = OVERHEAD + n_sensors * 3 + n_actuators * 3 + 50
    return {"safety": safety, "control": control, "telemetry": telemetry}


def check_schedulability(ir: CPSIR) -> CPSIR:
    wcets = estimate_wcets(ir)
    t = ir.timing
    tasks = [
        ("safety", wcets["safety"], 1_000_000 // t.safety_loop_hz),
        ("control", wcets["control"], 1_000_000 // t.control_loop_hz),
        ("telemetry", wcets["telemetry"], 1_000_000 // t.telemetry_hz),
    ]
    tasks.sort(key=lambda x: x[2])
    n = len(tasks)
    U = sum(C / T for _, C, T in tasks)

    schedulable = True
    for i, (name, Ci, Ti) in enumerate(tasks):
        Ri = Ci
        for _ in range(20):
            interference = sum(
                math.ceil(Ri / tasks[j][2]) * tasks[j][1] for j in range(i))
            Ri_new = Ci + interference
            if Ri_new == Ri: break
            Ri = Ri_new
        if Ri > Ti:
            schedulable = False

    new_timing = replace(
        t,
        wcet_safety_us=wcets["safety"],
        wcet_control_us=wcets["control"],
        wcet_telemetry_us=wcets["telemetry"],
        utilization=round(U, 4),
        schedulable=schedulable,
    )
    return replace(ir, timing=new_timing)
