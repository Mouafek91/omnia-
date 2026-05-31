"""
Typed contracts. msgspec for hot-path (zero-copy), Pydantic for config.
"""
from __future__ import annotations
import msgspec
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    ALLOW = "ALLOW"
    VETO = "VETO"


class SafetyLevel(str, Enum):
    SIL1 = "SIL1"
    SIL2 = "SIL2"
    SIL3 = "SIL3"
    SIL4 = "SIL4"

    @property
    def required_redundancy(self) -> int:
        return {"SIL1": 1, "SIL2": 2, "SIL3": 2, "SIL4": 3}[self.value]

    @property
    def max_debounce_ms(self) -> int:
        return {"SIL1": 5000, "SIL2": 1000, "SIL3": 200, "SIL4": 50}[self.value]

    @property
    def watchdog_multiplier(self) -> float:
        return {"SIL1": 10.0, "SIL2": 5.0, "SIL3": 3.0, "SIL4": 2.0}[self.value]


class SensorSample(msgspec.Struct, frozen=True, gc=False):
    channel: str
    value: float
    timestamp_us: int
    valid: bool = True


class ActuatorCommand(msgspec.Struct, frozen=True, gc=False):
    channel: str
    value: float
    timestamp_us: int
    source: str = "control"


class TelemetryPacket(msgspec.Struct, frozen=True, gc=False):
    timestamp_us: int
    state: str
    sensors: dict
    actuators: dict
    decision: Decision
    violated_contract: Optional[str]
    veto_reason: Optional[str]
    loop_time_us: int
    faults: list
    ir_hash: str


class Heartbeat(msgspec.Struct, frozen=True, gc=False):
    timestamp_us: int
    state: str
    safety_loop_us: int
    faults_count: int
    veto_active: bool
