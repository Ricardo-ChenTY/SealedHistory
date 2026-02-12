"""Run oral-ready main results table on a scale (non-toy) dataset.

This vNext script is dataset-parametric and is intended for E6/E7/E10:
- Scale-up: run on a larger dataset built from v2 internal exports.
- Stronger baselines: include simple, transparent baselines.
- Cost/profile: persist a machine-readable run_meta.json.

Outputs (under --output_dir):
- main_results.csv
- main_results.md
- per_run_metrics.json
- summary.json
- run_meta.json
- attacks/*.json
- {config_id}/{track}/seed_{seed}/eval_report.json + trace.json
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import resource
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from provetok.agents.base import CopyLastAgent, DependencyAwareAgent, FrontierSynthesisAgent, RandomAgent, run_agent_loop
from provetok.data.schema import PaperRecord, load_records, save_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer, ParetoPoint, save_eval_report
from run_oral_adaptive_attack_vnext import run_adaptive_attack


CONFIGS = [
    {"config_id": "sealed_frontier", "label": "SealedHistory (main)", "agent": "frontier", "view": "sealed"},
    {"config_id": "raw_frontier", "label": "Raw (upper bound)", "agent": "frontier", "view": "raw"},
    {"config_id": "sealed_dependency", "label": "Strong baseline (dependency agent)", "agent": "dependency", "view": "sealed"},
    {"config_id": "sealed_copylast", "label": "Strong baseline (copylast agent)", "agent": "copylast", "view": "sealed"},
    {"config_id": "sealed_l1only_frontier", "label": "Baseline (L1-only sealing)", "agent": "frontier", "view": "sealed_l1only"},
    {"config_id": "sealed_summary_frontier", "label": "Baseline (extractive summary)", "agent": "frontier", "view": "sealed_summary"},
    {"config_id": "sealed_redact_frontier", "label": "Baseline (naive redaction)", "agent": "frontier", "view": "sealed_redact"},
]


def _agent_by_name(name: str, seed: int):
    if name == "random":
        return RandomAgent(seed=seed)
    if name == "copylast":
        return CopyLastAgent(seed=seed)
    if name == "dependency":
        return DependencyAwareAgent(seed=seed)
    if name == "frontier":
        return FrontierSynthesisAgent(seed=seed)
    raise ValueError(f"unknown agent: {name}")


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _apply_naive_redaction(records: List[PaperRecord]) -> List[PaperRecord]:
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.title = "Redacted title (baseline)"
        d.background = "Redacted background (baseline): problem context removed."
        d.mechanism = "Redacted mechanism (baseline): method details removed."
        d.experiment = "Redacted experiment (baseline): evaluation details removed."
        d.keywords = []
        out.append(d)
    return out


def _apply_extractive_summary(records: List[PaperRecord], *, max_tokens: int = 40) -> List[PaperRecord]:
    def trunc(s: str) -> str:
        toks = str(s or "").split()
        return " ".join(toks[: max(1, int(max_tokens))])

    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.background = trunc(d.background)
        d.mechanism = trunc(d.mechanism)
        d.experiment = trunc(d.experiment)
        d.keywords = []
        out.append(d)
    return out


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _load_track(dataset_dir: Path, track_id: str) -> dict:
    raw_path = dataset_dir / f"track_{track_id}_raw.jsonl"
    sealed_path = dataset_dir / f"track_{track_id}_sealed.jsonl"
    sealed_l1_path = dataset_dir / f"track_{track_id}_sealed_l1only.jsonl"

    cb_sealed = dataset_dir / f"track_{track_id}_sealed.codebook.json"
    cb_l1 = dataset_dir / f"track_{track_id}_sealed_l1only.codebook.json"

    raw = load_records(raw_path)
    sealed = load_records(sealed_path)
    sealed_l1 = load_records(sealed_l1_path) if sealed_l1_path.exists() else []

    sealed_redact = _apply_naive_redaction(sealed)
    sealed_redact_path = dataset_dir / f"track_{track_id}_sealed_redact.jsonl"
    save_records(sealed_redact, sealed_redact_path)

    sealed_summary = _apply_extractive_summary(sealed, max_tokens=40)
    sealed_summary_path = dataset_dir / f"track_{track_id}_sealed_summary.jsonl"
    save_records(sealed_summary, sealed_summary_path)

    return {
        "raw_path": raw_path,
        "sealed_path": sealed_path,
        "sealed_l1_path": sealed_l1_path,
        "sealed_redact_path": sealed_redact_path,
        "sealed_summary_path": sealed_summary_path,
        "codebook_sealed": cb_sealed if cb_sealed.exists() else None,
        "codebook_l1": cb_l1 if cb_l1.exists() else None,
        "raw": raw,
        "sealed": sealed,
        "sealed_l1only": sealed_l1,
        "sealed_redact": sealed_redact,
        "sealed_summary": sealed_summary,
    }


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _run_one(
    *,
    observed: List[PaperRecord],
    raw: List[PaperRecord],
    agent_name: str,
    seed: int,
    out_eval_path: Path,
) -> dict:
    env = BenchmarkEnvironment(
        sealed_records=observed,
        real_records=raw,
        budget=max(40, len(raw) + 4),
        fast_mode=True,
    )
    agent = _agent_by_name(agent_name, seed=seed)
    trace = run_agent_loop(agent, env, max_cycles=80)

    rubric = AutoRubricScorer().score_run(trace, raw)
    save_eval_report(
        rubric_result=rubric,
        audit_summary={},
        pareto_points=[ParetoPoint(config_name=agent_name, leakage=0.0, utility=rubric["total"])],
        output_path=out_eval_path,
    )

    trace_path = out_eval_path.with_name("trace.json")
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "utility": float(rubric.get("total", 0.0)),
        "n_proposals": int(rubric.get("n_proposals", 0)),
        "n_accepted": int(rubric.get("n_accepted", 0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run oral vNext main-table experiments on a scale dataset.")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--output_dir", default="runs/EXP-022")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(args.dataset_dir)

    track_data = {tid: _load_track(dataset_dir, tid) for tid in ["A", "B"]}

    # Run attacks once per view per track.
    views = {
        "raw": ("raw_path", None),
        "sealed": ("sealed_path", "codebook_sealed"),
        "sealed_l1only": ("sealed_l1_path", "codebook_l1"),
        "sealed_summary": ("sealed_summary_path", "codebook_sealed"),
        "sealed_redact": ("sealed_redact_path", "codebook_sealed"),
    }
    attacks: Dict[str, dict] = {}
    (out_root / "attacks").mkdir(parents=True, exist_ok=True)
    for tid in ["A", "B"]:
        raw_path = track_data[tid]["raw_path"]
        for view_name, (rec_key, cb_key) in views.items():
            sealed_path = track_data[tid][rec_key]
            cb = track_data[tid][cb_key] if cb_key else None
            atk = run_adaptive_attack(
                sealed_path=Path(sealed_path),
                raw_path=Path(raw_path),
                codebook_path=Path(cb) if cb else None,
                max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
                seed=int(args.attack_seed),
            )
            attacks[f"{tid}:{view_name}"] = atk
            out_p = out_root / "attacks" / f"{tid}_{view_name}.json"
            out_p.write_text(json.dumps(atk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    per_run: List[dict] = []
    for cfg in CONFIGS:
        for tid in ["A", "B"]:
            raw = track_data[tid]["raw"]
            observed = track_data[tid][cfg["view"]]
            for seed in args.seeds:
                out_eval = out_root / cfg["config_id"] / tid / f"seed_{seed}" / "eval_report.json"
                out_eval.parent.mkdir(parents=True, exist_ok=True)
                bench = _run_one(observed=observed, raw=raw, agent_name=cfg["agent"], seed=seed, out_eval_path=out_eval)
                atk = attacks[f"{tid}:{cfg['view']}"]
                per_run.append(
                    {
                        "config_id": cfg["config_id"],
                        "label": cfg["label"],
                        "track": tid,
                        "seed": seed,
                        "agent": cfg["agent"],
                        "data_view": cfg["view"],
                        "utility": round(bench["utility"], 4),
                        "n_proposals": bench["n_proposals"],
                        "n_accepted": bench["n_accepted"],
                        "leakage_black_box": atk["black_box"]["composite_leakage"],
                        "leakage_white_box": atk["white_box"]["composite_leakage"],
                        "eval_report": str(out_eval),
                    }
                )

    (out_root / "per_run_metrics.json").write_text(
        json.dumps(per_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    agg_rows: List[dict] = []
    for cfg in CONFIGS:
        rows = [r for r in per_run if r["config_id"] == cfg["config_id"]]
        utilities = [r["utility"] for r in rows]
        by_track = {r["track"]: {"black": r["leakage_black_box"], "white": r["leakage_white_box"]} for r in rows}
        black_vals = [v["black"] for _, v in sorted(by_track.items())]
        white_vals = [v["white"] for _, v in sorted(by_track.items())]
        agg_rows.append(
            {
                "config_id": cfg["config_id"],
                "label": cfg["label"],
                "agent": cfg["agent"],
                "data_view": cfg["view"],
                "utility_mean": round(statistics.mean(utilities), 4),
                "utility_std": round(statistics.stdev(utilities), 4) if len(utilities) > 1 else 0.0,
                "leakage_black_box": round(statistics.mean(black_vals), 4) if black_vals else 0.0,
                "leakage_white_box": round(statistics.mean(white_vals), 4) if white_vals else 0.0,
                "n_runs": len(utilities),
            }
        )

    csv_path = out_root / "main_results.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "config_id",
                "label",
                "agent",
                "data_view",
                "utility_mean",
                "utility_std",
                "leakage_black_box",
                "leakage_white_box",
                "n_runs",
            ],
        )
        writer.writeheader()
        for row in agg_rows:
            writer.writerow(row)

    md_path = out_root / "main_results.md"
    lines = [
        "# Oral Main Results (vNext, EXP-022)",
        "",
        "| Config | Agent | Data View | Utility (mean±std) | Leakage Black-Box | Leakage White-Box |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in agg_rows:
        lines.append(
            "| {label} | `{agent}` | `{data_view}` | {mu} ± {sd} | {lb} | {lw} |".format(
                label=row["label"],
                agent=row["agent"],
                data_view=row["data_view"],
                mu=_fmt(row["utility_mean"]),
                sd=_fmt(row["utility_std"]),
                lb=_fmt(row["leakage_black_box"]),
                lw=_fmt(row["leakage_white_box"]),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    by_cfg = {r["config_id"]: r for r in agg_rows}
    main_cfg = "sealed_frontier"
    raw_cfg = "raw_frontier"
    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "dataset_stats": {
            tid: {
                "n_raw": len(track_data[tid]["raw"]),
                "n_sealed": len(track_data[tid]["sealed"]),
            }
            for tid in ["A", "B"]
        },
        "seeds": args.seeds,
        "tracks": ["A", "B"],
        "attack_settings": {"max_observed": int(args.attack_max_observed), "seed": int(args.attack_seed)},
        "main_config": main_cfg,
        "raw_upper_bound": raw_cfg,
        "main_vs_raw": {
            "utility_gap_raw_minus_main": round(
                float(by_cfg[raw_cfg]["utility_mean"]) - float(by_cfg[main_cfg]["utility_mean"]),
                4,
            ),
            "black_box_leakage_gap_raw_minus_main": round(
                float(by_cfg[raw_cfg]["leakage_black_box"]) - float(by_cfg[main_cfg]["leakage_black_box"]),
                4,
            ),
            "white_box_leakage_gap_raw_minus_main": round(
                float(by_cfg[raw_cfg]["leakage_white_box"]) - float(by_cfg[main_cfg]["leakage_white_box"]),
                4,
            ),
        },
    }
    (out_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Run meta (cost/profile)
    ru = resource.getrusage(resource.RUSAGE_SELF)
    meta = {
        "started_ts_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(float(time.time() - t0), 3),
        "maxrss_kb": int(getattr(ru, "ru_maxrss", 0) or 0),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
        "configs": CONFIGS,
        "attack_settings": summary["attack_settings"],
        "dataset_dir": str(dataset_dir),
    }
    (out_root / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {csv_path}")
    print(f"Saved: {md_path}")
    print(f"Saved: {out_root / 'summary.json'}")
    print(f"Saved: {out_root / 'run_meta.json'}")


if __name__ == "__main__":
    main()
