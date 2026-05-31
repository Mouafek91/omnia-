"""Plugin interfaces."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PluginMetadata:
    name: str
    version: str
    author: str
    description: str
    kind: str


class Plugin(ABC):
    @abstractmethod
    def metadata(self) -> PluginMetadata: ...
    @abstractmethod
    def register(self, registry): ...


class DomainPlugin(Plugin):
    @abstractmethod
    def yaml_path(self) -> Path: ...


class BoardPlugin(Plugin):
    @abstractmethod
    def hardware_profile(self): ...


class ProtocolPlugin(Plugin):
    @abstractmethod
    def comm_driver_factory(self): ...


class ValidatorPlugin(Plugin):
    @abstractmethod
    def validate(self, ir): ...


class DashboardPlugin(Plugin):
    @abstractmethod
    def widget_html(self) -> str: ...
    @abstractmethod
    def data_endpoint(self) -> str: ...
