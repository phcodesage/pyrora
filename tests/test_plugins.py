from __future__ import annotations

from starlette.testclient import TestClient

from pyrora import Pyrora, json
from pyrora.plugins import Plugin, PluginError


class DemoPlugin(Plugin):
    name = "demo"
    version = "1.2.3"
    config_defaults = {"DEMO_ENABLED": "yes"}

    def __init__(self):
        self.booted = False

    def register(self, app):
        app.container.singleton("demo-service", lambda: {"service": "demo"})
        app.add_route("/plugin", self.endpoint, name="demo.endpoint")
        app.add_command("demo:hello", lambda: "hello")
        app.add_health_check("demo", lambda: True)
        app.on("demo.event")(lambda value: value + 1)

    async def boot(self, app):
        self.booted = True

    async def endpoint(self, request):
        return json({"plugin": self.name})


def test_plugin_registration_route_service_commands_events_and_lifecycle(tmp_path):
    app = Pyrora(root_path=tmp_path)
    plugin = app.install(DemoPlugin())
    assert app.container.resolve("demo-service") == {"service": "demo"}
    assert app.config.get("DEMO_ENABLED") == "yes"
    assert "demo:hello" in app.commands
    assert TestClient(app).get("/plugin").json() == {"plugin": "demo"}
    with TestClient(app):
        assert plugin.booted
    import asyncio

    assert asyncio.run(app.dispatch_event("demo.event", 4)) == [5]
    assert asyncio.run(app.health())["demo"]["ok"] is True


def test_duplicate_and_dependency_errors(tmp_path):
    app = Pyrora(root_path=tmp_path)
    app.install(DemoPlugin())
    with __import__("pytest").raises(PluginError, match="already installed"):
        app.install(DemoPlugin())

    class NeedsDemo(Plugin):
        name = "needs-demo"
        dependencies = ("missing",)

    with __import__("pytest").raises(PluginError, match="requires"):
        Pyrora(root_path=tmp_path).install(NeedsDemo())


def test_plugin_discovery_does_not_import_entries(tmp_path, monkeypatch):
    class Entry:
        name = "third-party"
        value = "third_party:Plugin"

        def load(self):
            raise AssertionError("discovery must not load entry points")

    class Entries:
        def select(self, **kwargs):
            assert kwargs["group"] == "pyrora.plugins"
            return [Entry()]

    monkeypatch.setattr("pyrora.plugins.manager.metadata.entry_points", lambda: Entries())
    app = Pyrora(root_path=tmp_path)
    assert app.plugins.discover() == {"third-party": "third_party:Plugin"}
