"""Copy the local Pyrora source into Python Workers' generated package bundle."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / "src" / "pyrora"
TARGET = ROOT / "python_modules" / "pyrora"
GENERATED_ENVIRONMENT = ROOT / ".venv-workers"

if not SOURCE.is_dir():
    raise SystemExit(f"Pyrora source was not found at {SOURCE}.")
if not (ROOT / "python_modules").is_dir():
    raise SystemExit("Run pywrangler sync before building the Worker bundle.")
if TARGET.exists():
    shutil.rmtree(TARGET)

shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
if GENERATED_ENVIRONMENT.exists():
    shutil.rmtree(GENERATED_ENVIRONMENT)
print(f"Bundled local Pyrora source at {TARGET}")
