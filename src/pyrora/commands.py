"""The installable ``pyrora`` command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from .app import Pyrora
from .scaffold import create_project


def main(argv: list[str] | None = None) -> int:
    """Run the Pyrora CLI and return a conventional process exit status."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "new":
            create_project(Path.cwd() / args.name, react=args.react)
            print(f"Created Pyrora project at {args.name}")
            return 0
        if args.command == "serve":
            return _serve(args)
        if args.command == "routes":
            app = _load_app(args.app)
            for route in app.route_metadata:
                methods = ",".join(route.methods)
                print(f"{methods:20} {route.path:32} {route.name or '-'}")
            for route in app.websocket_metadata:
                print(f"WEBSOCKET            {route.path:32} {route.name or '-'}")
            return 0
        if args.command == "plugins":
            app = _load_app(args.app)
            if args.plugins_command == "list":
                installed = app.plugins.installed
                if not installed:
                    print("No plugins installed.")
                for plugin in installed:
                    print(f"{plugin.name}\t{plugin.version}")
                return 0
            discovered = app.plugins.discover()
            if not discovered:
                print("No discoverable plugins found.")
            for name, target in discovered.items():
                print(f"{name}\t{target}")
            return 0
        if args.command == "frontend":
            return _frontend(args.frontend_command)
        if args.command == "make:controller":
            _make_controller(args.name)
            return 0
        if args.command == "make:view":
            _make_view(args.name)
            return 0
    except (OSError, RuntimeError, ValueError, ModuleNotFoundError) as exc:
        print(f"pyrora: {exc}", file=sys.stderr)
        return 1
    parser.print_help()
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyrora", description="Pyrora application tooling")
    subcommands = parser.add_subparsers(dest="command", required=True)
    new = subcommands.add_parser("new", help="create a project")
    new.add_argument("name")
    new.add_argument("--react", action="store_true", help="include the optional React/Vite starter")
    serve = subcommands.add_parser("serve", help="serve an ASGI application with Uvicorn")
    serve.add_argument("--app", default=os.getenv("PYRORA_APP", "app:app"))
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    routes = subcommands.add_parser("routes", help="list application routes")
    routes.add_argument("--app", default=os.getenv("PYRORA_APP", "app:app"))
    plugins = subcommands.add_parser("plugins", help="inspect plugins")
    plugins.add_argument("--app", default=os.getenv("PYRORA_APP", "app:app"))
    plugin_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugin_sub.add_parser("list", help="list manually installed plugins")
    plugin_sub.add_parser("discover", help="list entry points without importing them")
    frontend = subcommands.add_parser("frontend", help="run frontend package scripts")
    frontend_sub = frontend.add_subparsers(dest="frontend_command", required=True)
    frontend_sub.add_parser("install")
    frontend_sub.add_parser("dev")
    frontend_sub.add_parser("build")
    controller = subcommands.add_parser("make:controller", help="create a controller")
    controller.add_argument("name")
    view = subcommands.add_parser("make:view", help="create a Jinja view")
    view.add_argument("name")
    return parser


def _load_app(target: str) -> Pyrora:
    module_name, separator, attribute = target.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("Application target must use module:attribute, e.g. app:app.")
    value: Any = getattr(importlib.import_module(module_name), attribute)
    if not isinstance(value, Pyrora):
        raise RuntimeError(f"{target!r} did not resolve to a Pyrora application.")
    return value


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Serving requires Uvicorn. Install it with: pip install 'pyrora[server]'.") from exc
    uvicorn.run(args.app, host=args.host, port=args.port, reload=args.reload)
    return 0


def _frontend(action: str) -> int:
    executable = shutil.which("npm")
    if executable is None:
        raise RuntimeError("Node.js/npm is required for frontend commands but was not found.")
    frontend = Path.cwd() / "frontend"
    if not (frontend / "package.json").is_file():
        raise RuntimeError("No frontend/package.json found. Run this inside a React Pyrora project.")
    command = [executable, "install"] if action == "install" else [executable, "run", action]
    return subprocess.run(command, cwd=frontend, check=False).returncode


def _make_controller(name: str) -> None:
    class_name = _class_name(name)
    destination = Path.cwd() / "controllers" / f"{_snake_case(class_name)}.py"
    _write_new(
        destination,
        f'''from pyrora import Controller, json


class {class_name}(Controller):
    async def get(self):
        return json({{"controller": "{class_name}"}})
''',
    )
    print(f"Created {destination.relative_to(Path.cwd())}")


def _make_view(name: str) -> None:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("View names must be relative paths without '..'.")
    filename = relative if relative.suffix else relative.with_suffix(".html")
    destination = Path.cwd() / "templates" / filename
    _write_new(destination, f"<h1>{filename.stem.replace('-', ' ').title()}</h1>\n")
    print(f"Created {destination.relative_to(Path.cwd())}")


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _class_name(value: str) -> str:
    name = "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)
    if not name or not name.isidentifier():
        raise ValueError("Controller name must be a valid Python identifier.")
    return name if name.endswith("Controller") else name + "Controller"


def _snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
