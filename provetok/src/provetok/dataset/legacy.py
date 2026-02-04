"""Legacy dataset export (PaperRecord -> PaperRecordV2).

This is a pragmatic bridge: it allows offline use and tests while the full
OpenAlex/S2/OC/fulltext pipeline is implemented.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema import PaperRecord, load_records
from provetok.data.schema_v2 import (
    PaperRecordInternalV2,
    PaperRecordV2,
    FormulaGraph,
    Protocol,
    Results,
    save_records_internal_v2,
    save_records_v2,
)
from provetok.dataset.paths import DatasetPaths

logger = logging.getLogger(__name__)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")


def default_taxonomy() -> Dict[str, Any]:
    return {
        "version": 1,
        "mechanism_tags": {
            "other": {"description": "Unclassified / placeholder tag for legacy exports."},
        },
        "task_families": {
            "unknown_task": {"description": "Task family unknown or not extracted."},
        },
        "datasets": {
            "unknown_dataset": {"description": "Dataset unknown or not extracted."},
        },
        "metrics": {
            "unknown_metric": {"description": "Metric unknown or not extracted."},
        },
        "compute_classes": {
            "unknown_compute": {"description": "Compute class unknown or not extracted."},
        },
        "train_regime_classes": {
            "unknown_regime": {"description": "Train regime unknown or not extracted."},
        },
        "notes": "This taxonomy is a minimal scaffold for plan.md; replace with a richer taxonomy for real releases.",
    }


def _track_inputs() -> Dict[str, Path]:
    return {
        "A": Path("provetok/data/raw/micro_history_a.jsonl"),
        "B": Path("provetok/data/raw/micro_history_b.jsonl"),
    }


def _bucket_delta(delta: float) -> int:
    """Bucket delta_vs_prev into an integer in [-3, 3]."""
    if delta <= -0.10:
        return -3
    if delta <= -0.03:
        return -2
    if delta <= -0.01:
        return -1
    if delta < 0.01:
        return 0
    if delta < 0.03:
        return 1
    if delta < 0.10:
        return 2
    return 3


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _infer_track_id(paper_id: str, fallback: str) -> str:
    if paper_id.startswith("A_"):
        return "A"
    if paper_id.startswith("B_"):
        return "B"
    return fallback


def export_legacy_tracks(raw_cfg: Dict[str, Any], paths: DatasetPaths, track: str = "A") -> None:
    """Export local JSONL into tiered public/private artifacts.

    The legacy path is intentionally offline-friendly: it uses local curated
    milestone JSONL files. When tier sizes exceed available data, it exports all
    available records and reports the shortfall via manifests/QA.
    """

    targets: List[str]
    if track == "both":
        targets = ["A", "B"]
    else:
        targets = [track]

    _write_json(paths.public_dir / "taxonomy.json", default_taxonomy())

    selection_rows_core: List[Dict[str, Any]] = []
    selection_rows_extended: List[Dict[str, Any]] = []
    dep_edges_core: List[str] = []
    dep_edges_extended: List[str] = []

    tracks_cfg = raw_cfg.get("tracks") or {}

    for t in targets:
        cfg_t = tracks_cfg.get(t) or {}
        core_size = int(cfg_t.get("core_size", 40) or 40)
        extended_size = int(cfg_t.get("extended_size", 500) or 500)

        in_path = _track_inputs().get(t)
        if not in_path or not in_path.exists():
            logger.warning("Legacy input missing for track %s: %s", t, in_path)
            continue

        legacy = load_records(in_path)
        if not legacy:
            logger.warning("No records in %s", in_path)
            continue

        # Legacy ordering is already curated; use prefix truncation to preserve dependency closure.
        extended_legacy = legacy[: min(len(legacy), extended_size)]
        core_legacy = extended_legacy[: min(len(extended_legacy), core_size)]

        in_sha = _sha256_text(in_path.read_text(encoding="utf-8"))

        def build_rank_map(items: List[PaperRecord]) -> Dict[str, int]:
            ranked_local = sorted(
                items,
                key=lambda r: (-float(getattr(r.results, "metric_main", 0.0)), r.paper_id),
            )
            return {r.paper_id: i + 1 for i, r in enumerate(ranked_local)}

        rank_map_ext = build_rank_map(extended_legacy)
        rank_map_core = build_rank_map(core_legacy)

        def export_tier(items: List[PaperRecord], tier: str, rank_map: Dict[str, int]) -> None:
            public_records: List[PaperRecordV2] = []
            internal_records: List[PaperRecordInternalV2] = []
            id_set = {r.paper_id for r in items}

            for r in items:
                track_id = _infer_track_id(r.paper_id, t)
                deps = list(r.dependencies or [])
                # Keep dependencies inside the tier only (should already hold for prefix truncation).
                deps = [d for d in deps if d in id_set]
                pub = PaperRecordV2(
                    paper_id=r.paper_id,
                    track_id=track_id,
                    dependencies=deps,
                    background=r.background or "",
                    mechanism_tags=["other"],
                    formula_graph=FormulaGraph(),
                    protocol=Protocol(),
                    results=Results(
                        primary_metric_rank=rank_map.get(r.paper_id, 0),
                        delta_over_baseline_bucket=_bucket_delta(float(r.results.delta_vs_prev)),
                        ablation_delta_buckets=[],
                        significance_flag=None,
                    ),
                    provenance={
                        "source": "legacy_jsonl",
                        "input_path": str(in_path),
                        "input_sha256": in_sha,
                        "tier": tier,
                    },
                    qa={},
                )
                public_records.append(pub)
                internal_records.append(
                    PaperRecordInternalV2(
                        public=pub,
                        title=r.title,
                        year=r.year,
                        venue=r.venue,
                        authors=list(r.authors) if r.authors else None,
                        keywords=list(r.keywords) if r.keywords else None,
                        retrieved_at_unix=int(time.time()),
                        source_paths=[str(in_path)],
                    )
                )

                row = {
                    "ts_unix": int(time.time()),
                    "track_id": track_id,
                    "tier": tier,
                    "paper_id": r.paper_id,
                    "action": "include",
                    "reason_tag": "legacy_curated_list" if tier == "extended" else "legacy_core_prefix",
                    "evidence": f"Imported from {in_path}",
                }
                if tier == "extended":
                    selection_rows_extended.append(row)
                else:
                    selection_rows_core.append(row)

                # Dependency edges: dep -> paper (prerequisite to dependent)
                for dep in deps:
                    if tier == "extended":
                        dep_edges_extended.append(f"{dep} {r.paper_id}")
                    else:
                        dep_edges_core.append(f"{dep} {r.paper_id}")

            save_records_v2(public_records, paths.public_records_path(t, tier))
            save_records_internal_v2(internal_records, paths.private_records_path(t, tier))

        export_tier(extended_legacy, "extended", rank_map_ext)
        export_tier(core_legacy, "core", rank_map_core)

    _write_jsonl(paths.public_selection_log_path("extended"), selection_rows_extended)
    _write_jsonl(paths.public_selection_log_path("core"), selection_rows_core)
    _write_lines(paths.public_dependency_graph_path("extended"), dep_edges_extended)
    _write_lines(paths.public_dependency_graph_path("core"), dep_edges_core)
