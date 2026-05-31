"""Statechart validation: reachability + determinism."""
from __future__ import annotations
from ..ir import CPSIR, CPSSystemState
from ..expr import parse_untyped, ExpressionError


class StatechartError(Exception):
    pass


def validate_statechart(ir: CPSIR):
    sc = ir.statechart
    if sc.initial not in sc.states:
        raise StatechartError(f"Initial state {sc.initial} not declared")
    for t in sc.transitions:
        if t.from_state not in sc.states:
            raise StatechartError(f"Transition from unknown state: {t.from_state}")
        if t.to_state not in sc.states:
            raise StatechartError(f"Transition to unknown state: {t.to_state}")
        try:
            parse_untyped(t.guard)
        except ExpressionError as e:
            raise StatechartError(f"Guard invalid: {e}")
    reachable = {sc.initial}; frontier = [sc.initial]
    while frontier:
        s = frontier.pop()
        for t in sc.transitions:
            if t.from_state == s and t.to_state not in reachable:
                reachable.add(t.to_state); frontier.append(t.to_state)
    unreachable = set(sc.states) - reachable
    if unreachable:
        raise StatechartError(f"Unreachable states: {unreachable}")
    for t in sc.transitions:
        if t.from_state == CPSSystemState.SHUTDOWN:
            raise StatechartError("SHUTDOWN must not have outgoing transitions")
