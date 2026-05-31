"""Shared helper for building name→unit maps."""
from ..ir import CPSIR
from ..units import Unit


def build_name_units(ir: CPSIR) -> dict:
    name_units = {}
    for s in ir.sensors:
        name_units[s.name] = s.quantity.unit
    for a in ir.actuators:
        name_units[a.name] = a.quantity.unit
    for sv in ir.physics.states:
        name_units[sv.name] = sv.unit
    return name_units
