"""Explicit plugin registration and safe entry-point discovery."""

from __future__ import annotations

import inspect
from importlib import metadata
from typing import TYPE_CHECKING, Any

from .base import Plugin

if TYPE_CHECKING:
    from pyrora.app import Pyrora


class PluginError(RuntimeError):
    """Raised for invalid plugin installation or lifecycle failures."""


class PluginManager:
    """Own the plugins installed on one application instance.

    Discovery only lists entry points. Loading external code always requires an
    explicit call to :meth:`install_entry_point` or :meth:`Pyrora.install`.
    """

    entry_point_group = "pyrora.plugins"

    def __init__(self, app: "Pyrora") -> None:
        self.app = app
        self._plugins: dict[str, Plugin] = {}
        self._booted: set[str] = set()

    @property
    def installed(self) -> tuple[Plugin, ...]:
        return tuple(self._plugins.values())

    def get(self, name: str) -> Plugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginError(f"Plugin {name!r} is not installed.") from exc

    def install(self, plugin: Plugin | type[Plugin]) -> Plugin:
        """Synchronously register a manually selected plugin."""
        instance = plugin() if inspect.isclass(plugin) else plugin
        if not isinstance(instance, Plugin):
            raise PluginError("Plugins must inherit from pyrora.plugins.Plugin.")
        name = instance.name or instance.__class__.__name__.removesuffix("Plugin").lower()
        if not name:
            raise PluginError("Plugin names must be non-empty.")
        if name in self._plugins:
            raise PluginError(f"Plugin {name!r} is already installed.")
        missing = [dependency for dependency in instance.dependencies if dependency not in self._plugins]
        if missing:
            raise PluginError(
                f"Plugin {name!r} requires installed dependencies: {', '.join(missing)}."
            )
        instance.name = name
        self.app.config.add_defaults(instance.config_defaults)
        try:
            instance.register(self.app)
        except Exception as exc:
            raise PluginError(f"Plugin {name!r} failed during register(): {exc}") from exc
        self._plugins[name] = instance
        return instance

    async def boot(self) -> None:
        """Run each installed plugin's boot hook at most once."""
        for name, plugin in self._plugins.items():
            if name in self._booted:
                continue
            try:
                result = plugin.boot(self.app)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                raise PluginError(f"Plugin {name!r} failed during boot(): {exc}") from exc
            self._booted.add(name)

    def discover(self) -> dict[str, str]:
        """Return discoverable plugin names and import targets without loading them."""
        all_entries = metadata.entry_points()
        entries: Any
        if hasattr(all_entries, "select"):
            entries = all_entries.select(group=self.entry_point_group)
        else:  # Python 3.10 compatibility
            entries = all_entries.get(self.entry_point_group, ())
        return {entry.name: entry.value for entry in entries}

    def install_entry_point(self, name: str) -> Plugin:
        """Load and install one explicitly named discovered plugin."""
        all_entries = metadata.entry_points()
        entries = (
            all_entries.select(group=self.entry_point_group, name=name)
            if hasattr(all_entries, "select")
            else [entry for entry in all_entries.get(self.entry_point_group, ()) if entry.name == name]
        )
        entry = next(iter(entries), None)
        if entry is None:
            raise PluginError(f"No Pyrora plugin entry point named {name!r} was found.")
        try:
            loaded = entry.load()
        except Exception as exc:
            raise PluginError(f"Could not load plugin entry point {name!r}: {exc}") from exc
        return self.install(loaded)
