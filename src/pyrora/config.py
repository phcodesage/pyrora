"""Configuration loading with explicit, predictable precedence."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")
_MISSING = object()


class ConfigurationError(RuntimeError):
    """Raised when required configuration is absent or invalid."""


class Config:
    """Merge defaults, a dotenv file, and environment variables.

    Precedence is ``defaults < .env < environment``. Values remain strings
    until callers request a cast, preserving the behaviour of OS environments.
    """

    def __init__(
        self,
        defaults: Mapping[str, Any] | None = None,
        *,
        env_file: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._values: dict[str, Any] = dict(defaults or {})
        self._defaults: dict[str, Any] = dict(defaults or {})
        self._env_file = Path(env_file) if env_file else Path.cwd() / ".env"
        self._dotenv = self._load_dotenv(self._env_file)
        self._values.update(self._dotenv)
        self._environ = dict(os.environ if environ is None else environ)
        self._values.update(self._environ)

    def get(self, key: str, default: T | None = None, *, cast: type[T] | None = None) -> Any | T:
        """Get a value, optionally casting it to ``bool``, ``int``, or another type."""
        value = self._values.get(key, default)
        if value is None or cast is None:
            return value
        return self._cast(value, cast)

    def require(self, key: str, *, cast: type[T] | None = None) -> Any | T:
        """Get a non-empty value or raise :class:`ConfigurationError`."""
        value = self._values.get(key, _MISSING)
        if value is _MISSING or value is None or value == "":
            raise ConfigurationError(f"Required configuration value {key!r} is not set.")
        return self._cast(value, cast) if cast else value

    def setdefault(self, key: str, value: Any) -> None:
        """Add a default without overriding dotenv or environment values."""
        self._defaults.setdefault(key, value)
        self._values.setdefault(key, value)

    def add_defaults(self, defaults: Mapping[str, Any]) -> None:
        """Add multiple defaults, primarily for plugins."""
        for key, value in defaults.items():
            self.setdefault(key, value)

    def namespace(self, name: str) -> "ConfigNamespace":
        """Return a namespaced view using ``PLUGIN_KEY`` environment names."""
        return ConfigNamespace(self, name)

    plugin = namespace

    def as_dict(self) -> dict[str, Any]:
        """Return a copy for diagnostics; secrets should not be logged."""
        return dict(self._values)

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise AttributeError(f"Configuration value {key!r} is not set.")
        return value

    @staticmethod
    def _load_dotenv(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        values: dict[str, str] = {}
        for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                raise ConfigurationError(f"Invalid dotenv line {number} in {path}: expected KEY=VALUE.")
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise ConfigurationError(f"Invalid dotenv line {number} in {path}: empty key.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key] = value
        return values

    @staticmethod
    def _cast(value: Any, cast: type[T]) -> T:
        if cast is bool:
            if isinstance(value, bool):
                return value  # type: ignore[return-value]
            normalized = str(value).strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True  # type: ignore[return-value]
            if normalized in {"0", "false", "no", "off"}:
                return False  # type: ignore[return-value]
            raise ConfigurationError(f"Cannot cast {value!r} to bool.")
        try:
            return cast(value)
        except (TypeError, ValueError) as exc:
            cast_name = getattr(cast, "__name__", str(cast))
            raise ConfigurationError(f"Cannot cast {value!r} to {cast_name}.") from exc


class ConfigNamespace:
    """A plugin-facing configuration view."""

    def __init__(self, config: Config, name: str) -> None:
        self._config = config
        self._prefix = name.upper().replace("-", "_") + "_"

    def get(self, key: str, default: T | None = None, *, cast: type[T] | None = None) -> Any | T:
        return self._config.get(self._prefix + key.upper(), default, cast=cast)

    def require(self, key: str, *, cast: type[T] | None = None) -> Any | T:
        return self._config.require(self._prefix + key.upper(), cast=cast)

    def setdefault(self, key: str, value: Any) -> None:
        self._config.setdefault(self._prefix + key.upper(), value)
