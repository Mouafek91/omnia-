"""Fixed-size ring buffer. Zero allocation after construction."""
from __future__ import annotations
from array import array


class RingBuffer:
    __slots__ = ("_buf", "_capacity", "_head", "_count")

    def __init__(self, capacity):
        self._buf = array("d", [0.0] * capacity)
        self._capacity = capacity; self._head = 0; self._count = 0

    @property
    def capacity(self): return self._capacity
    @property
    def count(self): return self._count

    def push(self, value):
        self._buf[self._head] = value
        self._head = (self._head + 1) % self._capacity
        if self._count < self._capacity: self._count += 1

    def get(self, index):
        if index < 0 or index >= self._count:
            raise IndexError(f"RingBuffer index {index} out of range")
        start = (self._head - self._count) % self._capacity
        return self._buf[(start + index) % self._capacity]

    def latest(self):
        if self._count == 0: raise IndexError("Empty buffer")
        return self._buf[(self._head - 1) % self._capacity]

    def moving_average(self):
        if self._count == 0: return 0.0
        return sum(self.get(i) for i in range(self._count)) / self._count

    def clear(self): self._head = 0; self._count = 0


class SensorFrame:
    __slots__ = ("_buf", "_names", "_timestamp_ms")

    def __init__(self, names):
        self._buf = array("d", [0.0] * len(names))
        self._names = names; self._timestamp_ms = 0

    def set(self, index, value): self._buf[index] = value
    def get(self, index): return self._buf[index]
    def set_by_name(self, name, value): self._buf[self._names.index(name)] = value
    def get_by_name(self, name): return self._buf[self._names.index(name)]

    @property
    def timestamp_ms(self): return self._timestamp_ms
    @timestamp_ms.setter
    def timestamp_ms(self, v): self._timestamp_ms = v

    def as_dict(self):
        return {n: self._buf[i] for i, n in enumerate(self._names)}
