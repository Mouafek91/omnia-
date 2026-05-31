"""Priority event bus: CRITICAL / HIGH / NORMAL / LOW."""
from __future__ import annotations
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable


class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(frozen=True)
class Event:
    topic: str
    payload: Any
    priority: Priority
    timestamp_us: int
    source: str = ""


class _Lane:
    __slots__ = ("name", "capacity", "queue", "lock", "dropped")

    def __init__(self, name, capacity):
        self.name = name; self.capacity = capacity
        self.queue = deque(maxlen=capacity)
        self.lock = threading.Lock(); self.dropped = 0

    def push(self, event):
        with self.lock:
            if len(self.queue) >= self.capacity:
                self.dropped += 1; return False
            self.queue.append(event); return True

    def pop(self):
        with self.lock:
            return self.queue.popleft() if self.queue else None


class EventBus:
    DEFAULT_CAPACITIES = {
        Priority.CRITICAL: 256, Priority.HIGH: 512,
        Priority.NORMAL: 1024, Priority.LOW: 2048,
    }

    def __init__(self, capacities=None):
        caps = capacities or self.DEFAULT_CAPACITIES
        self._lanes = {p: _Lane(p.name, caps[p]) for p in Priority}
        self._subs = {}
        self._stop = threading.Event()

    def subscribe(self, topic, handler, lane=Priority.NORMAL):
        self._subs.setdefault(topic, []).append((handler, lane))

    def publish(self, event):
        return self._lanes[event.priority].push(event)

    def publish_now(self, topic, payload, priority=Priority.NORMAL, source=""):
        return self.publish(Event(topic, payload, priority,
                                   int(time.time() * 1_000_000), source))

    def drain(self, max_events=1000):
        processed = 0
        for _ in range(max_events):
            event = self._next_event()
            if event is None: break
            for handler, _ in self._subs.get(event.topic, []):
                try: handler(event)
                except Exception: pass
            processed += 1
        return processed

    def _next_event(self):
        for p in Priority:
            e = self._lanes[p].pop()
            if e is not None: return e
        return None

    def run_forever(self, poll_interval_s=0.001):
        while not self._stop.is_set():
            if self.drain() == 0:
                time.sleep(poll_interval_s)

    def stop(self): self._stop.set()

    def stats(self):
        return {p.name: {"queued": len(self._lanes[p].queue),
                         "dropped": self._lanes[p].dropped}
                for p in Priority}
