"""YAML → CPSIR parser. Pure, deterministic, fail-fast."""
from __future__ import annotations
from pathlib import Path
import yaml

from .ir import (
    CPSIR, Metadata, SensorNode, ActuatorNode, QuantityType, DataType,
    SafetyClass, StateVariable, Derivative, Disturbance, PhysicsGraph,
    Contract, TemporalBound, TemporalOp, SafetyGraph, ControlGraph,
    ControlStrategy, Statechart, Transition, CPSSystemState, FaultRegion,
    FaultModel, TimingModel, DeploymentModel, DeploymentTarget,
    _default_statechart,
)
from .units import lookup_unit


def parse_yaml(path, source_prompt: str = "") -> CPSIR:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    meta = raw.get("metadata", {})
    metadata = Metadata(
        domain_name=meta.get("name", raw.get("name", "unknown")),
        version=str(meta.get("version", "1.0.0")),
        description=meta.get("description", ""),
        source_prompt=source_prompt,
    )

    sensors = tuple(
        SensorNode(
            name=s["name"],
            quantity=QuantityType(
                dtype=DataType(s.get("dtype", "float")),
                unit=lookup_unit(s["unit"]),
                min=float(s["min"]),
                max=float(s["max"]),
                default=float(s.get("default", 0.0)),
                safety_class=SafetyClass(s.get("safety_class", "TELEMETRY")),
                safety_level=s.get("safety_level", "SIL1"),
                rate_hz=int(s.get("rate_hz", 100)),
            ),
            hal_channel=s.get("hal_channel", f"ADC_{s['name'].upper()}"),
            stuck_detection_ms=int(s.get("stuck_detection_ms", 1000)),
            noise_filter=s.get("noise_filter", "moving_average"),
            fault_region=s.get("fault_region", "default"),
        ) for s in raw.get("sensors", []))

    actuators = tuple(
        ActuatorNode(
            name=a["name"],
            quantity=QuantityType(
                dtype=DataType(a.get("dtype", "float")),
                unit=lookup_unit(a.get("unit", "1")),
                min=float(a.get("min", 0.0)),
                max=float(a.get("max", 100.0)),
                default=float(a.get("default", 0.0)),
                safety_class=SafetyClass(a.get("safety_class", "IMPORTANT")),
                safety_level=a.get("safety_level", "SIL1"),
            ),
            hal_channel=a.get("hal_channel", f"GPIO_{a['name'].upper()}"),
            fail_safe_value=float(a.get("fail_safe_value", 0.0)),
            fault_region=a.get("fault_region", "default"),
        ) for a in raw.get("actuators", []))

    phys = raw.get("physics", {})
    states = tuple(
        StateVariable(name=sv["name"], unit=lookup_unit(sv["unit"]),
                      initial=float(sv.get("initial", 0.0)))
        for sv in phys.get("states", []))
    derivs = tuple(Derivative(state=k, expression=v)
                   for k, v in phys.get("equations", {}).items())
    disturbs = tuple(
        Disturbance(name=d["name"], affects=d["affects"],
                    magnitude=float(d.get("magnitude", 0.0)))
        for d in phys.get("disturbances", []))
    physics = PhysicsGraph(states=states, derivatives=derivs, disturbances=disturbs)

    contracts = tuple(
        Contract(
            name=c["name"],
            assume=c.get("assume", "True"),
            guarantee=c["guarantee"],
            reason=c["reason"],
            reason_ar=c.get("reason_ar", ""),
            safety_class=SafetyClass(c.get("safety_class", "CRITICAL")),
            safety_level=c.get("safety_level", "SIL1"),
            assume_temporal=_parse_temporal(c.get("assume_temporal")),
            guarantee_temporal=_parse_temporal(c.get("guarantee_temporal")),
            debounce_ms=int(c.get("debounce_ms", 0)),
            fault_region=c.get("fault_region", "default"),
        ) for c in raw.get("contracts", []))
    safety = SafetyGraph(contracts=contracts)

    ctrl = raw.get("control", {})
    control = ControlGraph(
        strategy=ControlStrategy(ctrl.get("strategy", "PID")),
        target_sensor=ctrl.get("target_sensor", ""),
        output_actuator=ctrl.get("output_actuator", ""),
        params=ctrl.get("params", {}),
        setpoint=float(ctrl.get("setpoint", 0.0)),
    )

    sc = raw.get("statechart")
    if sc:
        statechart = Statechart(
            states=tuple(CPSSystemState(s) for s in sc.get("states", [])),
            initial=CPSSystemState(sc.get("initial", "INIT")),
            transitions=tuple(
                Transition(from_state=CPSSystemState(t["from"]),
                           to_state=CPSSystemState(t["to"]),
                           guard=t.get("guard", "True"),
                           priority=int(t.get("priority", 0)))
                for t in sc.get("transitions", [])),
        )
    else:
        statechart = _default_statechart()

    faults_raw = raw.get("faults", {})
    if faults_raw.get("regions"):
        regions = tuple(
            FaultRegion(
                name=r["name"],
                sensors=tuple(r.get("sensors", [])),
                actuators=tuple(r.get("actuators", [])),
                contracts=tuple(r.get("contracts", [])),
                isolation_level=int(r.get("isolation_level", 1)),
                degraded_state=CPSSystemState(r.get("degraded_state", "DEGRADED")),
                recovery_allowed=bool(r.get("recovery_allowed", False)),
            ) for r in faults_raw["regions"])
    else:
        regions = (FaultRegion(
            name="default",
            sensors=tuple(s.name for s in sensors),
            actuators=tuple(a.name for a in actuators),
            contracts=tuple(c.name for c in contracts),
        ),)
    faults = FaultModel(
        regions=regions,
        detect_sensor_stuck=faults_raw.get("detect_sensor_stuck", True),
        detect_sensor_oor=faults_raw.get("detect_sensor_oor", True),
        detect_actuator_failure=faults_raw.get("detect_actuator_failure", True),
        detect_comm_loss=faults_raw.get("detect_comm_loss", True),
        detect_timing_overrun=faults_raw.get("detect_timing_overrun", True),
    )

    t = raw.get("timing", {})
    timing = TimingModel(
        safety_loop_hz=int(t.get("safety_loop_hz", 100)),
        control_loop_hz=int(t.get("control_loop_hz", 50)),
        telemetry_hz=int(t.get("telemetry_hz", 10)),
        watchdog_timeout_ms=int(t.get("watchdog_timeout_ms", 500)),
        max_jitter_ms=int(t.get("max_jitter_ms", 5)),
    )

    d = raw.get("deployment", {})
    deployment = DeploymentModel(
        target=DeploymentTarget(d.get("target", "mock")),
        dual_core=bool(d.get("dual_core", True)),
        safety_core=int(d.get("safety_core", 0)),
        comm_core=int(d.get("comm_core", 1)),
    )

    return CPSIR(
        metadata=metadata, sensors=sensors, actuators=actuators,
        physics=physics, safety=safety, control=control,
        statechart=statechart, faults=faults,
        timing=timing, deployment=deployment,
    )


def _parse_temporal(spec):
    if spec is None:
        return TemporalBound(TemporalOp.INSTANT)
    if isinstance(spec, str):
        return TemporalBound(TemporalOp(spec))
    if isinstance(spec, dict):
        return TemporalBound(
            op=TemporalOp(spec.get("op", "instant")),
            duration_ms=int(spec.get("duration_ms", 0)),
        )
    return TemporalBound(TemporalOp.INSTANT)
