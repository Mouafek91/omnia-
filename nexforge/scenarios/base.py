"""Scenario abstraction + global registry."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Disturbance:
    at_seconds: float
    channel: str
    value: any
    duration_s: float = 0.0


class Scenario(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def description(self) -> str: ...
    @abstractmethod
    def disturbances(self, duration_s: float) -> list: ...
    def applicable_to(self, domain_name: str) -> bool:
        return True


class ScenarioLibrary:
    def __init__(self):
        self._scenarios = {}

    def register(self, s):
        self._scenarios[s.name] = s

    def get(self, name):
        if name not in self._scenarios:
            raise KeyError(f"Unknown scenario: {name}. Available: {sorted(self._scenarios)}")
        return self._scenarios[name]

    def list(self):
        return sorted(self._scenarios.values(), key=lambda s: s.name)

    def applicable_to(self, domain_name):
        return [s for s in self._scenarios.values() if s.applicable_to(domain_name)]


LIBRARY = ScenarioLibrary()


def register(s):
    """Decorator to register a Scenario class or instance."""
    # Automatically instantiate if a class is passed
    instance = s() if isinstance(s, type) else s
    LIBRARY.register(instance)
    return instance