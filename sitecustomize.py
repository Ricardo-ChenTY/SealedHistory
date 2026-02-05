"""Repository-local Python path bootstrap.

This enables running `python -m provetok.cli ...` from a fresh checkout
without requiring an editable install, by adding the src-layout package root
to `sys.path` at interpreter startup.
"""

from __future__ import annotations

import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent
_SRC_ROOT = _REPO_ROOT / "provetok" / "src"

if _SRC_ROOT.is_dir():
    _src = str(_SRC_ROOT)
    if _src not in sys.path:
        sys.path.insert(0, _src)

