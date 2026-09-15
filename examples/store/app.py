"""A small Pyrora storefront showing pages, product APIs, and named routes."""

from pathlib import Path

from pyrora import Pyrora, json, render

ROOT = Path(__file__).parent
PRODUCTS = [
    {"slug": "day-bottle", "name": "Day Bottle", "description": "Olive insulated bottle", "price": 34},
    {"slug": "market-tote", "name": "Market Tote", "description": "Natural canvas tote", "price": 26},
    {"slug": "after-rain", "name": "After Rain", "description": "Amber glass candle", "price": 28},
]

app = Pyrora(debug=True, root_path=ROOT)


@app.get("/", name="store.home")
async def home(request):
    return render(request, "store.html", products=PRODUCTS)


@app.get("/api/products", name="store.products")
async def products(request):
    return json({"products": PRODUCTS})


@app.get("/products/{slug}", name="store.product")
async def product(request):
    slug = request.path_params["slug"]
    for item in PRODUCTS:
        if item["slug"] == slug:
            return json(item)
    return json({"detail": "Product not found"}, status_code=404)
