"""Tests for dataset pipeline (legacy export path)."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset
from provetok.dataset.config import load_dataset_config


def test_build_dataset_legacy_smoke():
    cfg_path = Path(__file__).resolve().parent.parent / "configs" / "dataset.yaml"
    assert cfg_path.exists()

    with tempfile.TemporaryDirectory() as td:
        out_root = Path(td)
        # Force legacy mode for this test, regardless of the default config.
        import yaml

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        raw.setdefault("record_build", {})
        raw["record_build"]["mode"] = "legacy_milestones"
        cfg_tmp = out_root / "dataset_legacy_test.yaml"
        cfg_tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

        dataset_version = load_dataset_config(cfg_tmp).dataset_version
        build_dataset(config_path=cfg_tmp, offline=True, out_root=out_root, track="A")

        root = out_root / dataset_version
        pub = root / "public"
        priv = root / "private"

        assert (pub / "track_A_extended_records.jsonl").exists()
        assert (pub / "track_A_core_records.jsonl").exists()
        assert (pub / "taxonomy.json").exists()
        assert (pub / "selection_log_extended.jsonl").exists()
        assert (pub / "selection_log_core.jsonl").exists()
        assert (pub / "dependency_graph_extended.edgelist").exists()
        assert (pub / "dependency_graph_core.edgelist").exists()
        assert (pub / "qa_report_extended.jsonl").exists()
        assert (pub / "qa_report_core.jsonl").exists()
        assert (pub / "dataset_manifest.json").exists()

        # Sealed worlds exist for configured seeds
        for seed in (42, 43, 44):
            assert (pub / "sealed_worlds" / str(seed) / "extended" / "records.jsonl").exists()
            assert (pub / "sealed_worlds" / str(seed) / "extended" / "manifest.json").exists()
            assert (pub / "sealed_worlds" / str(seed) / "core" / "records.jsonl").exists()
            assert (pub / "sealed_worlds" / str(seed) / "core" / "manifest.json").exists()
            # Public must NOT contain the private codebook mapping
            assert not (pub / "sealed_worlds" / str(seed) / "codebook.json").exists()
            assert (priv / "mapping_key" / f"seed_{seed}.codebook.json").exists()

        # Manifest references QA + sealed worlds
        man = json.loads((pub / "dataset_manifest.json").read_text(encoding="utf-8"))
        assert man["build_mode"] == "legacy_milestones"
        assert man["qa"]["core"]["n_records"] == 20
        assert man["qa"]["extended"]["n_records"] == 20
        assert len(man["sealed_worlds"]["seeds"]) == 3
