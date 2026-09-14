from pyrora import Pyrora
from pyrora.realtime import WebRTCSignaling

app = Pyrora()
signaling = WebRTCSignaling(app.connections)


@app.websocket("/ws/chat")
async def chat(socket):
    await socket.accept()
    while True:
        message = await socket.receive_json()
        await socket.send_json({"echo": message})


app.websocket("/signaling/{room_id}")(signaling.endpoint)
