# Realtime and WebRTC

`app.websocket(path)` receives Starlette's WebSocket with `accept`, `send_text`,
`send_json`, `receive_text`, `receive_json`, and `close`. Pyrora removes sockets
from its in-memory rooms when the handler disconnects.

```python
app.connections.join("support", socket)
await app.connections.broadcast("support", {"event": "message", "data": data})
```

`WebRTCSignaling` forwards room join/leave, offers, answers, ICE candidates,
and hang-up events over WebSockets. It is signaling only: audio and video flow
peer-to-peer through WebRTC; Pyrora neither relays nor records media. Production
deployments often need STUN/TURN (for example Coturn). Larger products may use
LiveKit, mediasoup, or other dedicated media infrastructure.

The default room backend is process-local. Use a future Redis or Socket.IO
adapter for cross-worker fan-out; neither is a Pyrora core dependency.
