from __future__ import annotations

import sys
from pathlib import Path

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1] / "deployments" / "cloudflare_store"))

from store_api import MemoryStoreRepository, create_app  # noqa: E402


def make_client() -> tuple[TestClient, MemoryStoreRepository]:
    repository = MemoryStoreRepository()
    return TestClient(create_app(repository)), repository


def test_store_catalog_and_health_are_available() -> None:
    client, _ = make_client()

    assert client.get("/health").json() == {"ok": True, "service": "pyrora-store-api"}
    products = client.get("/api/products").json()["products"]
    assert [product["slug"] for product in products] == [
        "day-bottle",
        "market-tote",
        "after-rain",
    ]


def test_store_records_an_order_with_server_side_prices() -> None:
    client, repository = make_client()

    response = client.post(
        "/api/orders",
        json={
            "email": "hello@example.com",
            "items": [
                {"slug": "day-bottle", "quantity": 2, "price_cents": 1},
                {"slug": "after-rain", "quantity": 1},
            ],
        },
        headers={"Origin": "https://pyrora.pages.dev"},
    )

    assert response.status_code == 201
    order = response.json()["order"]
    assert order["subtotal_cents"] == 9600
    assert order["status"] == "received"
    assert response.headers["access-control-allow-origin"] == "https://pyrora.pages.dev"
    assert repository.orders == [order]


def test_store_rejects_invalid_order_input() -> None:
    client, _ = make_client()

    response = client.post("/api/orders", json={"email": "not-an-email", "items": []})

    assert response.status_code == 422
    assert response.json()["detail"] == "Enter a valid email address."
