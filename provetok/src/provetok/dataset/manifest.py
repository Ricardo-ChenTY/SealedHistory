"""Manifest helpers for reproducible dataset exports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file():
            files.append(p)
    return sorted(files)


def compute_public_artifacts(public_dir: Path) -> List[Dict[str, object]]:
    """Return stable list of public artifacts with hashes."""
    artifacts: List[Dict[str, object]] = []
    for p in list_files(public_dir):
        rel = p.relative_to(public_dir)
        # dataset_manifest.json contains the artifact list; avoid recursion issues.
        if rel.as_posix() == "dataset_manifest.json":
            continue
        artifacts.append(
            {
                "path": rel.as_posix(),
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
        )
    return artifacts

