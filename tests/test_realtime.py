from __future__ import annotations

from starlette.testclient import TestClient

from pyrora import Pyrora
from pyrora.realtime import WebRTCSignaling


def test_websocket_json_echo(tmp_path):
    app = Pyrora(root_path=tmp_path)

    @app.websocket("/ws/chat")
    async def chat(socket):
        await socket.accept()
        message = await socket.receive_json()
        await socket.send_json({"echo": message})

    with TestClient(app).websocket_connect("/ws/chat") as socket:
        socket.send_json({"text": "hello"})
        assert socket.receive_json() == {"echo": {"text": "hello"}}


def test_room_broadcast_and_disconnect_cleanup(tmp_path):
    app = Pyrora(root_path=tmp_path)

    @app.websocket("/ws/{room}")
    async def room(socket):
        await socket.accept()
        room_name = socket.path_params["room"]
        app.connections.join(room_name, socket)
        while True:
            message = await socket.receive_json()
            await app.connections.broadcast(room_name, message)

    client = TestClient(app)
    with client.websocket_connect("/ws/team") as first:
        with client.websocket_connect("/ws/team") as second:
            first.send_json({"event": "hello"})
            assert second.receive_json() == {"event": "hello"}
    assert app.connections.members("team") == ()


def test_webrtc_signaling_forwards_offer_and_peer_events(tmp_path):
    app = Pyrora(root_path=tmp_path)
    signaling = WebRTCSignaling(app.connections)
    app.websocket("/signaling/{room_id}")(signaling.endpoint)
    client = TestClient(app)
    with client.websocket_connect("/signaling/demo?peer_id=one") as first:
        assert first.receive_json()["event"] == "room-joined"
        with client.websocket_connect("/signaling/demo?peer_id=two") as second:
            assert second.receive_json()["event"] == "room-joined"
            assert first.receive_json() == {"event": "peer-joined", "peer_id": "two"}
            first.send_json({"event": "offer", "to": "two", "sdp": {"type": "offer", "sdp": "x"}})
            offer = second.receive_json()
            assert offer["event"] == "offer"
            assert offer["from"] == "one"
        assert first.receive_json() == {"event": "peer-left", "peer_id": "two"}
