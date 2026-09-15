"""A small commerce API deployed as a Pyrora ASGI app on Cloudflare Workers.

The API persists a product catalog and submitted orders in Cloudflare D1. It
does not take payments; payment capture and fulfilment are intentionally left
to a separately configured commerce integration.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import uuid4

from pyrora import Pyrora, json
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StoreInputError(ValueError):
    """Raised when a submitted order cannot be accepted."""


class StoreRepository(Protocol):
    """Persistence boundary for the store's catalog and submitted orders."""

    async def list_products(self, request: Request) -> list[dict[str, Any]]: ...

    async def create_order(
        self, request: Request, *, email: str, items: list[dict[str, Any]]
    ) -> dict[str, Any]: ...


class D1StoreRepository:
    """Cloudflare D1 implementation using the ASGI scope's ``env`` binding."""

    async def list_products(self, request: Request) -> list[dict[str, Any]]:
        result = await self._database(request).prepare(
            """
            SELECT slug, name, description, category, price_cents, inventory
            FROM products
            WHERE active = 1
            ORDER BY display_order ASC
            """
        ).all()
        payload = _to_python(result)
        return [dict(product) for product in payload.get("results", [])]

    async def create_order(
        self, request: Request, *, email: str, items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        database = self._database(request)
        lines: list[dict[str, Any]] = []

        for item in items:
            result = await database.prepare(
                """
                SELECT slug, name, price_cents, inventory
                FROM products
                WHERE slug = ? AND active = 1
                """
            ).bind(item["slug"]).first()
            product = _to_python(result)
            if not product:
                raise StoreInputError(f"Product '{item['slug']}' is unavailable.")
            if product["inventory"] < item["quantity"]:
                raise StoreInputError(f"Not enough '{product['name']}' items are available.")
            lines.append({**dict(product), "quantity": item["quantity"]})

        order_id = f"ss_{uuid4().hex[:12]}"
        subtotal_cents = sum(line["price_cents"] * line["quantity"] for line in lines)
        statements = [
            database.prepare(
                """
                INSERT INTO orders (id, email, subtotal_cents, currency, status)
                VALUES (?, ?, ?, 'USD', 'received')
                """
            ).bind(order_id, email, subtotal_cents)
        ]
        statements.extend(
            database.prepare(
                """
                INSERT INTO order_items (order_id, product_slug, product_name, unit_price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
                """
            ).bind(order_id, line["slug"], line["name"], line["price_cents"], line["quantity"])
            for line in lines
        )
        await database.batch(statements)
        return {
            "id": order_id,
            "email": email,
            "status": "received",
            "currency": "USD",
            "subtotal_cents": subtotal_cents,
            "items": [
                {
                    "slug": line["slug"],
                    "name": line["name"],
                    "unit_price_cents": line["price_cents"],
                    "quantity": line["quantity"],
                }
                for line in lines
            ],
        }

    @staticmethod
    def _database(request: Request) -> Any:
        environment = request.scope.get("env")
        if environment is None:
            raise RuntimeError("Cloudflare D1 is unavailable outside the Workers runtime.")
        return environment.STORE_DB


class MemoryStoreRepository:
    """In-memory implementation used by the API tests and local examples."""

    def __init__(self, products: Sequence[Mapping[str, Any]] | None = None) -> None:
        self.products = [dict(product) for product in (products or DEFAULT_PRODUCTS)]
        self.orders: list[dict[str, Any]] = []

    async def list_products(self, request: Request) -> list[dict[str, Any]]:
        return [dict(product) for product in self.products if product["active"]]

    async def create_order(
        self, request: Request, *, email: str, items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        products = {product["slug"]: product for product in self.products if product["active"]}
        lines: list[dict[str, Any]] = []
        for item in items:
            product = products.get(item["slug"])
            if product is None:
                raise StoreInputError(f"Product '{item['slug']}' is unavailable.")
            if product["inventory"] < item["quantity"]:
                raise StoreInputError(f"Not enough '{product['name']}' items are available.")
            lines.append({**product, "quantity": item["quantity"]})

        order = {
            "id": f"ss_{uuid4().hex[:12]}",
            "email": email,
            "status": "received",
            "currency": "USD",
            "subtotal_cents": sum(line["price_cents"] * line["quantity"] for line in lines),
            "items": [
                {
                    "slug": line["slug"],
                    "name": line["name"],
                    "unit_price_cents": line["price_cents"],
                    "quantity": line["quantity"],
                }
                for line in lines
            ],
        }
        self.orders.append(order)
        return order


DEFAULT_PRODUCTS = (
    {
        "slug": "day-bottle",
        "name": "Day Bottle",
        "description": "Olive insulated bottle · 500 ml",
        "category": "carry",
        "price_cents": 3400,
        "inventory": 24,
        "active": True,
    },
    {
        "slug": "market-tote",
        "name": "Market Tote",
        "description": "Natural canvas · everyday carry",
        "category": "carry",
        "price_cents": 2600,
        "inventory": 18,
        "active": True,
    },
    {
        "slug": "after-rain",
        "name": "After Rain",
        "description": "Cedar candle · 40 hours",
        "category": "home",
        "price_cents": 2800,
        "inventory": 16,
        "active": True,
    },
)


def create_app(repository: StoreRepository | None = None) -> Pyrora:
    """Build the store API with a replaceable persistence implementation."""
    app = Pyrora(debug=False)
    app.starlette.state.store_repository = repository or D1StoreRepository()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://pyrora.pages.dev"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=86_400,
    )

    @app.get("/health", name="store.health")
    async def health(request: Request):
        return json({"ok": True, "service": "pyrora-store-api"})

    @app.get("/api/products", name="store.products")
    async def products(request: Request):
        repository = request.app.state.store_repository
        return json({"products": await repository.list_products(request)})

    @app.post("/api/orders", name="store.orders.create")
    async def create_order(request: Request):
        try:
            email, items = _parse_order(await request.json())
            repository = request.app.state.store_repository
            order = await repository.create_order(request, email=email, items=items)
        except StoreInputError as error:
            return json({"detail": str(error)}, status_code=422)
        return json({"order": order}, status_code=201)

    return app


def _parse_order(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(payload, Mapping):
        raise StoreInputError("Request body must be a JSON object.")

    email = payload.get("email")
    if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email.strip()):
        raise StoreInputError("Enter a valid email address.")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise StoreInputError("Add at least one item before submitting an order.")
    if len(raw_items) > 20:
        raise StoreInputError("An order can contain at most 20 distinct items.")

    quantities: dict[str, int] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            raise StoreInputError("Every order item must include a product and quantity.")
        slug = raw_item.get("slug")
        quantity = raw_item.get("quantity")
        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            raise StoreInputError("One of the selected products is invalid.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 10:
            raise StoreInputError("Item quantities must be whole numbers from 1 to 10.")
        quantities[slug] = quantities.get(slug, 0) + quantity
        if quantities[slug] > 10:
            raise StoreInputError("Item quantities must be whole numbers from 1 to 10.")

    return email.strip().lower(), [
        {"slug": slug, "quantity": quantity} for slug, quantity in quantities.items()
    ]


def _to_python(value: Any) -> Any:
    """Convert a Workers JavaScript proxy into JSON-safe Python when needed."""
    converter = getattr(value, "to_py", None)
    if callable(converter):
        value = converter()
    if isinstance(value, Mapping):
        return {key: _to_python(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_python(item) for item in value]
    return value


app = create_app()
