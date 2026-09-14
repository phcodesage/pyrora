# Pyrora

> **Alpha software — API feedback welcome.** Pyrora is a lightweight,
> Laravel-inspired developer experience for Python web applications. It uses
> Starlette for ASGI HTTP, Jinja2 for server-rendered templates, and keeps
> databases, authentication, queues, mail, billing, admin panels, Redis
> broadcasting, and media servers as separate plugins or integrations.

Pyrora exists for teams who want an ergonomic, batteries-available application
shape without a mandatory ORM, frontend, message broker, or global registry.
Its core package depends only on Starlette and Jinja2.

## Install

```bash
pip install "pyrora[server]"
pyrora new blog
cd blog
python -m venv .venv
source .venv/bin/activate
pip install -e .
pyrora serve --reload
```

## Quick start

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

`templates/` and `static/` are discovered automatically. Template autoescaping
is enabled by default. Response helpers are `json`, `html`, `text`, and
`redirect`.

## Routing and controllers

Use `app.route(..., methods=[...])` or the `get`, `post`, `put`, `patch`, and
`delete` decorators. Routes accept a `name` and free-form `metadata`; attach a
`Router` with `app.include_router(router, prefix="/api")`.

```python
from pyrora import Controller, json

class HealthController(Controller):
    async def get(self):
        return json({"status": "healthy"})

app.controller("/health", HealthController)
```

Controller methods map directly to verbs. Unsupported methods receive a 405
response and `Allow` header from Starlette.

## Configuration and services

`Config` merges defaults, `.env`, then environment variables. Use
`config.get("APP_DEBUG", cast=bool)`, `config.require("SECRET_KEY")`, and
`config.plugin("billing").get("currency")`. The container is application-scoped:

```python
app.container.bind("mailer", Mailer)
app.container.singleton("cache", Cache())
app.container.instance("settings", settings)
```

## Plugins

Plugins are manually installed provider objects. They can register services,
routes, middleware, commands, event listeners, template/static directories,
defaults, health checks, and lifecycle hooks.

```python
from pyrora.plugins import Plugin

class BillingPlugin(Plugin):
    name = "billing"
    version = "0.1.0"
    def register(self, app):
        app.add_route("/billing/health", self.health)

app.install(BillingPlugin())
```

`pyrora plugins list` reports installed providers; `pyrora plugins discover`
only lists entry points and never auto-loads arbitrary packages. See
[plugin documentation](docs/plugins.md) and the complete local example.

## WebSockets and WebRTC signaling

Use `@app.websocket("/ws/chat")` with Starlette’s `accept`, `send_*`,
`receive_*`, and `close` methods. `app.connections` offers local rooms and
`await manager.broadcast(room, message)`. `WebRTCSignaling` handles room
membership and forward-only offer, answer, ICE candidate, and hang-up messages.

Pyrora provides **signaling only**. WebRTC audio/video is peer-to-peer and
Pyrora is not a media relay or recorder. Production often needs STUN/TURN
(Coturn); large deployments may use LiveKit, mediasoup, or related media
infrastructure. Read [realtime documentation](docs/realtime.md).

## Optional React starter

```bash
pyrora new realtime-app --react
cd realtime-app
pyrora frontend install
pyrora frontend dev
```

The generated React + TypeScript + Vite app includes a responsive shell, API
client, WebSocket helper, native WebRTC helper, chat screen, room screen, Vite
development proxy/CORS configuration, and same-origin production support. React
is never required for Jinja-only or API-only projects. A built frontend can be
served with `Pyrora(frontend_dist="frontend/dist", spa_fallback=True)`.

## Project structure

```text
src/pyrora/        framework core
tests/             pytest suite
docs/              focused guides
examples/          hello, plugin, realtime, React starter guide
```

## Development

```bash
pip install -e ".[dev,server]"
pytest
ruff check src tests
python -m build
```

## Current limitations and roadmap

This 0.1.0 release is an in-process MVP. Its room backend does not broadcast
between workers, there is no persistence or authentication, and WebRTC does not
provide TURN/media infrastructure. Planned ecosystem packages include
`pyrora-database`, `pyrora-auth`, `pyrora-queue`, `pyrora-mail`, `pyrora-admin`,
`pyrora-redis`, and `pyrora-socketio`. The recommended next plugin is
`pyrora-database`: it can implement an explicit connection/session contract
without imposing SQLAlchemy or a database on every Pyrora app.

## License

MIT. See [LICENSE](LICENSE).
