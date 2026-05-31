"""Runtime kernel — fixed library, shared by all domains."""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass
from ..compiler.ir import CPSIR
from .hal.mock import MockHAL
from .scheduler import DeterministicScheduler, Task
from .physics import PhysicsEngine
from .control import ControlEngine
from .safety import SafetyEngine
from .statechart_engine import StatechartEngine
from .ringbuffer import SensorFrame

log = logging.getLogger("nexforge.kernel")

@dataclass
class TelemetryFrame:
    timestamp_ms: int
    state: str
    sensors: dict
    actuators: dict
    veto: bool
    veto_reason: str | None
    veto_critical: bool
    loop_time_ms: float
    faults: list

class NexForgeKernel:
    def __init__(self, ir: CPSIR, hal=None):
        self.ir = ir
        self.hal = hal or MockHAL()
        self._stop = False
        self._physics = PhysicsEngine(ir.physics)
        self._safety = SafetyEngine(ir)
        self._control = ControlEngine(ir.control)
        self._statechart = StatechartEngine(ir.statechart)
        self._sensor_names = ir.sensor_names()
        self._sensor_frame = SensorFrame(self._sensor_names)
        self._actuator_values = {a.name: a.fail_safe_value for a in ir.actuators}
        self._readings_dict = {n: 0.0 for n in self._sensor_names}
        t = ir.timing
        self._scheduler = DeterministicScheduler(
            1.0 / t.safety_loop_hz, 1.0 / t.control_loop_hz,
            1.0 / t.telemetry_hz, t.watchdog_timeout_ms / 1000.0)
        self._telemetry_cb = None
        self._last_report = None
        self._faults = []

    def on_telemetry(self, cb): self._telemetry_cb = cb
    def start(self): self.hal.init()
    def stop(self): self._stop = True

    def run(self):
        self.start()
        self._scheduler.register(Task("safety", self._safety_tick, 0, True))
        self._scheduler.register(Task("control", self._control_tick, 1, False))
        self._scheduler.register(Task("telemetry", self._telemetry_tick, 2, False))
        try: self._scheduler.run(stop_check=lambda: self._stop)
        finally: self._shutdown()

    def _safety_tick(self):
        t0 = time.perf_counter()
        faults = []
        now_ms = int(time.time() * 1000)
        for i, sensor in enumerate(self.ir.sensors):
            try:
                v = self.hal.read_sensor(sensor.hal_channel)
                if not sensor.quantity.contains(v):
                    faults.append(f"oor:{sensor.name}")
                    v = sensor.quantity.default
                self._sensor_frame.set(i, v)
                self._readings_dict[sensor.name] = v
            except Exception:
                faults.append(f"read_err:{sensor.name}")
                self._sensor_frame.set(i, sensor.quantity.default)
                self._readings_dict[sensor.name] = sensor.quantity.default
        self._sensor_frame.timestamp_ms = now_ms
        report = self._safety.evaluate(self._readings_dict, now_ms)
        self._last_report = report
        if report.veto:
            for act in self.ir.actuators:
                self.hal.write_actuator(act.hal_channel, act.fail_safe_value)
                self._actuator_values[act.name] = act.fail_safe_value
        ctx = dict(self._readings_dict)
        # Match the new statechart guard names
        ctx["critical_veto_active"] = 1.0 if report.veto_critical else 0.0
        ctx["important_veto_active"] = 1.0 if (report.veto and not report.veto_critical) else 0.0
        self._statechart.tick(ctx)
        self._faults = faults
        self._last_loop_ms = (time.perf_counter() - t0) * 1000

    def _control_tick(self):
        if self._last_report and self._last_report.veto: return
        ctrl = self.ir.control
        measured = self._readings_dict.get(ctrl.target_sensor, 0.0)
        out = self._control.update(ctrl.setpoint, measured, 1.0 / self.ir.timing.control_loop_hz)
        if ctrl.output_actuator:
            act = next((a for a in self.ir.actuators if a.name == ctrl.output_actuator), None)
            if act:
                clamped = max(act.quantity.min, min(act.quantity.max, out))
                self.hal.write_actuator(act.hal_channel, clamped)
                self._actuator_values[act.name] = clamped

    def _telemetry_tick(self):
        if self._telemetry_cb is None: return
        frame = TelemetryFrame(
            timestamp_ms=int(time.time() * 1000),
            state=self._statechart.current.value,
            sensors=self._sensor_frame.as_dict(),
            actuators=dict(self._actuator_values),
            veto=self._last_report.veto if self._last_report else False,
            veto_reason=self._last_report.veto_reason if self._last_report else None,
            veto_critical=self._last_report.veto_critical if self._last_report else False,
            loop_time_ms=getattr(self, "_last_loop_ms", 0.0),
            faults=list(self._faults))
        try: self._telemetry_cb(frame)
        except Exception as e: log.error("Telemetry callback failed: %s", e)

    def _shutdown(self):
        for act in self.ir.actuators:
            try: self.hal.write_actuator(act.hal_channel, act.fail_safe_value)
            except Exception: pass
        self.hal.shutdown()