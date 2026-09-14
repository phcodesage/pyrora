"""Connection rooms backed by application-local memory."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Protocol

from starlette.websockets import WebSocket


class ConnectionBackend(Protocol):
    """Adapter contract for future cross-process connection backends."""

    def join(self, room: str, socket: WebSocket) -> None: ...

    def leave(self, room: str, socket: WebSocket) -> None: ...

    def leave_all(self, socket: WebSocket) -> None: ...

    def members(self, room: str) -> Iterable[WebSocket]: ...


class InMemoryConnectionBackend:
    """A process-local room backend suited to one ASGI worker."""

    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)

    def join(self, room: str, socket: WebSocket) -> None:
        self.rooms[room].add(socket)

    def leave(self, room: str, socket: WebSocket) -> None:
        members = self.rooms.get(room)
        if not members:
            return
        members.discard(socket)
        if not members:
            self.rooms.pop(room, None)

    def leave_all(self, socket: WebSocket) -> None:
        for room in tuple(self.rooms):
            self.leave(room, socket)

    def members(self, room: str) -> Iterable[WebSocket]:
        return tuple(self.rooms.get(room, ()))


class ConnectionManager:
    """Join sockets to rooms and broadcast JSON or text messages.

    The default backend has no cross-worker semantics. A Redis or Socket.IO
    adapter can implement ``ConnectionBackend`` in a separate optional package.
    """

    def __init__(self, backend: ConnectionBackend | None = None) -> None:
        self.backend = backend or InMemoryConnectionBackend()

    def join(self, room: str, socket: WebSocket) -> None:
        self.backend.join(room, socket)

    def leave(self, room: str, socket: WebSocket) -> None:
        self.backend.leave(room, socket)

    def leave_all(self, socket: WebSocket) -> None:
        self.backend.leave_all(socket)

    def members(self, room: str) -> tuple[WebSocket, ...]:
        return tuple(self.backend.members(room))

    async def broadcast(
        self, room: str, message: Any, *, exclude: WebSocket | None = None
    ) -> None:
        """Send JSON ``message`` to room members, ignoring disconnected peers."""
        for socket in self.members(room):
            if socket is exclude:
                continue
            try:
                await socket.send_json(message)
            except RuntimeError:
                self.leave(room, socket)

    async def broadcast_text(
        self, room: str, message: str, *, exclude: WebSocket | None = None
    ) -> None:
        for socket in self.members(room):
            if socket is exclude:
                continue
            try:
                await socket.send_text(message)
            except RuntimeError:
                self.leave(room, socket)
