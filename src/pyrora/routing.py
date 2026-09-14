"""Composable route collection used by applications and plugins."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RouteDefinition:
    path: str
    endpoint: Callable[..., Any]
    methods: tuple[str, ...] = ("GET",)
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Router:
    """A route group that can be attached to a :class:`pyrora.Pyrora` app."""

    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix.rstrip("/")
        self.definitions: list[RouteDefinition] = []

    def route(
        self,
        path: str,
        *,
        methods: Iterable[str] | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        route_methods = tuple(method.upper() for method in (methods or ("GET",)))

        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.definitions.append(RouteDefinition(path, endpoint, route_methods, name, metadata or {}))
            return endpoint

        return decorator

    def _method(self, method: str, path: str, **kwargs: Any):
        return self.route(path, methods=(method,), **kwargs)

    def get(self, path: str, **kwargs: Any):
        return self._method("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self._method("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any):
        return self._method("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any):
        return self._method("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any):
        return self._method("DELETE", path, **kwargs)
