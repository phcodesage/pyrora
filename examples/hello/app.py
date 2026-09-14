from pyrora import Pyrora, json, render

app = Pyrora(debug=True)


@app.get("/")
async def home(request):
    return render(request, "home.html", title="Hello, Pyrora")


@app.get("/api/health")
async def health(request):
    return json({"ok": True})
