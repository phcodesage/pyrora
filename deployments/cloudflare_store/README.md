# Pyrora store API on Cloudflare

This deployment uses a real Pyrora ASGI application, the Cloudflare Python
Workers beta adapter, and D1 for the catalog and submitted orders. The Pages
storefront calls this API from `https://pyrora.pages.dev`.

## Deploy

Python Workers currently require Python 3.13 or later and the `python_workers`
compatibility flag. Create the D1 database, copy the returned UUID into
`wrangler.store.json`, then apply the schema and deploy:

```bash
cd deployments/cloudflare_store
npx wrangler d1 create pyrora-store
npx wrangler d1 execute pyrora-store --remote \
  --file=migrations/0001_store.sql
uvx --from workers-py --with workers-runtime-sdk pywrangler sync
python build_bundle.py
npx wrangler deploy
```

`pywrangler sync` builds the pure-Python dependency bundle. `build_bundle.py`
then copies the local `src/pyrora` package into that generated bundle; it does
not duplicate framework source in version control. It also removes the
tool-generated local virtual environment before deployment.

The API exposes `GET /health`, `GET /api/products`, and `POST /api/orders`.
It validates the catalog and prices on the server before recording an order.

## Commerce boundary

This sample records an order request; it does not collect a payment, fulfil an
order, calculate tax, or reserve stock. A production store needs a separate,
configured payment and fulfilment integration (for example, Stripe plus an
order-management service). Do not describe an order returned by this API as
paid unless that payment integration has confirmed it.
