"""
NexForge Intermediate Representation — typed, immutable, content-addressed.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from .units import Unit, lookup_unit, DIMENSIONLESS


class SafetyClass(str, Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    TELEMETRY = "TELEMETRY"

class DataType(str, Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"

class ControlStrategy(str, Enum):
    PID = "PID"
    HYSTERESIS = "HYSTERESIS"
    STATE_MACHINE = "STATE_MACHINE"

class DeploymentTarget(str, Enum):
    MOCK = "mock"
    ESP32 = "esp32"
    STM32 = "stm32"
    LINUX_RT = "linux_rt"
    RP2040 = "rp2040"

class CPSSystemState(str, Enum):
    INIT = "INIT"
    SAFE = "SAFE"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    EMERGENCY = "EMERGENCY"
    SHUTDOWN = "SHUTDOWN"

class TemporalOp(str, Enum):
    INSTANT = "instant"
    FOR = "for"
    WITHIN = "within"
    AFTER = "after"
    STABLE = "stable"

@dataclass(frozen=True)
class QuantityType:
    dtype: DataType
    unit: Unit
    min: float
    max: float
    default: float
    safety_class: SafetyClass = SafetyClass.TELEMETRY
    safety_level: str = "SIL1"
    rate_hz: int = 100

    def __post_init__(self):
        if self.min > self.max: raise ValueError(f"min ({self.min}) > max ({self.max})")
        if not (self.min <= self.default <= self.max): raise ValueError(f"default {self.default} outside [{self.min}, {self.max}]")

    def contains(self, v: float) -> bool: return self.min <= v <= self.max

@dataclass(frozen=True)
class SensorNode:
    name: str
    quantity: QuantityType
    hal_channel: str
    stuck_detection_ms: int = 1000
    noise_filter: str = "moving_average"
    fault_region: str = "default"

@dataclass(frozen=True)
class ActuatorNode:
    name: str
    quantity: QuantityType
    hal_channel: str
    fail_safe_value: float
    fault_region: str = "default"

@dataclass(frozen=True)
class StateVariable:
    name: str
    unit: Unit
    initial: float = 0.0

@dataclass(frozen=True)
class Derivative:
    state: str
    expression: str
    depends_on: tuple = ()

@dataclass(frozen=True)
class Disturbance:
    name: str
    affects: str
    magnitude: float

@dataclass(frozen=True)
class PhysicsGraph:
    states: tuple
    derivatives: tuple
    disturbances: tuple = ()
    topo_order: tuple = ()

@dataclass(frozen=True)
class TemporalBound:
    op: TemporalOp
    duration_ms: int = 0
    def is_instant(self) -> bool: return self.op == TemporalOp.INSTANT

@dataclass(frozen=True)
class Contract:
    name: str
    assume: str
    guarantee: str
    reason: str
    reason_ar: str = ""
    safety_class: SafetyClass = SafetyClass.CRITICAL
    safety_level: str = "SIL1"
    assume_temporal: TemporalBound = field(default_factory=lambda: TemporalBound(TemporalOp.INSTANT))
    guarantee_temporal: TemporalBound = field(default_factory=lambda: TemporalBound(TemporalOp.INSTANT))
    debounce_ms: int = 0
    fault_region: str = "default"
    depends_on: tuple = ()

@dataclass(frozen=True)
class SafetyGraph:
    contracts: tuple

@dataclass(frozen=True)
class ControlGraph:
    strategy: ControlStrategy
    target_sensor: str
    output_actuator: str
    params: dict = field(default_factory=dict)
    setpoint: float = 0.0

@dataclass(frozen=True)
class Transition:
    from_state: CPSSystemState
    to_state: CPSSystemState
    guard: str
    priority: int = 0

@dataclass(frozen=True)
class Statechart:
    states: tuple
    initial: CPSSystemState
    transitions: tuple
    entry_actions: dict = field(default_factory=dict)
    exit_actions: dict = field(default_factory=dict)

@dataclass(frozen=True)
class FaultRegion:
    name: str
    sensors: tuple
    actuators: tuple
    contracts: tuple
    isolation_level: int = 1
    degraded_state: CPSSystemState = CPSSystemState.DEGRADED
    recovery_allowed: bool = False

@dataclass(frozen=True)
class FaultModel:
    regions: tuple
    detect_sensor_stuck: bool = True
    detect_sensor_oor: bool = True
    detect_actuator_failure: bool = True
    detect_comm_loss: bool = True
    detect_timing_overrun: bool = True

@dataclass(frozen=True)
class TimingModel:
    safety_loop_hz: int = 100
    control_loop_hz: int = 50
    telemetry_hz: int = 10
    watchdog_timeout_ms: int = 500
    max_jitter_ms: int = 5
    wcet_safety_us: int = 0
    wcet_control_us: int = 0
    wcet_telemetry_us: int = 0
    utilization: float = 0.0
    schedulable: bool = False

@dataclass(frozen=True)
class DeploymentModel:
    target: DeploymentTarget
    dual_core: bool = True
    safety_core: int = 0
    comm_core: int = 1

@dataclass(frozen=True)
class HardwareProfile:
    name: str
    ram_bytes: int
    flash_bytes: int
    cpu_mhz: int
    adc_channels: int
    adc_bits: int
    pwm_channels: int
    gpio_pins: int
    i2c_buses: int
    spi_buses: int
    uart_ports: int
    isr_latency_us: int
    has_fpu: bool
    has_dual_core: bool
    rtos_tick_hz: int
    max_tasks: int

HARDWARE_PROFILES = {
    DeploymentTarget.ESP32: HardwareProfile("ESP32-WROOM-32", 520*1024, 4*1024*1024, 240, 16, 12, 16, 34, 2, 3, 3, 5, True, True, 1000, 32),
    DeploymentTarget.STM32: HardwareProfile("STM32F4", 192*1024, 1*1024*1024, 168, 16, 12, 14, 80, 3, 3, 6, 2, True, False, 1000, 24),
    DeploymentTarget.RP2040: HardwareProfile("RP2040", 264*1024, 2*1024*1024, 133, 4, 12, 8, 30, 2, 2, 2, 3, False, True, 1000, 16),
    DeploymentTarget.MOCK: HardwareProfile("Mock", 2**30, 2**30, 3000, 256, 24, 256, 256, 16, 16, 16, 0, True, True, 10000, 256),
    DeploymentTarget.LINUX_RT: HardwareProfile("Linux RT", 512*1024*1024, 8*1024*1024*1024, 2000, 256, 24, 256, 256, 16, 16, 16, 1, True, True, 1000, 256),
}

@dataclass(frozen=True)
class Metadata:
    domain_name: str
    version: str
    description: str
    source_prompt: str = ""
    generator: str = "nexforge-v6"

@dataclass(frozen=True)
class CPSIR:
    metadata: Metadata
    sensors: tuple
    actuators: tuple
    physics: PhysicsGraph
    safety: SafetyGraph
    control: ControlGraph
    statechart: Statechart
    faults: FaultModel
    timing: TimingModel
    deployment: DeploymentModel

    def sensor_names(self) -> tuple: return tuple(s.name for s in self.sensors)
    def actuator_names(self) -> tuple: return tuple(a.name for a in self.actuators)
    def state_names(self) -> tuple: return tuple(s.name for s in self.physics.states)

    def sensor_by_name(self, name: str):
        for s in self.sensors:
            if s.name == name: return s
        raise KeyError(f"Sensor '{name}' not in IR")

    def to_json(self) -> str:
        d = asdict(self); _convert_units(d)
        return json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True)

    def content_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()[:16]


def _convert_units(d):
    if isinstance(d, dict):
        for k, v in list(d.items()):
            if isinstance(v, Unit): d[k] = v.name
            else: _convert_units(v)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if isinstance(v, Unit): d[i] = v.name
            else: _convert_units(v)


def _default_statechart() -> Statechart:
    return Statechart(
        states=tuple(CPSSystemState),
        initial=CPSSystemState.INIT,
        transitions=(
            Transition(CPSSystemState.INIT, CPSSystemState.SAFE, "True", 10),
            Transition(CPSSystemState.SAFE, CPSSystemState.RUNNING, "True", 5),
            Transition(CPSSystemState.RUNNING, CPSSystemState.EMERGENCY, "critical_veto_active", 100),
            Transition(CPSSystemState.RUNNING, CPSSystemState.DEGRADED, "important_veto_active", 90),
            Transition(CPSSystemState.EMERGENCY, CPSSystemState.SHUTDOWN, "True", 100),
            Transition(CPSSystemState.DEGRADED, CPSSystemState.SHUTDOWN, "True", 50),
        ),
    )