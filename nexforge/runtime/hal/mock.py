"""Mock HAL for simulation + tests."""
from __future__ import annotations
from .protocol import DriverError


class MockHAL:
    def __init__(self):
        self._sensors = {}
        self._actuators = {}

    def init(self): pass
    def shutdown(self): pass

    def read_sensor(self, channel):
        return self._sensors.get(channel, 0.0)

    def write_actuator(self, channel, value):
        self._actuators[channel] = value

    def inject_sensor(self, channel, value):
        self._sensors[channel] = value

    def read_actuator(self, channel):
        return self._actuators.get(channel, 0.0)


class FaultInjectingHAL:
    def __init__(self, inner):
        self._inner = inner
        self._dead = set()
        self._stuck = {}
        self._offset = {}

    def init(self): self._inner.init()
    def shutdown(self): self._inner.shutdown()

    def read_sensor(self, channel):
        if channel in self._dead:
            raise IOError(f"Dead sensor: {channel}")
        v = self._inner.read_sensor(channel)
        if channel in self._stuck:
            return self._stuck[channel]
        return v + self._offset.get(channel, 0.0)

    def write_actuator(self, channel, value):
        self._inner.write_actuator(channel, value)

    def kill_sensor(self, ch): self._dead.add(ch)
    def stick_sensor(self, ch, v): self._stuck[ch] = v
    def offset_sensor(self, ch, d): self._offset[ch] = d
