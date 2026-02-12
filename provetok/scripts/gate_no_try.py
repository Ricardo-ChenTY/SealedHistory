"""Gate: ensure repository code contains zero `try/except/finally` blocks.

This is an AST-based gate to avoid false positives from strings/comments.

Usage:
  python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


_SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
}


def _iter_py_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix == ".py":
            yield path
        return

    for p in path.rglob("*.py"):
        # Skip generated/cache folders.
        parts = set(p.parts)
        if parts & _SKIP_DIR_NAMES:
            continue
        if any(part.endswith(".egg-info") for part in p.parts):
            continue
        yield p


def _find_try_nodes(py_path: Path) -> List[Tuple[int, int]]:
    src = py_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(py_path))

    spans: List[Tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            lineno = int(getattr(node, "lineno", 1))
            end_lineno = int(getattr(node, "end_lineno", lineno))
            spans.append((lineno, end_lineno))
    return spans


def main() -> None:
    p = argparse.ArgumentParser(description="AST gate: forbid try/except/finally in repository code.")
    p.add_argument("--paths", nargs="+", required=True, help="Files/dirs to scan (recursively for dirs).")
    p.add_argument(
        "--fail-on-match",
        action="store_true",
        help="Exit non-zero if any try blocks are found.",
    )
    args = p.parse_args()

    paths = [Path(x) for x in args.paths]
    py_files: List[Path] = []
    for root in paths:
        py_files.extend(list(_iter_py_files(root)))

    offenders: List[Tuple[Path, List[Tuple[int, int]]]] = []
    for f in sorted(set(py_files)):
        spans = _find_try_nodes(f)
        if spans:
            offenders.append((f, spans))

    if offenders:
        print("FAIL: found try/except/finally blocks (AST ast.Try nodes).")
        for f, spans in offenders:
            for (lo, hi) in spans:
                if lo == hi:
                    print(f"{f}:{lo}")
                else:
                    print(f"{f}:{lo}-{hi}")
        print(f"\nSummary: {sum(len(s) for _, s in offenders)} try blocks in {len(offenders)} files.")
        if args.fail_on_match:
            sys.exit(1)
    else:
        print(f"PASS: 0 try blocks found across {len(py_files)} python files.")
    sys.exit(0)


if __name__ == "__main__":
    main()

