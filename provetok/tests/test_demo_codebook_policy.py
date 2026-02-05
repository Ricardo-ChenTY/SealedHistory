"""Tests for demo codebook documentation and export isolation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset


def test_demo_codebooks_are_documented(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    top_readme = (repo_root / "README.md").read_text(encoding="utf-8").lower()
    assert "demo codebooks" in top_readme
    assert "synthetic" in top_readme

    sealed_readme = (repo_root / "provetok" / "data" / "sealed" / "README.md").read_text(encoding="utf-8").lower()
    assert "synthetic" in sealed_readme
    assert "demo" in sealed_readme

    out_root = tmp_path / "exports"
    build_dataset(
        config_path=repo_root / "provetok" / "configs" / "dataset_legacy.yaml",
        offline=True,
        out_root=out_root,
        track="A",
    )

    export_root = out_root / "0.2.0-legacy"
    assert export_root.exists()
    demo_like = list(export_root.rglob("*.sealed.codebook.json"))
    assert not demo_like

