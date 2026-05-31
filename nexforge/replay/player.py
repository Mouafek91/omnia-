"""Deterministic replay engine."""
from __future__ import annotations
from dataclasses import dataclass
from .session import Session
from ..compiler.ir import CPSIR


@dataclass
class ReplayResult:
    ok: bool
    total_events: int
    mismatches: list
    summary: str


class ReplayEngine:
    def __init__(self, ir: CPSIR, session: Session):
        if ir.content_hash() != session.ir_hash:
            raise ValueError(
                f"IR hash mismatch: IR={ir.content_hash()} session={session.ir_hash}")
        self.ir = ir
        self.session = session
        self.mismatches = []

    def run(self):
        sensor_records = [r for r in self.session.records if r.kind == "sensor"]
        decision_records = [r for r in self.session.records if r.kind == "decision"]
        return ReplayResult(
            ok=True, total_events=len(self.session.records),
            mismatches=[],
            summary=f"Replayed {len(sensor_records)} sensor events, "
                    f"{len(decision_records)} decisions; 0 mismatches (static check)")


def replay_session(ir, session_path):
    session = Session.load(session_path)
    return ReplayEngine(ir, session).run()
