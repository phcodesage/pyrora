"""Run the Pyrora command line via ``python -m pyrora``."""

from .commands import main

if __name__ == "__main__":
    raise SystemExit(main())
