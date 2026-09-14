"""A deliberately small, application-scoped service container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ServiceNotFoundError(LookupError):
    """Raised when an application has not registered a requested service."""


@dataclass
class _Binding:
    provider: Any
    singleton: bool = False
    resolved: bool = False
    value: Any = None


class Container:
    """Resolve services registered on one Pyrora application.

    Providers are classes or zero-argument factories. ``singleton`` providers
    are instantiated once on first resolution; ``instance`` stores an existing
    value. The container has no process-wide state.
    """

    def __init__(self) -> None:
        self._bindings: dict[str, _Binding] = {}

    def bind(self, name: str, provider: Any) -> None:
        """Register a transient class or zero-argument factory."""
        self._validate_name(name)
        self._bindings[name] = _Binding(provider=provider)

    def singleton(self, name: str, provider: Any) -> None:
        """Register a lazy singleton class or zero-argument factory."""
        self._validate_name(name)
        self._bindings[name] = _Binding(provider=provider, singleton=True)

    def instance(self, name: str, value: Any) -> None:
        """Register an already-created service instance."""
        self._validate_name(name)
        self._bindings[name] = _Binding(provider=value, singleton=True, resolved=True, value=value)

    def resolve(self, name: str) -> Any:
        """Return a registered service or raise a clear lookup error."""
        try:
            binding = self._bindings[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._bindings)) or "none"
            raise ServiceNotFoundError(
                f"Service {name!r} is not registered. Available services: {available}."
            ) from exc
        if binding.singleton and binding.resolved:
            return binding.value
        value = self._create(binding.provider)
        if binding.singleton:
            binding.value = value
            binding.resolved = True
        return value

    def has(self, name: str) -> bool:
        """Return whether a service name is registered."""
        return name in self._bindings

    @property
    def services(self) -> tuple[str, ...]:
        """Registered service names, useful for diagnostics."""
        return tuple(self._bindings)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Service names must be non-empty strings.")

    @staticmethod
    def _create(provider: Any) -> Any:
        if isinstance(provider, type):
            return provider()
        if isinstance(provider, Callable):
            return provider()
        return provider
