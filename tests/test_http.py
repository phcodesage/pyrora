from __future__ import annotations

from starlette.testclient import TestClient

from pyrora import Controller, Pyrora, html, json, redirect, text


def test_route_decorators_sync_async_and_metadata(tmp_path):
    app = Pyrora(root_path=tmp_path)

    @app.get("/async", name="async.route", metadata={"scope": "public"})
    async def async_route(request):
        return json({"kind": "async"})

    @app.post("/sync")
    def sync_route(request):
        return {"kind": "sync"}

    client = TestClient(app)
    assert client.get("/async").json() == {"kind": "async"}
    assert client.post("/sync").json() == {"kind": "sync"}
    assert app.route_metadata[0].name == "async.route"
    assert app.route_metadata[0].metadata == {"scope": "public"}


def test_response_helpers(tmp_path):
    app = Pyrora(root_path=tmp_path)

    @app.get("/json")
    def json_response(request):
        return json({"ok": True}, 201)

    @app.get("/html")
    def html_response(request):
        return html("<b>ok</b>", 202)

    @app.get("/text")
    def text_response(request):
        return text("ok", 203)

    @app.get("/redirect")
    def redirect_response(request):
        return redirect("/json")

    client = TestClient(app)
    assert client.get("/json").status_code == 201
    assert client.get("/html").text == "<b>ok</b>"
    assert client.get("/text").status_code == 203
    response = client.get("/redirect", follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/json")


def test_controller_and_405_allow_header(tmp_path):
    app = Pyrora(root_path=tmp_path)

    class HealthController(Controller):
        async def get(self):
            return json({"status": "healthy"})

        def post(self, request):
            return {"method": request.method}

    app.controller("/health", HealthController, name="health")
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.post("/health").json() == {"method": "POST"}
    response = client.put("/health")
    assert response.status_code == 405
    assert set(response.headers["allow"].split(", ")) == {"GET", "HEAD", "POST"}


def test_router_group(tmp_path):
    from pyrora import Router

    router = Router(prefix="/v1")

    @router.get("/status")
    def status(request):
        return {"ok": True}

    app = Pyrora(root_path=tmp_path)
    app.include_router(router, prefix="/api")
    assert TestClient(app).get("/api/v1/status").json() == {"ok": True}
