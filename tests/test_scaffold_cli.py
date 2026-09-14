from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from pyrora import Pyrora
from pyrora.commands import main
from pyrora.scaffold import create_project


def test_project_generation_and_generated_backend_smoke(tmp_path, monkeypatch):
    create_project(tmp_path / "blog")
    project = tmp_path / "blog"
    assert (project / "backend" / "app.py").is_file()
    assert (project / "templates").exists() is False
    monkeypatch.syspath_prepend(str(project))
    import importlib

    generated = importlib.import_module("backend.app")
    assert TestClient(generated.app).get("/api/health").json() == {"ok": True}


def test_react_generation_contains_expected_files(tmp_path):
    create_project(tmp_path / "realtime-app", react=True)
    frontend = tmp_path / "realtime-app" / "frontend"
    for filename in [
        "package.json",
        "index.html",
        "vite.config.ts",
        "src/App.tsx",
        "src/api.ts",
        "src/realtime.ts",
        "src/webrtc.ts",
        "src/components/AppShell.tsx",
        "src/pages/ChatPage.tsx",
        "src/pages/RoomPage.tsx",
    ]:
        assert (frontend / filename).is_file()


def test_spa_fallback_keeps_api_routes_first(tmp_path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<div id='app'>frontend</div>", encoding="utf-8")
    (dist / "asset.js").write_text("console.log('asset')", encoding="utf-8")
    app = Pyrora(root_path=tmp_path, frontend_dist=dist, spa_fallback=True)

    @app.get("/api/health")
    def health(request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/health").json() == {"ok": True}
    assert "frontend" in client.get("/dashboard/settings").text
    assert "asset" in client.get("/asset.js").text


def test_cli_new_and_makers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "dashboard"]) == 0
    monkeypatch.chdir(tmp_path / "dashboard")
    assert main(["make:controller", "UserController"]) == 0
    assert main(["make:view", "dashboard/home"]) == 0
    assert (tmp_path / "dashboard" / "controllers" / "user_controller.py").is_file()
    assert (tmp_path / "dashboard" / "templates" / "dashboard" / "home.html").is_file()


def test_cli_routes_and_plugins_list(tmp_path, monkeypatch, capsys):
    (tmp_path / "app.py").write_text(
        "from pyrora import Pyrora\napp=Pyrora(root_path=r'%s')\n@app.get('/ok', name='ok')\ndef ok(request): return {'ok': True}\n"
        % tmp_path,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    assert main(["routes", "--app", "app:app"]) == 0
    assert "/ok" in capsys.readouterr().out
    assert main(["plugins", "--app", "app:app", "list"]) == 0
    assert "No plugins" in capsys.readouterr().out


def test_cli_frontend_build_invokes_npm(tmp_path, monkeypatch):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pyrora.commands.shutil.which", lambda name: "/usr/bin/npm")

    class Completed:
        returncode = 0

    called = {}

    def run(command, cwd, check):
        called.update(command=command, cwd=cwd, check=check)
        return Completed()

    monkeypatch.setattr("pyrora.commands.subprocess.run", run)
    assert main(["frontend", "build"]) == 0
    assert called["command"] == ["/usr/bin/npm", "run", "build"]
    assert called["cwd"] == frontend
