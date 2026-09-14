"""The Pyrora ASGI application."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable, Iterable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket, WebSocketDisconnect

from .config import Config
from .container import Container
from .controllers import Controller
from .http import Templates, html, text
from .middleware import RequestIDMiddleware, SecurityHeadersMiddleware, TimingMiddleware
from .plugins.manager import PluginManager
from .realtime.channels import ConnectionManager
from .routing import RouteDefinition, Router


@dataclass(frozen=True)
class RouteMetadata:
    """Framework metadata for diagnostics and the ``pyrora routes`` command."""

    path: str
    methods: tuple[str, ...]
    name: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    endpoint: Callable[..., Any] | None = None


class Pyrora:
    """A modular Starlette-based ASGI application.

    Routes, services, templates, plugins, and realtime connections are scoped
    to this instance. It is directly usable by Uvicorn and Starlette TestClient.
    """

    def __init__(
        self,
        *,
        debug: bool = False,
        root_path: str | Path | None = None,
        templates_dir: str | Path | None = None,
        static_dir: str | Path | None = None,
        config: Config | None = None,
        frontend_dist: str | Path | None = None,
        spa_fallback: bool = False,
    ) -> None:
        self.debug = debug
        self.root_path = Path(root_path or Path.cwd()).resolve()
        self.config = config or Config(defaults={"APP_DEBUG": debug}, env_file=self.root_path / ".env")
        self.container = Container()
        self.templates = Templates([templates_dir or self.root_path / "templates"])
        self.connections = ConnectionManager()
        self.realtime = self.connections
        self._route_metadata: list[RouteMetadata] = []
        self._websocket_metadata: list[RouteMetadata] = []
        self._startup_hooks: list[Callable[["Pyrora"], Any]] = []
        self._shutdown_hooks: list[Callable[["Pyrora"], Any]] = []
        self._event_listeners: dict[str, list[Callable[..., Any]]] = {}
        self._health_checks: dict[str, Callable[[], Any]] = {}
        self.commands: dict[str, Callable[..., Any]] = {}
        self._frontend_dist = Path(frontend_dist).resolve() if frontend_dist else None
        self._spa_fallback = spa_fallback
        self._frontend_route: Route | None = None
        self._starlette = Starlette(debug=debug, lifespan=self._lifespan)
        self._starlette.state.pyrora = self
        self.plugins = PluginManager(self)
        self.add_middleware(SecurityHeadersMiddleware)
        self.add_middleware(TimingMiddleware)
        self.add_middleware(RequestIDMiddleware)
        discovered_static = Path(static_dir) if static_dir else self.root_path / "static"
        if static_dir is not None or discovered_static.is_dir():
            self.mount_static("/static", discovered_static, name="static")
        if self._frontend_dist:
            self._install_frontend_fallback()

    @property
    def starlette(self) -> Starlette:
        """The underlying Starlette application for advanced integrations."""
        return self._starlette

    @property
    def routes(self) -> list[Any]:
        """Underlying Starlette routes, mounts, and websocket routes."""
        return self._starlette.router.routes

    @property
    def route_metadata(self) -> tuple[RouteMetadata, ...]:
        """Pyrora route definitions including names and arbitrary metadata."""
        return tuple(self._route_metadata)

    @property
    def websocket_metadata(self) -> tuple[RouteMetadata, ...]:
        return tuple(self._websocket_metadata)

    def route(
        self,
        path: str,
        *,
        methods: Iterable[str] | None = None,
        name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorate a synchronous or asynchronous HTTP endpoint."""
        route_methods = tuple(method.upper() for method in (methods or ("GET",)))
        if not route_methods:
            raise ValueError("A route must declare at least one HTTP method.")

        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            self.add_route(path, handler, methods=route_methods, name=name, metadata=metadata)
            return handler

        return decorator

    def add_route(
        self,
        path: str,
        handler: Callable[..., Any],
        *,
        methods: Iterable[str] | None = None,
        name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Register an HTTP endpoint directly, useful to plugins."""
        route_methods = tuple(method.upper() for method in (methods or ("GET",)))
        if not path.startswith("/"):
            raise ValueError(f"Route paths must start with '/'; got {path!r}.")

        async def endpoint(request: Request) -> Response:
            result = await self._invoke(handler, request)
            return self._to_response(result)

        self._append_route(Route(path, endpoint=endpoint, methods=list(route_methods), name=name))
        self._route_metadata.append(RouteMetadata(path, route_methods, name, dict(metadata or {}), handler))

    def _method(self, method: str, path: str, **kwargs: Any):
        return self.route(path, methods=(method,), **kwargs)

    def get(self, path: str, **kwargs: Any):
        return self._method("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self._method("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any):
        return self._method("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any):
        return self._method("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any):
        return self._method("DELETE", path, **kwargs)

    def include_router(self, router: Router, *, prefix: str = "") -> None:
        """Attach all routes from a :class:`Router` under an optional prefix."""
        if not isinstance(router, Router):
            raise TypeError("include_router() expects pyrora.Router.")
        route_prefix = _join_paths(prefix, router.prefix)
        for definition in router.definitions:
            self.add_route(
                _join_paths(route_prefix, definition.path),
                definition.endpoint,
                methods=definition.methods,
                name=definition.name,
                metadata=definition.metadata,
            )

    def controller(
        self,
        path: str,
        controller: type[Controller],
        *,
        name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Register class methods as a single method-aware controller route."""
        if not inspect.isclass(controller) or not issubclass(controller, Controller):
            raise TypeError("controller() expects a Controller subclass.")
        methods = controller.methods()
        if not methods:
            raise ValueError(f"Controller {controller.__name__} implements no HTTP methods.")

        async def dispatch(request: Request) -> Response:
            instance = controller()
            instance._bind(self, request)
            action = getattr(instance, request.method.lower())
            result = await self._invoke(action, request, pass_request_if_accepted=True)
            return self._to_response(result)

        self._append_route(Route(path, endpoint=dispatch, methods=list(methods), name=name))
        self._route_metadata.append(RouteMetadata(path, methods, name, dict(metadata or {}), controller))

    def websocket(
        self, path: str, *, name: str | None = None, metadata: Mapping[str, Any] | None = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorate a WebSocket handler with automatic room cleanup."""

        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            async def endpoint(socket: WebSocket) -> None:
                try:
                    result = handler(socket)
                    if inspect.isawaitable(result):
                        await result
                except WebSocketDisconnect:
                    pass
                finally:
                    self.connections.leave_all(socket)

            self._append_route(WebSocketRoute(path, endpoint=endpoint, name=name))
            self._websocket_metadata.append(RouteMetadata(path, ("WEBSOCKET",), name, dict(metadata or {}), handler))
            return handler

        return decorator

    def add_middleware(self, middleware_class: type[Any], **options: Any) -> None:
        """Add Starlette-compatible middleware; plugins use this same method."""
        self._starlette.add_middleware(middleware_class, **options)

    def add_template_directory(self, directory: str | Path) -> None:
        """Make plugin templates available to :func:`pyrora.render`."""
        self.templates.add_directory(directory)

    def mount_static(
        self,
        prefix: str,
        directory: str | Path,
        *,
        name: str | None = None,
        check_dir: bool = True,
    ) -> None:
        """Mount a static directory, normally called by application plugins."""
        if not prefix.startswith("/"):
            raise ValueError("Static mount prefixes must start with '/'.")
        path = Path(directory)
        if check_dir and not path.is_dir():
            raise FileNotFoundError(f"Static directory does not exist: {path}")
        self._append_route(Mount(prefix, app=StaticFiles(directory=path, check_dir=check_dir), name=name))

    def install(self, plugin: Any) -> Any:
        """Explicitly install a plugin instance or Plugin subclass."""
        return self.plugins.install(plugin)

    def on_startup(self, callback: Callable[["Pyrora"], Any]) -> Callable[["Pyrora"], Any]:
        self._startup_hooks.append(callback)
        return callback

    def on_shutdown(self, callback: Callable[["Pyrora"], Any]) -> Callable[["Pyrora"], Any]:
        self._shutdown_hooks.append(callback)
        return callback

    def on(self, event: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an application event listener for plugins and app code."""
        def decorator(callback: Callable[..., Any]) -> Callable[..., Any]:
            self._event_listeners.setdefault(event, []).append(callback)
            return callback
        return decorator

    async def dispatch_event(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Run event listeners in registration order and return their results."""
        results = []
        for callback in self._event_listeners.get(event, ()):
            result = callback(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            results.append(result)
        return results

    def add_command(self, name: str, command: Callable[..., Any]) -> None:
        """Register an application-specific CLI command, typically from a plugin."""
        if not name or name in self.commands:
            raise ValueError(f"Command {name!r} is invalid or already registered.")
        self.commands[name] = command

    def add_health_check(self, name: str, check: Callable[[], Any]) -> None:
        """Register a named lightweight health check."""
        if not name or name in self._health_checks:
            raise ValueError(f"Health check {name!r} is invalid or already registered.")
        self._health_checks[name] = check

    async def health(self) -> dict[str, Any]:
        """Run registered health checks, reporting failures without hiding them."""
        results: dict[str, Any] = {}
        for name, check in self._health_checks.items():
            try:
                value = check()
                if inspect.isawaitable(value):
                    value = await value
                results[name] = {"ok": bool(value), "result": value}
            except Exception as exc:
                results[name] = {"ok": False, "error": str(exc)}
        return results

    async def _invoke(
        self, handler: Callable[..., Any], request: Request, *, pass_request_if_accepted: bool = False
    ) -> Any:
        arguments: tuple[Any, ...] = (request,)
        if pass_request_if_accepted and not _accepts_positional_argument(handler):
            arguments = ()
        if inspect.iscoroutinefunction(handler):
            return await handler(*arguments)
        result = await run_in_threadpool(handler, *arguments)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _to_response(result: Any) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, (Mapping, list, tuple)):
            return JSONResponse(result)
        if isinstance(result, str):
            return html(result)
        if result is None:
            raise RuntimeError("Pyrora endpoint returned None; return a response, mapping, list, or string.")
        return text(str(result))

    @asynccontextmanager
    async def _lifespan(self, _: Starlette) -> AsyncIterator[None]:
        await self.plugins.boot()
        for callback in self._startup_hooks:
            result = callback(self)
            if inspect.isawaitable(result):
                await result
        await self.dispatch_event("startup", self)
        try:
            yield
        finally:
            await self.dispatch_event("shutdown", self)
            for callback in reversed(self._shutdown_hooks):
                result = callback(self)
                if inspect.isawaitable(result):
                    await result

    def _append_route(self, route: Any) -> None:
        if self._frontend_route is not None:
            self._starlette.router.routes.remove(self._frontend_route)
        self._starlette.router.routes.append(route)
        if self._frontend_route is not None:
            self._starlette.router.routes.append(self._frontend_route)

    def _install_frontend_fallback(self) -> None:
        async def frontend(request: Request) -> Response:
            assert self._frontend_dist is not None
            requested = request.path_params.get("path", "")
            candidate = (self._frontend_dist / requested).resolve()
            try:
                candidate.relative_to(self._frontend_dist)
            except ValueError:
                return text("Not Found", status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)
            index = self._frontend_dist / "index.html"
            if self._spa_fallback and index.is_file():
                return FileResponse(index)
            return text("Not Found", status_code=404)

        self._frontend_route = Route("/{path:path}", endpoint=frontend, methods=["GET", "HEAD"], name="frontend")
        self._starlette.router.routes.append(self._frontend_route)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self._starlette(scope, receive, send)


def _accepts_positional_argument(callback: Callable[..., Any]) -> bool:
    try:
        parameters = inspect.signature(callback).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD, parameter.VAR_POSITIONAL)
        for parameter in parameters
    )


def _join_paths(*parts: str) -> str:
    cleaned = [part.strip("/") for part in parts if part and part.strip("/")]
    return "/" + "/".join(cleaned)
