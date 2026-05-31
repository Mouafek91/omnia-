"""Watchdog Supervisor — external process monitor."""
from __future__ import annotations
import threading
import time
import logging
from dataclasses import dataclass

log = logging.getLogger("nexforge.watchdog")


@dataclass
class WatchdogConfig:
    heartbeat_timeout_ms: int = 500
    max_loop_latency_us: int = 50_000
    max_faults_per_second: int = 100
    veto_stuck_window_ms: int = 5_000


class WatchdogSupervisor:
    def __init__(self, config, emergency_shutdown):
        self.config = config
        self._emergency_shutdown = emergency_shutdown
        self._last_heartbeat = None
        self._last_hb_time = 0
        self._veto_start = 0
        self._fault_window = []
        self._stop = threading.Event()
        self._thread = None

    def on_heartbeat(self, hb):
        self._last_heartbeat = hb
        self._last_hb_time = int(time.time() * 1_000_000)
        if hb.veto_active:
            if self._veto_start == 0: self._veto_start = self._last_hb_time
        else:
            self._veto_start = 0
        self._fault_window.append(self._last_hb_time)
        cutoff = self._last_hb_time - 1_000_000
        self._fault_window = [t for t in self._fault_window if t > cutoff]

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="watchdog")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2.0)

    def _loop(self):
        while not self._stop.is_set():
            self._check(int(time.time() * 1_000_000))
            time.sleep(self.config.heartbeat_timeout_ms / 10_000.0)

    def _check(self, now_us):
        if self._last_hb_time > 0:
            since = now_us - self._last_hb_time
            if since > self.config.heartbeat_timeout_ms * 1000:
                log.critical("WATCHDOG: heartbeat timeout"); self._trigger("heartbeat_timeout"); return
        if self._last_heartbeat:
            if self._last_heartbeat.safety_loop_us > self.config.max_loop_latency_us:
                log.warning("WATCHDOG: loop overrun")
        if len(self._fault_window) > self.config.max_faults_per_second:
            log.critical("WATCHDOG: fault storm"); self._trigger("fault_storm"); return
        if self._veto_start > 0:
            stuck_ms = (now_us - self._veto_start) // 1000
            if stuck_ms > self.config.veto_stuck_window_ms:
                log.critical("WATCHDOG: veto stuck"); self._trigger("veto_stuck")

    def _trigger(self, reason):
        log.critical("WATCHDOG TRIGGERED: %s", reason)
        try: self._emergency_shutdown()
        except Exception as e: log.error("Emergency shutdown failed: %s", e)
