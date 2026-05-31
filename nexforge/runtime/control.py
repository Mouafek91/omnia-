"""PID / Hysteresis controllers."""
from __future__ import annotations
from ..compiler.ir import ControlGraph, ControlStrategy


class ControlEngine:
    def __init__(self, graph: ControlGraph):
        self.graph = graph
        if graph.strategy == ControlStrategy.PID:
            self._impl = _PID(
                graph.params.get("kp", 1.0), graph.params.get("ki", 0.0),
                graph.params.get("kd", 0.0),
                graph.params.get("out_min", -100.0), graph.params.get("out_max", 100.0))
        elif graph.strategy == ControlStrategy.HYSTERESIS:
            self._impl = _Hyst(
                graph.params.get("on_threshold", 5.0),
                graph.params.get("off_threshold", 1.0))
        else:
            self._impl = _Passthrough()

    def update(self, setpoint, measured, dt):
        return self._impl.update(setpoint, measured, dt)


class _PID:
    def __init__(self, kp, ki, kd, out_min, out_max):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.out_min, self.out_max = out_min, out_max
        self.integral = 0.0; self.prev_error = 0.0

    def update(self, sp, m, dt):
        e = sp - m
        self.integral = max(-1000, min(1000, self.integral + e * dt))
        d = (e - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = e
        return max(self.out_min, min(self.out_max,
                                     self.kp*e + self.ki*self.integral + self.kd*d))


class _Hyst:
    def __init__(self, on, off):
        self.on, self.off = on, off; self.state = False

    def update(self, sp, m, dt):
        e = m - sp
        if e >= self.on: self.state = True
        elif e <= self.off: self.state = False
        return 1.0 if self.state else 0.0


class _Passthrough:
    def update(self, sp, m, dt): return 0.0
