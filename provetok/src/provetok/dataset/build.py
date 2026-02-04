"""Dataset build orchestration."""

from __future__ import annotations

import json
import subprocess
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


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _compute_formula_graph_summary(paths: DatasetPaths, *, track: str, tier: str) -> Dict[str, Any]:
    """Summarize formula_graph extraction status from private mapping rows."""
    targets = ["A", "B"] if track == "both" else [track]

    def init_counts() -> Dict[str, int]:
        return {
            "n_rows": 0,
            "n_arxiv": 0,
            "ok": 0,
            "empty": 0,
            "missing_source": 0,
            "error": 0,
            "skipped_offline": 0,
            "skipped_non_arxiv": 0,
            "unknown": 0,
        }

    by_track: Dict[str, Any] = {}
    overall = init_counts()

    for t in targets:
        p = paths.private_mapping_path(t, tier)
        if not p.exists():
            continue

        counts = init_counts()
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            counts["n_rows"] += 1
            overall["n_rows"] += 1

            ft_source = str(row.get("fulltext_source") or "")
            if ft_source == "arxiv":
                counts["n_arxiv"] += 1
                overall["n_arxiv"] += 1

            status = str(row.get("formula_graph_status") or "")
            key = status if status in counts else "unknown"
            counts[key] += 1
            overall[key] += 1

        arxiv_ok_rate = (counts["ok"] / counts["n_arxiv"]) if counts["n_arxiv"] else 0.0
        by_track[t] = {**counts, "arxiv_ok_rate": round(arxiv_ok_rate, 4)}

    overall_arxiv_ok_rate = (overall["ok"] / overall["n_arxiv"]) if overall["n_arxiv"] else 0.0
    manual_queue_n = _count_lines(paths.private_dir / "manual_formula_queue.jsonl")

    return {
        "tier": tier,
        "overall": {**overall, "arxiv_ok_rate": round(overall_arxiv_ok_rate, 4)},
        "by_track": by_track,
        "manual_queue_n": manual_queue_n,
    }


def _git_metadata() -> Dict[str, Any]:
    """Best-effort git metadata for reproducible manifests."""
    try:
        top = (
            subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=top, stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        dirty = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=top, stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        return {"git_commit": commit, "git_dirty": dirty}
    except Exception:
        return {}


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return _count_lines(path)


def _selection_exclusion_breakdown(selection_log_path: Path, *, track_id: Optional[str] = None) -> Dict[str, int]:
    if not selection_log_path.exists():
        return {}
    counts: Dict[str, int] = {}
    for line in selection_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if track_id and str(row.get("track_id") or "") != track_id:
            continue
        if str(row.get("action") or "") != "exclude":
            continue
        tag = str(row.get("reason_tag") or "unknown")
        counts[tag] = counts.get(tag, 0) + 1
    return counts


def _targets_from_config(raw_cfg: Dict[str, Any], *, track: str) -> Dict[str, Dict[str, int]]:
    targets = ["A", "B"] if track == "both" else [track]
    out: Dict[str, Dict[str, int]] = {}
    tracks_cfg = raw_cfg.get("tracks") or {}
    for t in targets:
        cfg_t = tracks_cfg.get(t) or {}
        out[t] = {
            "core": int(cfg_t.get("core_size") or cfg_t.get("target_min") or 0),
            "extended": int(cfg_t.get("extended_size") or cfg_t.get("target_max") or cfg_t.get("target_min") or 0),
        }
    return out


def _actuals_from_outputs(paths: DatasetPaths, *, track: str) -> Dict[str, Dict[str, int]]:
    targets = ["A", "B"] if track == "both" else [track]
    out: Dict[str, Dict[str, int]] = {}
    for t in targets:
        out[t] = {
            "core": _count_jsonl(paths.public_records_path(t, "core")),
            "extended": _count_jsonl(paths.public_records_path(t, "extended")),
        }
    return out


def _enforce_qa_thresholds(raw_cfg: Dict[str, Any], *, qa_summary: Dict[str, Any], edge_agreement: Dict[str, Any]) -> None:
    cfg = raw_cfg.get("qa") or {}
    schema_req = float(cfg.get("schema_pass_rate_required", 0.0) or 0.0)
    consistency_req = float(cfg.get("consistency_pass_rate_required", 0.0) or 0.0)
    edge_req = float(cfg.get("edge_coverage_threshold", 0.0) or 0.0)
    other_ratio_max = float(cfg.get("taxonomy_other_ratio_max_core", 1.0) or 1.0)

    def require_rate(name: str, actual: float, required: float) -> None:
        if required <= 0.0:
            return
        if actual + 1e-12 < required:
            raise RuntimeError(f"QA threshold failed: {name}={actual:.4f} < required={required:.4f}")

    # Schema/consistency are checked per tier.
    for tier in ("core", "extended"):
        summ = qa_summary.get(tier) or {}
        require_rate(f"{tier}.schema_pass_rate", float(summ.get("schema_pass_rate", 0.0) or 0.0), schema_req)
        require_rate(
            f"{tier}.consistency_pass_rate",
            float(summ.get("consistency_pass_rate", 0.0) or 0.0),
            consistency_req,
        )

    # Taxonomy coverage (Core only): optionally cap how much falls into "other".
    if other_ratio_max < 1.0:
        core_tax = (qa_summary.get("core") or {}).get("taxonomy") or {}
        other_ratio = float(core_tax.get("other_ratio", 0.0) or 0.0)
        if other_ratio - other_ratio_max > 1e-12:
            raise RuntimeError(
                f"QA threshold failed: core.taxonomy.other_ratio={other_ratio:.4f} > max={other_ratio_max:.4f}"
            )

    # Edge coverage is gated on core only (benchmark tier).
    if edge_req > 0.0:
        core_overall = (edge_agreement.get("core") or {}).get("overall") or {}
        n_edges = core_overall.get("n_edges") or {}
        n_other = int(n_edges.get("s2", 0) or 0) + int(n_edges.get("opencitations", 0) or 0)
        # If no cross-source edges are available (e.g., legacy/offline builds),
        # the agreement metric is undefined; skip the gate.
        if n_other > 0:
            cov = (core_overall.get("coverage") or {}).get("openalex_by_union", 0.0)
            require_rate("core.edge_coverage.openalex_by_union", float(cov or 0.0), edge_req)


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
        from provetok.dataset.edge_agreement import compute_edge_agreement
        edge_agreement = {
            "core": compute_edge_agreement(paths=paths, tier="core", track=track),
            "extended": compute_edge_agreement(paths=paths, tier="extended", track=track),
        }
        from provetok.dataset.sealed_worlds import export_sealed_worlds
        sealed_summary = export_sealed_worlds(cfg.raw, paths=paths, track=track)
        from provetok.dataset.attack_suite import export_attack_suite
        export_attack_suite(paths)
        from provetok.dataset.manifest import compute_public_artifacts
        artifacts = compute_public_artifacts(paths.public_dir)

        targets = _targets_from_config(cfg.raw, track=track)
        actuals = _actuals_from_outputs(paths, track=track)
        track_ids = list(targets.keys())
        exclusions = {
            "extended": {
                "overall": _selection_exclusion_breakdown(paths.public_selection_log_path("extended")),
                **{
                    tid: _selection_exclusion_breakdown(paths.public_selection_log_path("extended"), track_id=tid)
                    for tid in track_ids
                },
            },
            "core": {
                "overall": _selection_exclusion_breakdown(paths.public_selection_log_path("core")),
                **{
                    tid: _selection_exclusion_breakdown(paths.public_selection_log_path("core"), track_id=tid)
                    for tid in track_ids
                },
            },
        }

        _enforce_qa_thresholds(cfg.raw, qa_summary=qa_summary, edge_agreement=edge_agreement)

        _write_json(
            paths.public_dir / "dataset_manifest.json",
            {
                "dataset_version": cfg.dataset_version,
                "build_mode": mode,
                "track": track,
                **_git_metadata(),
                "targets": targets,
                "actuals": actuals,
                "selection_exclusions": exclusions,
                "qa": qa_summary,
                "edge_agreement": edge_agreement,
                "confidence": {
                    "core": _compute_confidence_summary(paths, track=track, tier="core"),
                    "extended": _compute_confidence_summary(paths, track=track, tier="extended"),
                },
                "formula_graph": {
                    "core": _compute_formula_graph_summary(paths, track=track, tier="core"),
                    "extended": _compute_formula_graph_summary(paths, track=track, tier="extended"),
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
        "core": run_qa(paths=paths, track=track, tier="core", cfg=cfg.raw),
        "extended": run_qa(paths=paths, track=track, tier="extended", cfg=cfg.raw),
    }
    from provetok.dataset.edge_agreement import compute_edge_agreement
    edge_agreement = {
        "core": compute_edge_agreement(paths=paths, tier="core", track=track),
        "extended": compute_edge_agreement(paths=paths, tier="extended", track=track),
    }
    from provetok.dataset.sealed_worlds import export_sealed_worlds
    sealed_summary = export_sealed_worlds(cfg.raw, paths=paths, track=track)
    from provetok.dataset.attack_suite import export_attack_suite
    export_attack_suite(paths)
    from provetok.dataset.manifest import compute_public_artifacts
    artifacts = compute_public_artifacts(paths.public_dir)

    targets = _targets_from_config(cfg.raw, track=track)
    actuals = _actuals_from_outputs(paths, track=track)
    track_ids = list(targets.keys())
    exclusions = {
        "extended": {
            "overall": _selection_exclusion_breakdown(paths.public_selection_log_path("extended")),
            **{
                tid: _selection_exclusion_breakdown(paths.public_selection_log_path("extended"), track_id=tid)
                for tid in track_ids
            },
        },
        "core": {
            "overall": _selection_exclusion_breakdown(paths.public_selection_log_path("core")),
            **{
                tid: _selection_exclusion_breakdown(paths.public_selection_log_path("core"), track_id=tid)
                for tid in track_ids
            },
        },
    }

    _enforce_qa_thresholds(cfg.raw, qa_summary=qa_summary, edge_agreement=edge_agreement)

    _write_json(
        paths.public_dir / "dataset_manifest.json",
        {
            "dataset_version": cfg.dataset_version,
            "build_mode": mode,
            "track": track,
            **_git_metadata(),
            "targets": targets,
            "actuals": actuals,
            "selection_exclusions": exclusions,
            "qa": qa_summary,
            "edge_agreement": edge_agreement,
            "confidence": {
                "core": _compute_confidence_summary(paths, track=track, tier="core"),
                "extended": _compute_confidence_summary(paths, track=track, tier="extended"),
            },
            "formula_graph": {
                "core": _compute_formula_graph_summary(paths, track=track, tier="core"),
                "extended": _compute_formula_graph_summary(paths, track=track, tier="extended"),
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
        "core": run_qa(paths=paths, track=track, tier="core", cfg=cfg.raw),
        "extended": run_qa(paths=paths, track=track, tier="extended", cfg=cfg.raw),
    }
