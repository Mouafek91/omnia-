"""HAL protocols: SensorDriver / ActuatorDriver / CommDriver."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from enum import Enum


class DriverError(Enum):
    OK = "OK"
    TIMEOUT = "TIMEOUT"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    HARDWARE_FAULT = "HARDWARE_FAULT"
    NOT_INITIALIZED = "NOT_INITIALIZED"


@runtime_checkable
class SensorDriver(Protocol):
    name: str
    def init(self) -> DriverError: ...
    def read(self) -> tuple: ...
    def shutdown(self) -> None: ...


@runtime_checkable
class ActuatorDriver(Protocol):
    name: str
    def init(self) -> DriverError: ...
    def write(self, value: float) -> DriverError: ...
    def readback(self) -> tuple: ...
    def shutdown(self) -> None: ...


@runtime_checkable
class CommDriver(Protocol):
    name: str
    def init(self) -> DriverError: ...
    def send(self, data: bytes) -> DriverError: ...
    def recv(self, max_bytes, timeout_ms) -> tuple: ...
    def shutdown(self) -> None: ...
