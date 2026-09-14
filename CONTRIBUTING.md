# Contributing to Pyrora

Pyrora is an alpha project. Keep pull requests focused, typed, documented, and
covered by tests. Run `python -m compileall -q src tests`, `pytest`, and `ruff
check src tests` before opening a pull request.

New integrations belong in separate packages when they add a heavyweight or
optional dependency. Prefer a `Plugin` and small contracts in `pyrora.contracts`
over growing the framework core.
