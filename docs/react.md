# Optional React/Vite preset

Run `pyrora new realtime-app --react`. The generator creates a Pyrora backend
and a responsive TypeScript React/Vite frontend with API, WebSocket, and native
WebRTC helpers. Run `pyrora frontend install`, then `pyrora frontend dev`.

Vite proxies `/api`, `/ws`, and `/signaling` to the backend during development;
the generated backend permits the Vite origin with CORS. `pyrora frontend build`
produces `frontend/dist`, and the generated `Pyrora(frontend_dist=...,
spa_fallback=True)` serves it same-origin in production.
