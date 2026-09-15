"""Cloudflare's Python Workers adapter for the Pyrora store API."""

from workers import asgi

from store_api import app

Default = asgi.entrypoint(app)
