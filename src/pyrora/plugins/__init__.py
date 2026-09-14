"""Pyrora's explicit, provider-style plugin APIs."""

from .base import Plugin
from .manager import PluginError, PluginManager

__all__ = ["Plugin", "PluginError", "PluginManager"]
