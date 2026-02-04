"""Export sealed worlds (multi-seed) for PaperRecordV2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from provetok.data.schema_v2 import (
    PaperRecordInternalV2,
    PaperRecordV2,
    load_records_internal_v2,
    load_records_v2,
    save_records_v2,
)
from provetok.dataset.paths import DatasetPaths
from provetok.sdg.sealer_v2 import SDGPipelineV2


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_keywords_by_paper_id(paths: DatasetPaths, track: str, tiers: List[str]) -> Dict[str, List[str]]:
    targets = ["A", "B"] if track == "both" else [track]
    keywords: Dict[str, List[str]] = {}
    for t in targets:
        for tier in tiers:
            p = paths.private_records_path(t, tier)
            if not p.exists():
                continue
            for rec in load_records_internal_v2(p):
                if rec.keywords:
                    keywords[rec.public.paper_id] = list(rec.keywords)
    return keywords


def export_sealed_worlds(cfg: Dict[str, Any], *, paths: DatasetPaths, track: str) -> Dict[str, Any]:
    seeds = list((cfg.get("seeds") or {}).get("public_seeds") or [])
    sdg_cfg = cfg.get("sdg") or {}
    enable_l1 = bool(sdg_cfg.get("enable_l1", True))
    enable_l2 = bool(sdg_cfg.get("enable_l2", True))
    enable_l3 = bool(sdg_cfg.get("enable_l3", True))

    tiers = ["core", "extended"]
    targets = ["A", "B"] if track == "both" else [track]

    records_by_tier: Dict[str, List[PaperRecordV2]] = {tier: [] for tier in tiers}
    for tier in tiers:
        for t in targets:
            p = paths.public_records_path(t, tier)
            if p.exists():
                records_by_tier[tier].extend(load_records_v2(p))

    keywords_map = _load_keywords_by_paper_id(paths, track, tiers=tiers)

    manifests: Dict[str, Any] = {"seeds": []}
    for seed in seeds:
        seed_dir = paths.public_dir / "sealed_worlds" / str(seed)
        seed_dir.mkdir(parents=True, exist_ok=True)

        pipeline = SDGPipelineV2(seed=int(seed), enable_l1=enable_l1, enable_l2=enable_l2, enable_l3=enable_l3)

        tier_mans: Dict[str, Any] = {}
        for tier in ("extended", "core"):
            out_dir = seed_dir / tier
            out_dir.mkdir(parents=True, exist_ok=True)

            sealed = [
                pipeline.seal_record(r, lexical_terms=keywords_map.get(r.paper_id))
                for r in records_by_tier.get(tier, [])
            ]
            rec_path = out_dir / "records.jsonl"
            save_records_v2(sealed, rec_path)
            tier_mans[tier] = {
                "n_records": len(sealed),
                "records_sha256": _sha256_file(rec_path),
            }
            _write_json(out_dir / "manifest.json", {"seed": int(seed), "tier": tier, **tier_mans[tier]})

        # IMPORTANT: do not publish the codebook mapping (it contains real terms).
        cb_path = paths.private_dir / "mapping_key" / f"seed_{int(seed)}.codebook.json"
        pipeline.codebook.save(cb_path)

        manifests["seeds"].append(
            {
                "seed": int(seed),
                "tiers": tier_mans,
                "codebook_sha256": _sha256_file(cb_path),
                "sdg": {"enable_l1": enable_l1, "enable_l2": enable_l2, "enable_l3": enable_l3},
            }
        )

    # Also export SDG config snapshot for reproducibility
    _write_json(paths.public_dir / "sdg_configs" / "sdg.json", {"sdg": {"enable_l1": enable_l1, "enable_l2": enable_l2, "enable_l3": enable_l3}})

    return manifests
