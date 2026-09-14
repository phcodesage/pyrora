"""WebRTC signaling over WebSocket; never a media relay."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import uuid4

from starlette.websockets import WebSocket, WebSocketDisconnect

from .channels import ConnectionManager


class WebRTCSignaling:
    """Forward WebRTC setup messages among peers in a room.

    Pyrora only transports signaling messages. WebRTC carries audio/video
    directly between peers (or through a separately operated TURN server).
    """

    forwardable_events = {"offer", "answer", "ice-candidate", "hangup"}

    def __init__(self, manager: ConnectionManager | None = None) -> None:
        self.manager = manager or ConnectionManager()
        self._peers: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def endpoint(self, socket: WebSocket) -> None:
        """ASGI WebSocket endpoint for ``/signaling/{room_id}``."""
        room = str(socket.path_params.get("room_id", ""))
        if not room:
            await socket.close(code=1008)
            return
        peer_id = socket.query_params.get("peer_id") or uuid4().hex
        if peer_id in self._peers[room]:
            await socket.close(code=1008, reason="peer_id is already connected in this room")
            return
        await socket.accept()
        self._peers[room][peer_id] = socket
        self.manager.join(room, socket)
        await socket.send_json({"event": "room-joined", "room": room, "peer_id": peer_id})
        await self.manager.broadcast(room, {"event": "peer-joined", "peer_id": peer_id}, exclude=socket)
        try:
            while True:
                message = await socket.receive_json()
                await self._forward(room, peer_id, socket, message)
        except WebSocketDisconnect:
            pass
        finally:
            self.manager.leave(room, socket)
            self._peers[room].pop(peer_id, None)
            if not self._peers[room]:
                self._peers.pop(room, None)
            await self.manager.broadcast(room, {"event": "peer-left", "peer_id": peer_id})

    async def _forward(
        self, room: str, peer_id: str, socket: WebSocket, message: Any
    ) -> None:
        if not isinstance(message, dict):
            await socket.send_json({"event": "error", "message": "Signaling payload must be an object."})
            return
        event = message.get("event")
        if event not in self.forwardable_events:
            await socket.send_json({"event": "error", "message": f"Unsupported signaling event: {event!r}."})
            return
        forwarded = {**message, "from": peer_id}
        target = message.get("to")
        if target:
            recipient = self._peers.get(room, {}).get(str(target))
            if recipient is None:
                await socket.send_json({"event": "error", "message": f"Peer {target!r} is not in room."})
                return
            await recipient.send_json(forwarded)
            return
        await self.manager.broadcast(room, forwarded, exclude=socket)
