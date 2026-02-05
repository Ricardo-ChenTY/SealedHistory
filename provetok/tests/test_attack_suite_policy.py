"""Tests for the exported attack suite README policy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.attack_suite import export_attack_suite
from provetok.dataset.paths import DatasetPaths


def test_exported_attack_suite_readme_mentions_repo_scripts(tmp_path: Path) -> None:
    paths = DatasetPaths(export_root=tmp_path, dataset_version="test-attack-suite")
    paths.ensure_dirs()

    export_attack_suite(paths)

    readme = paths.public_dir / "attack_suite" / "README.md"
    assert readme.exists()
    text = readme.read_text(encoding="utf-8")

    assert "documentation only" in text.lower()
    assert "python -m provetok.cli dataset build" in text
    assert "python provetok/scripts/run_audit_v2.py" in text

