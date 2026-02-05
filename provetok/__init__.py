"""Repo checkout shim for the src-layout `provetok` package.

This repository uses a src layout (`provetok/src/provetok`). When running from
the repo root without installing the package (e.g. `python -m provetok.cli`),
Python will otherwise resolve `provetok` to this top-level directory and fail
to find submodules.

We extend this package's `__path__` to include the real implementation package
directory so module execution works from a fresh checkout.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

_IMPL_ROOT = Path(__file__).resolve().parent / "src" / "provetok"
if _IMPL_ROOT.is_dir():
    __path__.append(str(_IMPL_ROOT))

