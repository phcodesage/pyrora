from __future__ import annotations

from starlette.testclient import TestClient

from pyrora import Pyrora, render


def test_jinja_rendering_and_autoescape(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "profile.html").write_text("<h1>{{ title }}</h1><p>{{ user }}</p>", encoding="utf-8")
    app = Pyrora(root_path=tmp_path)

    @app.get("/")
    async def profile(request):
        return render(request, "profile.html", title="Profile", user="<script>unsafe()</script>")

    response = TestClient(app).get("/")
    assert "<h1>Profile</h1>" in response.text
    assert "&lt;script&gt;unsafe()&lt;/script&gt;" in response.text


def test_static_files_and_default_middleware(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "app.css").write_text("body { color: red; }", encoding="utf-8")
    app = Pyrora(root_path=tmp_path)

    @app.get("/")
    def home(request):
        return "ok"

    client = TestClient(app)
    response = client.get("/", headers={"X-Request-ID": "given"})
    assert response.headers["x-request-id"] == "given"
    assert "x-process-time" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/static/app.css").text == "body { color: red; }"


def test_plugin_template_directory(tmp_path):
    extra = tmp_path / "plugin-templates"
    extra.mkdir()
    (extra / "hello.html").write_text("hello {{ name }}", encoding="utf-8")
    app = Pyrora(root_path=tmp_path)
    app.add_template_directory(extra)

    @app.get("/")
    def home(request):
        return render(request, "hello.html", name="Pyrora")

    assert TestClient(app).get("/").text == "hello Pyrora"
