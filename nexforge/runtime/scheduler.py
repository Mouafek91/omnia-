"""Deterministic priority-preemptive scheduler with watchdog."""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger("nexforge.scheduler")


@dataclass
class Task:
    name: str
    callback: Callable
    priority: int
    critical: bool = False


@dataclass
class _TaskState:
    task: Task
    period_s: float
    next_run: float = 0.0
    runs: int = 0
    overruns: int = 0
    last_ms: float = 0.0


class DeterministicScheduler:
    def __init__(self, safety_period_s, control_period_s,
                 telemetry_period_s, watchdog_timeout_s):
        self._tasks = {}
        self._periods = {
            "safety": safety_period_s,
            "control": control_period_s,
            "telemetry": telemetry_period_s,
        }
        self._watchdog = watchdog_timeout_s
        self._last_safety = time.time()

    def register(self, task):
        self._tasks[task.name] = _TaskState(
            task=task, period_s=self._periods.get(task.name, 0.1),
            next_run=time.time())

    def run(self, stop_check=lambda: False):
        while not stop_check():
            now = time.time()
            if "safety" in self._tasks:
                if now - self._last_safety > self._watchdog:
                    raise RuntimeError("Watchdog timeout")
            due = [ts for ts in self._tasks.values() if now >= ts.next_run]
            due.sort(key=lambda ts: ts.task.priority)
            for ts in due:
                t0 = time.perf_counter()
                try: ts.task.callback()
                except Exception as e:
                    log.error("Task '%s' raised: %s", ts.task.name, e)
                    if ts.task.critical: raise
                dur = (time.perf_counter() - t0) * 1000
                ts.last_ms = dur; ts.runs += 1
                if dur > ts.period_s * 1000: ts.overruns += 1
                ts.next_run = now + ts.period_s
                if ts.task.name == "safety":
                    self._last_safety = time.time()
            next_dl = min(ts.next_run for ts in self._tasks.values())
            sleep_for = max(0.0, next_dl - time.time())
            if sleep_for > 0: time.sleep(min(sleep_for, 0.001))

    def stats(self):
        return {name: {"runs": ts.runs, "overruns": ts.overruns, "last_ms": ts.last_ms}
                for name, ts in self._tasks.items()}
