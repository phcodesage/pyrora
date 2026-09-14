"""A complete local example of the Pyrora plugin/provider contract."""

from __future__ import annotations

from pathlib import Path

from pyrora import json, render
from pyrora.plugins import Plugin


class BillingService:
    def status(self) -> str:
        return "ready"


class ExampleBillingPlugin(Plugin):
    name = "example-billing"
    version = "0.1.0"
    config_defaults = {"EXAMPLE_BILLING_CURRENCY": "USD"}

    def register(self, app):
        root = Path(__file__).parent
        app.container.singleton("billing", BillingService)
        app.add_route("/billing/health", self.health, name="billing.health")
        app.add_route("/billing", self.dashboard, name="billing.dashboard")
        app.add_template_directory(root / "templates")
        app.mount_static("/billing-assets", root / "static", name="billing-assets")
        app.add_command("billing:status", self.command)
        app.add_health_check("billing", lambda: app.container.resolve("billing").status() == "ready")
        app.on("invoice.created")(self.on_invoice_created)

    async def boot(self, app):
        app.container.resolve("billing")

    async def health(self, request):
        return json({"plugin": self.name, "status": "ok"})

    async def dashboard(self, request):
        return render(request, "billing.html", currency=request.app.state.pyrora.config.plugin("example_billing").get("currency"))

    def command(self):
        print("Billing plugin is ready")

    def on_invoice_created(self, invoice):
        return invoice
