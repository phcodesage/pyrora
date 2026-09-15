# Contributing to Pyrora

Thank you for improving Pyrora. This is alpha software, so small, well-tested
contributions and clear API feedback are especially valuable.

## Before you begin

- Search existing issues and pull requests before opening a duplicate.
- Open an issue first for a new public API, a behavior change, or work that
  spans several modules. This keeps the core small and avoids parallel work.
- Keep database, auth, queues, mail, billing, admin, Redis, Socket.IO, and
  other heavyweight integrations in separate plugin packages unless there is a
  compelling core contract to discuss.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues
  through the process in [SECURITY.md](SECURITY.md), not a public issue.

## Development setup

Pyrora supports Python 3.10 and newer. Create an isolated environment outside
of version control, install the development extras, and run the checks:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,server]"
python -m compileall -q src tests
pytest
ruff check src tests
python -m build
```

The test suite uses pytest and Starlette's TestClient. New user-visible
behavior needs a regression test. When touching generated project templates,
also test the generated output.

## Pull requests

1. Branch from `main` and give the branch a descriptive name.
2. Keep each pull request focused. Separate refactors from behavior changes.
3. Add type hints and docstrings to public interfaces.
4. Update the relevant guide, README section, or changelog when behavior or
   installation changes.
5. Explain the problem, approach, tests run, compatibility impact, and any
   follow-up work in the pull-request template.

Maintainers may request a smaller surface area, a plugin boundary, or a public
API review before merging. Do not merge your own pull request unless you have
been explicitly granted that responsibility.

## Style and compatibility

- Use Python 3.10-compatible syntax in the core.
- Prefer explicit dependencies, errors, and configuration over process-wide
  state or implicit discovery.
- Preserve sync and async handler support.
- Keep Starlette and Jinja2 as the only mandatory runtime dependencies.
- Do not add a dependency solely to support an optional integration; expose a
  small contract or plugin hook instead.

## Release notes

Add a concise entry under `Unreleased` in `CHANGELOG.md` for a user-visible
fix, feature, deprecation, or security change. Releases use semantic versioning:
patch for compatible fixes, minor for compatible features, and major for
breaking public API changes.
