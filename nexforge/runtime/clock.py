"""Clock abstraction: realtime / simulated / replay."""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from enum import Enum
import threading


class ClockMode(str, Enum):
    REALTIME = "realtime"
    SIMULATED = "simulated"
    REPLAY = "replay"


class ClockProvider(ABC):
    @abstractmethod
    def now_us(self) -> int: ...
    @abstractmethod
    def mode(self) -> ClockMode: ...
    def sleep_us(self, us: int):
        time.sleep(us / 1_000_000.0)


class RealtimeClock(ClockProvider):
    def __init__(self, epoch_us: int | None = None):
        self._epoch_us = epoch_us if epoch_us is not None else int(time.time() * 1_000_000)
        self._start_mono = time.monotonic_ns()

    def now_us(self) -> int:
        return self._epoch_us + (time.monotonic_ns() - self._start_mono) // 1000

    def mode(self): return ClockMode.REALTIME


class SimulatedClock(ClockProvider):
    def __init__(self, start_us: int = 0):
        self._now = start_us
        self._lock = threading.Lock()

    def now_us(self) -> int:
        with self._lock: return self._now

    def advance(self, delta_us: int) -> int:
        with self._lock:
            self._now += delta_us; return self._now

    def set(self, us: int):
        with self._lock: self._now = us

    def sleep_us(self, us: int): self.advance(us)

    def mode(self): return ClockMode.SIMULATED


class ReplayClock(ClockProvider):
    def __init__(self, timestamps_us):
        self._iter = iter(timestamps_us)
        self._now = 0
        self._advance()

    def _advance(self):
        try: self._now = next(self._iter)
        except StopIteration: pass

    def now_us(self) -> int: return self._now

    def step(self) -> int:
        self._advance(); return self._now

    def mode(self): return ClockMode.REPLAY
