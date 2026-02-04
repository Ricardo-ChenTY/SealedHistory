"""Tests for private (hidden) seeds export behavior."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset
from provetok.dataset.config import load_dataset_config


def test_private_seeds_export_to_private_only():
    cfg_path = Path(__file__).resolve().parent.parent / "configs" / "dataset.yaml"
    assert cfg_path.exists()

    import yaml

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    raw.setdefault("record_build", {})
    raw["record_build"]["mode"] = "legacy_milestones"
    raw.setdefault("seeds", {})
    raw["seeds"]["public_seeds"] = [1]
    raw["seeds"]["private_seeds"] = [99]

    with tempfile.TemporaryDirectory() as td:
        out_root = Path(td)
        cfg_tmp = out_root / "dataset_private_seeds.yaml"
        cfg_tmp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

        dataset_version = load_dataset_config(cfg_tmp).dataset_version
        build_dataset(config_path=cfg_tmp, offline=True, out_root=out_root, track="A")

        root = out_root / dataset_version
        pub = root / "public"
        priv = root / "private"

        # Public seed present in public/, private seed must NOT.
        assert (pub / "sealed_worlds" / "1" / "extended" / "records.jsonl").exists()
        assert not (pub / "sealed_worlds" / "99").exists()

        # Private seed worlds exist under private/ only.
        assert (priv / "sealed_worlds_private" / "99" / "extended" / "records.jsonl").exists()
        assert (priv / "sealed_worlds_private" / "99" / "extended" / "manifest.json").exists()
        assert (priv / "sealed_worlds_private" / "99" / "core" / "records.jsonl").exists()
        assert (priv / "sealed_worlds_private" / "99" / "core" / "manifest.json").exists()

        # Codebook is always private.
        assert (priv / "mapping_key" / "seed_99.codebook.json").exists()

        man = json.loads((pub / "dataset_manifest.json").read_text(encoding="utf-8"))
        priv_seeds = man.get("sealed_worlds", {}).get("private_seeds") or []
        assert any(int(s.get("seed", 0)) == 99 for s in priv_seeds)

