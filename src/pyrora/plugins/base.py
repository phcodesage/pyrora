"""Base class for Pyrora plugins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyrora.app import Pyrora


class Plugin:
    """A provider-like extension point.

    ``register`` is called synchronously at explicit installation time. Use it
    to add services, routes, middleware, commands, templates, static files,
    configuration defaults, and event listeners. ``boot`` runs once during the
    application's ASGI startup lifecycle and may be async.
    """

    name: str | None = None
    version = "0.1.0"
    dependencies: Sequence[str] = ()
    config_defaults: Mapping[str, object] = {}

    def register(self, app: "Pyrora") -> None:
        """Register synchronous application extensions."""

    async def boot(self, app: "Pyrora") -> None:
        """Optionally initialize resources after ASGI startup."""
