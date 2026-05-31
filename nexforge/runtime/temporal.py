"""Temporal contract evaluator: for/within/after/rise/fall/stable."""
from __future__ import annotations
from array import array


class TemporalEngine:
    def __init__(self, n_contracts):
        self._true_since = array("q", [0] * n_contracts)
        self._false_since = array("q", [0] * n_contracts)
        self._last_value = array("b", [0] * n_contracts)
        self._stable_since = array("q", [0] * n_contracts)
        self._n = n_contracts

    def tick(self, idx, value, now_ms):
        prev = bool(self._last_value[idx])
        if value != prev:
            if value: self._true_since[idx] = now_ms
            else: self._false_since[idx] = now_ms
            self._stable_since[idx] = now_ms
            self._last_value[idx] = int(value)

    def for_duration(self, idx, value, duration_ms, now_ms):
        if not value: return False
        return (now_ms - self._true_since[idx]) >= duration_ms

    def within_duration(self, idx, value, duration_ms, now_ms):
        if value: return (now_ms - self._true_since[idx]) <= duration_ms
        return False

    def after_duration(self, idx, duration_ms, now_ms):
        return (now_ms - self._true_since[idx]) >= duration_ms

    def rise(self, idx, value):
        return value and not bool(self._last_value[idx])

    def fall(self, idx, value):
        return (not value) and bool(self._last_value[idx])

    def stable(self, idx, value, duration_ms, now_ms):
        if value != bool(self._last_value[idx]): return False
        return (now_ms - self._stable_since[idx]) >= duration_ms
