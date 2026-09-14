# Your first Pyrora app

```python
from pyrora import Pyrora, json, render

app = Pyrora(debug=True)

@app.get("/")
async def home(request):
    return render(request, "home.html", title="Hello, Pyrora")

@app.get("/api/health")
def health(request):
    return json({"ok": True})
```

Put `home.html` in `templates/` and static assets in `static/`. Run with
`pyrora serve --reload`. Handlers may be normal functions or coroutines.

For grouped routes, create a `Router` and call `app.include_router(router,
prefix="/api")`. `app.route`, `get`, `post`, `put`, `patch`, and `delete`
accept names and metadata for route tooling.
