import pytest
# Explicitly import builtin to guarantee @register runs during test collection
import nexforge.scenarios.builtin  # noqa: F401
from nexforge.scenarios.base import LIBRARY


def test_builtin_scenarios_registered():
    names = {s.name for s in LIBRARY.list()}
    assert "motor_failure" in names
    assert "sensor_stuck" in names
    assert "overheating" in names


def test_scenario_applicability():
    motor = LIBRARY.get("motor_failure")
    assert motor.applicable_to("pump")
    assert not motor.applicable_to("cold_storage")


def test_scenario_disturbances_deterministic():
    noisy = LIBRARY.get("noisy_signal")
    d1 = noisy.disturbances(30.0)
    d2 = noisy.disturbances(30.0)
    assert d1 == d2


