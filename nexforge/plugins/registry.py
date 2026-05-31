"""Plugin registry + discovery."""
from __future__ import annotations
import importlib
import importlib.util
from pathlib import Path


class PluginRegistry:
    def __init__(self):
        self._plugins = {}
        self._domains = []
        self._boards = []
        self._protocols = []
        self._validators = []
        self._dashboards = []

    def register(self, plugin):
        from .interfaces import (
            DomainPlugin, BoardPlugin, ProtocolPlugin,
            ValidatorPlugin, DashboardPlugin)
        meta = plugin.metadata()
        if meta.name in self._plugins:
            raise ValueError(f"Plugin '{meta.name}' already registered")
        self._plugins[meta.name] = plugin
        plugin.register(self)
        if isinstance(plugin, DomainPlugin): self._domains.append(plugin)
        if isinstance(plugin, BoardPlugin): self._boards.append(plugin)
        if isinstance(plugin, ProtocolPlugin): self._protocols.append(plugin)
        if isinstance(plugin, ValidatorPlugin): self._validators.append(plugin)
        if isinstance(plugin, DashboardPlugin): self._dashboards.append(plugin)

    def discover_entrypoints(self):
        try:
            from importlib.metadata import entry_points
        except ImportError: return 0
        count = 0
        for ep in entry_points().get("nexforge.plugins", []):
            try:
                plugin = ep.load()()
                self.register(plugin); count += 1
            except Exception: pass
        return count

    def discover_directory(self, directory):
        directory = Path(directory)
        if not directory.exists(): return 0
        count = 0
        for path in directory.glob("*.py"):
            if path.name.startswith("_"): continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"nexforge_plugin_{path.stem}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "PLUGIN"):
                    self.register(module.PLUGIN); count += 1
            except Exception: pass
        return count

    def summary(self):
        return {"total": len(self._plugins), "domains": len(self._domains),
                "boards": len(self._boards), "protocols": len(self._protocols),
                "validators": len(self._validators),
                "dashboard_widgets": len(self._dashboards)}
