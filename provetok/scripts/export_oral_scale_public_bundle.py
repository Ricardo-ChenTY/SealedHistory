"""Export a public-safe bundle from an already-built oral scale dataset dir.

Why this exists
---------------
`provetok/scripts/build_oral_scale_dataset.py` materializes a scale dataset from
internal exports and writes private codebooks next to the JSONLs. For public
reproducibility we need a directory that:
  - contains only publishable JSONLs (raw + sealed variants),
  - contains a manifest with hashes/record-counts,
  - contains **no** `*.codebook.json`,
  - does not leak internal input paths in its manifest.

This script is intentionally simple and deterministic. It does not catch errors
(`try/except/finally` is forbidden under `provetok/`); failures should surface as
exceptions and be handled by rerunning with corrected inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _count_jsonl_records(path: Path) -> int:
    n = 0
    with open(path, "rb") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _default_include_files(dataset_dir: Path) -> List[str]:
    # Prefer a stable, explicit set (raw + sealed variants). If some variants are
    # absent, we simply skip them.
    names = [
        "track_A_raw.jsonl",
        "track_B_raw.jsonl",
        "track_A_sealed.jsonl",
        "track_B_sealed.jsonl",
        "track_A_sealed_l1only.jsonl",
        "track_B_sealed_l1only.jsonl",
        "track_A_sealed_redact.jsonl",
        "track_B_sealed_redact.jsonl",
        "track_A_sealed_summary.jsonl",
        "track_B_sealed_summary.jsonl",
    ]
    return [n for n in names if (dataset_dir / n).exists()]


def export_bundle(*, dataset_dir: Path, out_dir: Path, include: List[str], overwrite: bool) -> Dict:
    t0 = time.time()

    if out_dir.exists():
        if not overwrite:
            raise ValueError(f"out_dir already exists: {out_dir} (pass --overwrite to replace)")
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy selected JSONLs only.
    copied: List[Path] = []
    for name in include:
        src = dataset_dir / name
        if not src.exists():
            raise FileNotFoundError(src)
        if src.name.endswith(".codebook.json"):
            raise ValueError(f"Refusing to copy private codebook into public bundle: {src.name}")
        dst = out_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)

    # Hard forbid any codebook-like filename in out_dir.
    forbidden = sorted(str(p) for p in out_dir.rglob("*.codebook.json"))
    if forbidden:
        raise ValueError(f"Public bundle contains forbidden files: {forbidden[:5]}")

    files = []
    for p in copied:
        files.append(
            {
                "path": p.name,
                "bytes": p.stat().st_size,
                "sha256": _sha256_file(p),
                "n_records": _count_jsonl_records(p) if p.suffix == ".jsonl" else None,
            }
        )

    # Record provenance WITHOUT leaking internal file paths.
    src_manifest = dataset_dir / "dataset_manifest.json"
    src_manifest_sha256 = _sha256_file(src_manifest) if src_manifest.exists() else ""

    script_path = Path(__file__).resolve()
    script_sha256 = _sha256_file(script_path)

    elapsed = time.time() - t0
    manifest = {
        "bundle_name": "oral_scale_public_bundle_v0",
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "source_manifest_sha256": src_manifest_sha256,
            "note": "Internal input paths intentionally omitted from public bundle manifest.",
        },
        "runtime": {
            "elapsed_sec": round(float(elapsed), 3),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": {
            "commit": _git_head(),
            "dirty": bool(_git_dirty()),
        },
        "provenance": {
            "script": str(script_path.name),
            "script_sha256": script_sha256,
        },
        "policy": {
            "forbidden_globs": ["*.codebook.json"],
            "public_only": True,
        },
        "files": files,
    }

    (out_dir / "public_dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Small README for the bundle (useful when shipped as a tarball).
    readme = (
        "# Oral vNext Scale Public Bundle\n\n"
        "This directory contains a public-safe dataset bundle for reproducing the **scale** experiments.\n\n"
        "Contents:\n"
        "- raw records (public)\n"
        "- sealed records (public)\n"
        "- stronger baselines (public): `sealed_redact`, `sealed_summary`\n\n"
        "Policy:\n"
        "- This bundle **must not** contain any `*.codebook.json`.\n"
        "- White-box results that require private codebooks cannot be reproduced from this bundle alone.\n\n"
        "Manifest:\n"
        f"- `public_dataset_manifest.json` (generated by `{script_path.name}`)\n"
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Export a public-safe oral scale bundle (no codebooks, no internal paths).")
    p.add_argument("--dataset_dir", required=True, help="Input dataset dir (e.g. runs/EXP-021/dataset)")
    p.add_argument("--out_dir", required=True, help="Output bundle dir (e.g. runs/EXP-031/public)")
    p.add_argument(
        "--include",
        nargs="*",
        default=None,
        help="Explicit file basenames to include; default copies raw+sealed variants if present.",
    )
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.out_dir)
    include = list(args.include) if args.include else _default_include_files(dataset_dir)
    if not include:
        raise ValueError("No files selected for export (dataset_dir appears incomplete)")

    manifest = export_bundle(dataset_dir=dataset_dir, out_dir=out_dir, include=include, overwrite=bool(args.overwrite))
    # Print minimal confirmation (avoid leaking paths).
    print(json.dumps({"out_dir": str(out_dir), "n_files": len(manifest.get("files") or [])}, indent=2))


if __name__ == "__main__":
    main()

