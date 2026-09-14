"""Class-based HTTP controller support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.requests import Request

    from .app import Pyrora


class Controller:
    """Base class for simple HTTP-method controllers.

    Pyrora sets ``request`` and ``app`` immediately before dispatch. Implement
    one or more of ``get``, ``post``, ``put``, ``patch``, and ``delete``.
    """

    request: "Request"
    app: "Pyrora"

    def __init__(self) -> None:
        self.request: Request
        self.app: Pyrora

    def _bind(self, app: "Pyrora", request: "Request") -> None:
        self.app = app
        self.request = request

    @classmethod
    def methods(cls) -> tuple[str, ...]:
        """Return methods implemented directly by the controller hierarchy."""
        result = []
        for method in ("get", "post", "put", "patch", "delete"):
            candidate: Any = getattr(cls, method, None)
            if callable(candidate):
                result.append(method.upper())
        return tuple(result)
