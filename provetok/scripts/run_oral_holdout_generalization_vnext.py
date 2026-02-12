"""Run external holdout generalization experiment on a scale dataset (vNext).

This is a dataset-parametric vNext variant of `run_oral_holdout_generalization.py` that uses:
- --dataset_dir for track_{A,B}_{raw,sealed}.jsonl + codebooks
- `run_oral_adaptive_attack_vnext` with optional subsampling for attack metrics

Outputs (under --output_dir):
- holdout_{A,B}_{raw,sealed}.jsonl
- summary.json
- summary.md
- run_meta.json
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from provetok.agents.base import FrontierSynthesisAgent, run_agent_loop
from provetok.data.schema import PaperRecord, load_records, save_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer
from run_oral_adaptive_attack_vnext import run_adaptive_attack


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _holdout_ids(raw_records: List[PaperRecord], quantile: float = 0.7) -> Set[str]:
    years = sorted([int(r.year) for r in raw_records if r.year is not None])
    if not years:
        n = len(raw_records)
        return {r.paper_id for r in raw_records[int(n * quantile) :] if r.paper_id}
    idx = min(len(years) - 1, max(0, int(len(years) * quantile)))
    year_cut = years[idx]
    return {r.paper_id for r in raw_records if (r.year is not None and int(r.year) >= year_cut)}


def _subset(records: List[PaperRecord], ids: Set[str]) -> List[PaperRecord]:
    return [r for r in records if r.paper_id in ids]


def _run_utility(observed: List[PaperRecord], raw: List[PaperRecord], seeds: List[int]) -> List[float]:
    out = []
    for seed in seeds:
        env = BenchmarkEnvironment(
            sealed_records=observed,
            real_records=raw,
            budget=max(20, len(raw) + 3),
            fast_mode=True,
        )
        trace = run_agent_loop(FrontierSynthesisAgent(seed=int(seed)), env, max_cycles=50)
        rub = AutoRubricScorer().score_run(trace, raw)
        out.append(float(rub.get("total", 0.0)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vNext external holdout generalization on a scale dataset.")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--output_dir", default="runs/EXP-030")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--quantile", type=float, default=0.7, help="year quantile boundary for holdout")
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(args.dataset_dir)

    per_track = {}
    trend_flags = []

    max_obs = int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None

    for tid in ["A", "B"]:
        raw_path = dataset_dir / f"track_{tid}_raw.jsonl"
        sealed_path = dataset_dir / f"track_{tid}_sealed.jsonl"
        cb_path = dataset_dir / f"track_{tid}_sealed.codebook.json"
        codebook = cb_path if cb_path.exists() else None

        raw = load_records(raw_path)
        sealed = load_records(sealed_path)

        ids = _holdout_ids(raw, quantile=float(args.quantile))
        raw_h = _subset(raw, ids)
        sealed_h = _subset(sealed, ids)

        raw_h_path = out_dir / f"holdout_{tid}_raw.jsonl"
        sealed_h_path = out_dir / f"holdout_{tid}_sealed.jsonl"
        save_records(raw_h, raw_h_path)
        save_records(sealed_h, sealed_h_path)

        util_raw = _run_utility(raw_h, raw_h, args.seeds)
        util_sealed = _run_utility(sealed_h, raw_h, args.seeds)

        atk_raw = run_adaptive_attack(
            sealed_path=raw_h_path,
            raw_path=raw_h_path,
            codebook_path=None,
            max_observed=max_obs,
            seed=int(args.attack_seed),
        )
        atk_sealed = run_adaptive_attack(
            sealed_path=sealed_h_path,
            raw_path=raw_h_path,
            codebook_path=codebook,
            max_observed=max_obs,
            seed=int(args.attack_seed),
        )

        bb_raw = float(atk_raw["black_box"]["composite_leakage"])
        bb_sealed = float(atk_sealed["black_box"]["composite_leakage"])
        trend = bool(bb_sealed < bb_raw)
        trend_flags.append(trend)

        per_track[tid] = {
            "n_holdout": len(raw_h),
            "utility_raw_mean": round(statistics.mean(util_raw), 4),
            "utility_sealed_mean": round(statistics.mean(util_sealed), 4),
            "utility_retention": round(statistics.mean(util_sealed) / statistics.mean(util_raw), 4)
            if statistics.mean(util_raw)
            else 0.0,
            "black_box_leakage_raw": round(bb_raw, 4),
            "black_box_leakage_sealed": round(bb_sealed, 4),
            "white_box_leakage_raw": round(float(atk_raw["white_box"]["composite_leakage"]), 4),
            "white_box_leakage_sealed": round(float(atk_sealed["white_box"]["composite_leakage"]), 4),
            "black_box_trend_holds": trend,
        }

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "quantile": float(args.quantile),
        "seeds": args.seeds,
        "attack_settings": {"max_observed": max_obs, "seed": int(args.attack_seed)},
        "tracks": per_track,
        "overall": {
            "black_box_trend_holds_all_tracks": bool(all(trend_flags)),
            "avg_utility_retention": round(statistics.mean([v["utility_retention"] for v in per_track.values()]), 4)
            if per_track
            else 0.0,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Holdout Generalization (vNext, EXP-030)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- quantile: `{args.quantile}`",
        f"- seeds: `{args.seeds}`",
        f"- attack_max_observed: `{max_obs}`",
        "",
        "| Track | Holdout N | Utility Sealed | Utility Raw | Utility Retention | BB Leak Sealed | BB Leak Raw | BB Trend Holds |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for t in ["A", "B"]:
        r = per_track[t]
        md.append(
            "| {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {} |".format(
                t,
                r["n_holdout"],
                r["utility_sealed_mean"],
                r["utility_raw_mean"],
                r["utility_retention"],
                r["black_box_leakage_sealed"],
                r["black_box_leakage_raw"],
                "yes" if r["black_box_trend_holds"] else "no",
            )
        )
    md.extend(
        [
            "",
            "## Overall",
            f"- black_box_trend_holds_all_tracks: `{summary['overall']['black_box_trend_holds_all_tracks']}`",
            f"- avg_utility_retention: `{summary['overall']['avg_utility_retention']}`",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ru = resource.getrusage(resource.RUSAGE_SELF)
    meta = {
        "started_ts_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(float(time.time() - t0), 3),
        "maxrss_kb": int(getattr(ru, "ru_maxrss", 0) or 0),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
        "dataset_dir": str(dataset_dir),
        "quantile": float(args.quantile),
        "seeds": args.seeds,
        "attack_settings": summary["attack_settings"],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

