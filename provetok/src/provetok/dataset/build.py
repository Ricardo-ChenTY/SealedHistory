"""Dataset build orchestration."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from provetok.dataset.config import load_dataset_config
from provetok.dataset.paths import DatasetPaths


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _quantiles(xs: List[float], ps: List[float]) -> Dict[str, float]:
    if not xs:
        return {f"p{int(p * 100)}": 0.0 for p in ps}
    xs_sorted = sorted(xs)
    out: Dict[str, float] = {}
    n = len(xs_sorted)
    for p in ps:
        if n == 1:
            out[f"p{int(p * 100)}"] = float(xs_sorted[0])
            continue
        idx = max(0, min(n - 1, int(round(p * (n - 1)))))
        out[f"p{int(p * 100)}"] = float(xs_sorted[idx])
    return out


def _compute_confidence_summary(paths: DatasetPaths, *, track: str, tier: str) -> Dict[str, Any]:
    """Summarize deterministic confidence signals from private mapping rows."""
    targets = ["A", "B"] if track == "both" else [track]
    by_track: Dict[str, Any] = {}
    all_scores: List[float] = []

    for t in targets:
        p = paths.private_mapping_path(t, tier)
        if not p.exists():
            continue

        scores: List[float] = []
        n = 0
        has_abstract = 0
        has_s2 = 0
        has_fulltext = 0

        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            n += 1

            abs_len = len(str(row.get("abstract") or "").strip())
            if abs_len >= 200:
                has_abstract += 1
            if row.get("s2_id"):
                has_s2 += 1
            if row.get("pdf_sha256") or (row.get("source_paths") or []):
                has_fulltext += 1

            conf = row.get("confidence_score")
            try:
                conf_f = float(conf) if conf is not None else 0.0
            except Exception:
                conf_f = 0.0
            scores.append(conf_f)

        all_scores.extend(scores)
        by_track[t] = {
            "n": n,
            "mean": (sum(scores) / n) if n else 0.0,
            "min": min(scores) if scores else 0.0,
            "max": max(scores) if scores else 0.0,
            **_quantiles(scores, [0.5, 0.9]),
            "abstract_present_rate": (has_abstract / n) if n else 0.0,
            "s2_enriched_rate": (has_s2 / n) if n else 0.0,
            "fulltext_cached_rate": (has_fulltext / n) if n else 0.0,
        }

    n_all = len(all_scores)
    overall = {
        "n": n_all,
        "mean": (sum(all_scores) / n_all) if n_all else 0.0,
        "min": min(all_scores) if all_scores else 0.0,
        "max": max(all_scores) if all_scores else 0.0,
        **_quantiles(all_scores, [0.5, 0.9]),
    }
    return {"tier": tier, "overall": overall, "by_track": by_track}


def build_dataset(
    config_path: Optional[Path] = None,
    offline: bool = False,
    out_root: Optional[Path] = None,
    track: str = "both",
) -> None:
    """Run the end-to-end dataset pipeline.

    This is the main entry point for implementing plan.md. For now, it supports
    an offline-friendly path via `record_build.mode=legacy_milestones` and a
    full online path (OpenAlex/S2/OC/arXiv) implemented in submodules.
    """

    cfg = load_dataset_config(config_path)
    export_root = out_root if out_root else cfg.export_root
    paths = DatasetPaths(export_root=export_root, dataset_version=cfg.dataset_version)
    paths.ensure_dirs()

    started = time.time()

    mode = str(cfg.raw.get("record_build", {}).get("mode", "legacy_milestones"))
    if mode == "legacy_milestones":
        qa_summary = export_legacy_dataset(config_path=config_path, out_root=out_root, track=track)
        from provetok.dataset.sealed_worlds import export_sealed_worlds
        sealed_summary = export_sealed_worlds(cfg.raw, paths=paths, track=track)
        from provetok.dataset.attack_suite import export_attack_suite
        export_attack_suite(paths)
        from provetok.dataset.manifest import compute_public_artifacts
        artifacts = compute_public_artifacts(paths.public_dir)
        _write_json(
            paths.public_dir / "dataset_manifest.json",
            {
                "dataset_version": cfg.dataset_version,
                "build_mode": mode,
                "track": track,
                "qa": qa_summary,
                "confidence": {
                    "core": _compute_confidence_summary(paths, track=track, tier="core"),
                    "extended": _compute_confidence_summary(paths, track=track, tier="extended"),
                },
                "sealed_worlds": sealed_summary,
                "config_path": str(cfg.path),
                "config": cfg.raw,
                "public_artifacts": artifacts,
                "built_at_unix": int(time.time()),
                "elapsed_sec": round(time.time() - started, 3),
            },
        )
        return

    # Online path is implemented in dedicated modules.
    from provetok.dataset.pipeline import build_online_dataset

    build_online_dataset(cfg.raw, paths=paths, offline=offline, track=track)
    from provetok.dataset.qa import run_qa
    qa_summary = {
        "core": run_qa(paths=paths, track=track, tier="core"),
        "extended": run_qa(paths=paths, track=track, tier="extended"),
    }
    from provetok.dataset.sealed_worlds import export_sealed_worlds
    sealed_summary = export_sealed_worlds(cfg.raw, paths=paths, track=track)
    from provetok.dataset.attack_suite import export_attack_suite
    export_attack_suite(paths)
    from provetok.dataset.manifest import compute_public_artifacts
    artifacts = compute_public_artifacts(paths.public_dir)
    _write_json(
        paths.public_dir / "dataset_manifest.json",
        {
            "dataset_version": cfg.dataset_version,
            "build_mode": mode,
            "track": track,
            "qa": qa_summary,
            "confidence": {
                "core": _compute_confidence_summary(paths, track=track, tier="core"),
                "extended": _compute_confidence_summary(paths, track=track, tier="extended"),
            },
            "sealed_worlds": sealed_summary,
            "config_path": str(cfg.path),
            "config": cfg.raw,
            "public_artifacts": artifacts,
            "built_at_unix": int(time.time()),
            "elapsed_sec": round(time.time() - started, 3),
        },
    )


def export_legacy_dataset(
    config_path: Optional[Path] = None,
    out_root: Optional[Path] = None,
    track: str = "A",
) -> Dict[str, Any]:
    """Export existing legacy JSONL (PaperRecord) into tiered layout.

    This path keeps the repository usable offline and provides a minimal,
    reproducible artifact set suitable for tests and demos.
    """

    cfg = load_dataset_config(config_path)
    export_root = out_root if out_root else cfg.export_root
    paths = DatasetPaths(export_root=export_root, dataset_version=cfg.dataset_version)
    paths.ensure_dirs()

    from provetok.dataset.legacy import export_legacy_tracks

    export_legacy_tracks(cfg.raw, paths=paths, track=track)
    from provetok.dataset.qa import run_qa
    return {
        "core": run_qa(paths=paths, track=track, tier="core"),
        "extended": run_qa(paths=paths, track=track, tier="extended"),
    }
