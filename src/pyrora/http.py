"""HTTP response helpers and template rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response


def json(data: Any, status_code: int = 200) -> JSONResponse:
    """Return a JSON response."""
    return JSONResponse(data, status_code=status_code)


def html(content: str, status_code: int = 200) -> HTMLResponse:
    """Return an HTML response."""
    return HTMLResponse(content, status_code=status_code)


def text(content: str, status_code: int = 200) -> PlainTextResponse:
    """Return a plain-text response."""
    return PlainTextResponse(content, status_code=status_code)


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    """Redirect to ``url``; 303 is intentionally the default for form posts."""
    return RedirectResponse(url, status_code=status_code)


class Templates:
    """Jinja environment with explicit, extensible template search paths."""

    def __init__(self, directories: list[str | Path]) -> None:
        self._directories: list[str] = []
        self.environment = Environment(
            loader=FileSystemLoader(self._directories),
            autoescape=select_autoescape(("html", "htm", "xml", "xhtml"), default_for_string=True),
        )
        for directory in directories:
            self.add_directory(directory)

    @property
    def directories(self) -> tuple[str, ...]:
        return tuple(self._directories)

    def add_directory(self, directory: str | Path) -> None:
        """Add a search directory. It may be created after application setup."""
        normalized = str(Path(directory).resolve())
        if normalized not in self._directories:
            self._directories.append(normalized)
            loader = self.environment.loader
            assert isinstance(loader, FileSystemLoader)
            loader.searchpath[:] = self._directories

    async def render(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template asynchronously for async application code."""
        template = self.environment.get_template(name)
        return template.render(**context)


def render(request: Request, template: str, status_code: int = 200, **context: Any) -> HTMLResponse:
    """Render a Jinja template belonging to the request's Pyrora app.

    The helper stays synchronous for the ergonomic ``return render(request,
    ...)`` API and Jinja autoescaping is enabled by default.
    """
    try:
        pyrora = request.app.state.pyrora
    except AttributeError as exc:
        raise RuntimeError("render() requires a request handled by a Pyrora application.") from exc
    values = {"request": request, **context}
    rendered = pyrora.templates.environment.get_template(template).render(**values)
    return HTMLResponse(rendered, status_code=status_code)


ResponseType = Response
