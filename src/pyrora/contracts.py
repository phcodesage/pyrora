"""Small extension contracts for optional Pyrora integrations.

Packages such as ``pyrora-database`` and ``pyrora-redis`` can implement these
protocols without making their dependencies part of Pyrora's core.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HealthCheck(Protocol):
    """A callable that returns a health-check result."""

    def __call__(self) -> Any: ...


@runtime_checkable
class BroadcastBackend(Protocol):
    """Future cross-process realtime backends should implement this interface."""

    async def publish(self, room: str, message: dict[str, Any]) -> None: ...


@runtime_checkable
class StorageProvider(Protocol):
    """Minimal future storage plugin contract."""

    async def get(self, key: str) -> bytes | None: ...

    async def put(self, key: str, value: bytes) -> None: ...
