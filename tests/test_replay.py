import pytest
from pathlib import Path
from nexforge.replay.session import Session, SessionRecord
from nexforge.compiler.parser import parse_yaml
from nexforge.replay.player import ReplayEngine


def test_session_roundtrip(tmp_path):
    session = Session(
        name="test", ir_hash="abc123",
        records=[
            SessionRecord(timestamp_us=0, kind="sensor",
                          channel="flow", value=1.5, ir_hash="abc123"),
            SessionRecord(timestamp_us=1000, kind="decision",
                          channel="safety", value={"decision": "ALLOW"},
                          ir_hash="abc123"),
        ])
    path = tmp_path / "s.json"
    session.save(path)
    loaded = Session.load(path)
    assert loaded.name == "test"
    assert len(loaded.records) == 2


def test_replay_detects_hash_mismatch():
    ir = parse_yaml("domains/pump.yaml")
    session = Session(name="x", ir_hash="wrong", records=[])
    with pytest.raises(ValueError):
        ReplayEngine(ir, session)
