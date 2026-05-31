"""
SI-based dimensional analysis.

Every physical quantity has a dimension vector of 7 exponents:
(L, M, T, Θ, I, N, J) = (Length, Mass, Time, Temperature, Current, Amount, Luminosity)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


L, M, T, THETA, I, N, J = 0, 1, 2, 3, 4, 5, 6
ZERO_DIM: Tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0)


@dataclass(frozen=True)
class Dimension:
    """7-tuple of SI exponents."""
    vec: Tuple[int, ...]

    def __post_init__(self):
        if len(self.vec) != 7:
            raise ValueError(f"Dimension must have 7 components, got {len(self.vec)}")

    def __mul__(self, other: "Dimension") -> "Dimension":
        return Dimension(tuple(a + b for a, b in zip(self.vec, other.vec)))

    def __truediv__(self, other: "Dimension") -> "Dimension":
        return Dimension(tuple(a - b for a, b in zip(self.vec, other.vec)))

    def __pow__(self, n: int) -> "Dimension":
        return Dimension(tuple(a * n for a in self.vec))

    def is_dimensionless(self) -> bool:
        return self.vec == ZERO_DIM

    def __eq__(self, other) -> bool:
        return isinstance(other, Dimension) and self.vec == other.vec

    def __hash__(self) -> int:
        return hash(self.vec)


# Canonical dimensions
DIMENSIONLESS = Dimension(ZERO_DIM)
BOOLEAN = Dimension((-1, -1, -1, -1, -1, -1, -1))
LENGTH = Dimension((1, 0, 0, 0, 0, 0, 0))
MASS = Dimension((0, 1, 0, 0, 0, 0, 0))
TIME = Dimension((0, 0, 1, 0, 0, 0, 0))
TEMPERATURE = Dimension((0, 0, 0, 1, 0, 0, 0))
CURRENT = Dimension((0, 0, 0, 0, 1, 0, 0))
VELOCITY = LENGTH / TIME
ACCELERATION = VELOCITY / TIME
FORCE = MASS * ACCELERATION
ENERGY = FORCE * LENGTH
POWER = ENERGY / TIME
VOLTAGE = POWER / CURRENT
RESISTANCE = VOLTAGE / CURRENT
PRESSURE = FORCE / (LENGTH ** 2)
VOLUME = LENGTH ** 3
FLOW_RATE = VOLUME / TIME
ANGLE = DIMENSIONLESS
ANGULAR_VEL = ANGLE / TIME


@dataclass(frozen=True)
class Unit:
    """Named unit with dimension and scale factor."""
    name: str
    dimension: Dimension
    scale: float = 1.0

    def __repr__(self) -> str:
        return self.name


UNITS: dict[str, Unit] = {
    "1":        Unit("1", DIMENSIONLESS),
    "bool":     Unit("bool", BOOLEAN),
    "percent":  Unit("percent", DIMENSIONLESS, 0.01),
    "count":    Unit("count", DIMENSIONLESS),
    "m":        Unit("m", LENGTH),
    "mm":       Unit("mm", LENGTH, 0.001),
    "s":        Unit("s", TIME),
    "ms":       Unit("ms", TIME, 0.001),
    "Hz":       Unit("Hz", DIMENSIONLESS / TIME),
    "kg":       Unit("kg", MASS),
    "K":        Unit("K", TEMPERATURE),
    "degC":     Unit("degC", TEMPERATURE),
    "A":        Unit("A", CURRENT),
    "mA":       Unit("mA", CURRENT, 0.001),
    "V":        Unit("V", VOLTAGE),
    "W":        Unit("W", POWER),
    "ohm":      Unit("ohm", RESISTANCE),
    "N":        Unit("N", FORCE),
    "Nm":       Unit("Nm", ENERGY),
    "Pa":       Unit("Pa", PRESSURE),
    "bar":      Unit("bar", PRESSURE, 1e5),
    "m/s":      Unit("m/s", VELOCITY),
    "m/s^2":    Unit("m/s^2", ACCELERATION),
    "deg":      Unit("deg", ANGLE, 0.0174533),
    "rad":      Unit("rad", ANGLE),
    "deg/s":    Unit("deg/s", ANGULAR_VEL, 0.0174533),
    "dps":      Unit("dps", ANGULAR_VEL, 0.0174533),
    "rpm":      Unit("rpm", DIMENSIONLESS / TIME, 1.0 / 60.0),
    "L":        Unit("L", VOLUME, 0.001),
    "L/min":    Unit("L/min", FLOW_RATE, 0.001 / 60.0),
    "n/cm2/s":  Unit("n/cm2/s", DIMENSIONLESS / (LENGTH ** 2) / TIME),
}


def lookup_unit(name: str) -> Unit:
    if name not in UNITS:
        raise KeyError(f"Unknown unit: '{name}'")
    return UNITS[name]


class DimensionError(Exception):
    pass


def check_additive_compat(a: Unit, b: Unit, op: str) -> Unit:
    if a.dimension != b.dimension:
        raise DimensionError(
            f"Cannot {op} {a.name} with {b.name}: "
            f"dimensions {a.dimension.vec} vs {b.dimension.vec}")
    return a
