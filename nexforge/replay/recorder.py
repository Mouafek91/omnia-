"""Records telemetry into a Session."""
from __future__ import annotations
from .session import Session, SessionRecord


class Recorder:
    def __init__(self, name, ir_hash):
        self._name = name
        self._ir_hash = ir_hash
        self._records = []

    def on_telemetry(self, frame):
        t = frame.timestamp_ms * 1000
        for ch, val in frame.sensors.items():
            self._records.append(SessionRecord(t, "sensor", ch, val, self._ir_hash))
        self._records.append(SessionRecord(
            t, "decision", "safety",
            {"decision": "VETO" if frame.veto else "ALLOW",
             "violated": frame.violated_contract,
             "reason": frame.veto_reason},
            self._ir_hash))
        for ch, val in frame.actuators.items():
            self._records.append(SessionRecord(t, "actuator", ch, val, self._ir_hash))
        for f in frame.faults:
            self._records.append(SessionRecord(t, "fault", "system", f, self._ir_hash))

    def to_session(self):
        return Session(name=self._name, ir_hash=self._ir_hash,
                       records=list(self._records))
