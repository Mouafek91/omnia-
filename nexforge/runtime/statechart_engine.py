"""Statechart executor."""
from __future__ import annotations
from ..compiler.ir import Statechart
from ..compiler.expr import parse_untyped


class StatechartEngine:
    def __init__(self, sc: Statechart):
        self.statechart = sc
        self.current = sc.initial
        self._parsed_guards = {
            (t.from_state, t.to_state, t.priority): parse_untyped(t.guard)
            for t in sc.transitions
        }
        self._transitions_by_state = {}
        for s in sc.states:
            self._transitions_by_state[s] = sorted(
                (t for t in sc.transitions if t.from_state == s),
                key=lambda t: -t.priority)

    def tick(self, context):
        transitions = self._transitions_by_state.get(self.current, [])
        for t in transitions:
            key = (t.from_state, t.to_state, t.priority)
            try:
                if bool(self._parsed_guards[key].evaluate(context)):
                    self.current = t.to_state
                    return self.current
            except Exception: continue
        return self.current
