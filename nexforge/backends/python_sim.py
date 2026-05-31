"""
Python simulator backend.
Uses the runtime kernel + MockHAL. No codegen — pure configuration.
"""
from __future__ import annotations
import time
import threading
from pathlib import Path
from ..compiler.ir import CPSIR
from ..runtime.kernel import NexForgeKernel, TelemetryFrame
from ..runtime.hal.mock import MockHAL
from ..runtime.physics import PhysicsEngine


class SimulatorBackend:
    def __init__(self, ir: CPSIR, duration_s: float = 30.0, realtime: bool = True):
        self.ir = ir
        self.duration_s = duration_s
        self.realtime = realtime
        self.hal = MockHAL()
        self.kernel = NexForgeKernel(ir, self.hal)

        name_units = {}
        for s in ir.sensors: name_units[s.name] = s.quantity.unit
        for a in ir.actuators: name_units[a.name] = a.quantity.unit
        for sv in ir.physics.states: name_units[sv.name] = sv.unit
        self._physics = PhysicsEngine(ir.physics)

        self._history: list[dict] = []
        self._disturbances: list[tuple[float, dict, float]] = []
        self._sim_t = 0.0
        self._active_disturbances = {}

    def schedule_disturbance(self, at_seconds: float, inputs: dict, duration_s: float = 1.0):
        self._disturbances.append((at_seconds, inputs, duration_s))

    def on_telemetry(self, frame: TelemetryFrame):
        frame.sim_t = self._sim_t  # Attach accurate simulation time
        self._history.append({
            "sim_t": self._sim_t,
            "state": frame.state, "sensors": frame.sensors,
            "actuators": frame.actuators, "veto": frame.veto,
            "veto_reason": frame.veto_reason, "critical": frame.veto_critical,
            "loop_ms": frame.loop_time_ms, "faults": frame.faults,
        })

    def run(self) -> list[dict]:
        self.kernel.on_telemetry(self.on_telemetry)
        dt = 1.0 / self.ir.timing.safety_loop_hz
        self._sim_t = 0.0
        self._active_disturbances = {}

        if self.realtime:
            self._run_realtime(dt)
        else:
            self._run_sync(dt)  # ✅ Deterministic fast-forward

        return self._history

    def _run_sync(self, dt: float):
        """Synchronous step loop for fast-forward simulation."""
        self.kernel.start()
        total_steps = int(self.duration_s / dt) + 1

        for _ in range(total_steps):
            # 1. Update active disturbances
            self._active_disturbances.clear()
            for at, inputs, dur in self._disturbances:
                if at <= self._sim_t < at + dur:
                    self._active_disturbances.update(inputs)

            # 2. Physics step
            inputs = {a.name: self.hal.read_actuator(a.hal_channel) for a in self.ir.actuators}
            state = self._physics.step(inputs, dt, self._active_disturbances)
            for s in self.ir.sensors:
                if s.name in state:
                    self.hal.inject_sensor(s.hal_channel, state[s.name])

            # 3. Kernel ticks (bypass scheduler for deterministic sync)
            self.kernel._safety_tick()
            self.kernel._control_tick()
            self.kernel._telemetry_tick()

            # 4. Advance simulation time
            self._sim_t += dt

        self.kernel._shutdown()

    def _run_realtime(self, dt: float):
        """Threaded approach for real-time wall-clock simulation."""
        stop_evt = threading.Event()
        self.kernel.start()

        def physics_loop():
            while not stop_evt.is_set():
                if self._sim_t >= self.duration_s:
                    stop_evt.set()
                    break
                self._active_disturbances.clear()
                for at, inputs, dur in self._disturbances:
                    if at <= self._sim_t < at + dur:
                        self._active_disturbances.update(inputs)

                inputs = {a.name: self.hal.read_actuator(a.hal_channel) for a in self.ir.actuators}
                state = self._physics.step(inputs, dt, self._active_disturbances)
                for s in self.ir.sensors:
                    if s.name in state:
                        self.hal.inject_sensor(s.hal_channel, state[s.name])

                self.kernel._safety_tick()
                self.kernel._control_tick()
                self.kernel._telemetry_tick()
                self._sim_t += dt
                time.sleep(dt)

        t = threading.Thread(target=physics_loop, daemon=True)
        t.start()

        def timeout():
            time.sleep(self.duration_s * 1.2)
            self.kernel.stop()
        threading.Thread(target=timeout, daemon=True).start()

        try:
            self.kernel.run()
        finally:
            stop_evt.set()

    def save(self, path: Path):
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)