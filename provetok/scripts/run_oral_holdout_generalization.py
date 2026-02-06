"""Run external holdout generalization experiment (EXP-019)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from provetok.agents.base import FrontierSynthesisAgent, run_agent_loop
from provetok.data.schema import PaperRecord, load_records, save_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer
from run_oral_adaptive_attack import run_adaptive_attack


TRACKS = {
    "A": {
        "sealed": Path("provetok/data/sealed/micro_history_a.sealed.jsonl"),
        "raw": Path("provetok/data/raw/micro_history_a.jsonl"),
        "codebook": Path("provetok/data/sealed/micro_history_a.sealed.codebook.json"),
    },
    "B": {
        "sealed": Path("provetok/data/sealed/micro_history_b.sealed.jsonl"),
        "raw": Path("provetok/data/raw/micro_history_b.jsonl"),
        "codebook": Path("provetok/data/sealed/micro_history_b.sealed.codebook.json"),
    },
}


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


def _run_utility(observed_path: Path, raw_path: Path, seeds: List[int]) -> List[float]:
    observed = load_records(observed_path)
    raw = load_records(raw_path)
    out = []
    for seed in seeds:
        env = BenchmarkEnvironment(
            sealed_records=observed,
            real_records=raw,
            budget=max(20, len(raw) + 3),
            fast_mode=True,
        )
        trace = run_agent_loop(FrontierSynthesisAgent(seed=seed), env, max_cycles=50)
        rub = AutoRubricScorer().score_run(trace, raw)
        out.append(float(rub.get("total", 0.0)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXP-019 external holdout generalization.")
    parser.add_argument("--output_dir", default="runs/EXP-019")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--quantile", type=float, default=0.7, help="year quantile boundary for holdout")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_track = {}
    trend_flags = []
    for track, cfg in TRACKS.items():
        raw = load_records(cfg["raw"])
        sealed = load_records(cfg["sealed"])
        ids = _holdout_ids(raw, quantile=args.quantile)
        raw_h = _subset(raw, ids)
        sealed_h = _subset(sealed, ids)

        raw_path = out_dir / f"holdout_{track}_raw.jsonl"
        sealed_path = out_dir / f"holdout_{track}_sealed.jsonl"
        save_records(raw_h, raw_path)
        save_records(sealed_h, sealed_path)

        util_raw = _run_utility(raw_path, raw_path, args.seeds)
        util_sealed = _run_utility(sealed_path, raw_path, args.seeds)

        atk_raw = run_adaptive_attack(raw_path, raw_path, None)
        atk_sealed = run_adaptive_attack(sealed_path, raw_path, cfg["codebook"])

        bb_raw = float(atk_raw["black_box"]["composite_leakage"])
        bb_sealed = float(atk_sealed["black_box"]["composite_leakage"])
        trend_flags.append(bb_sealed < bb_raw)

        per_track[track] = {
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
            "black_box_trend_holds": bool(bb_sealed < bb_raw),
        }

    summary = {
        "quantile": args.quantile,
        "seeds": args.seeds,
        "tracks": per_track,
        "overall": {
            "black_box_trend_holds_all_tracks": bool(all(trend_flags)),
            "avg_utility_retention": round(
                statistics.mean([v["utility_retention"] for v in per_track.values()]), 4
            )
            if per_track
            else 0.0,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Holdout Generalization (EXP-019)",
        "",
        "| Track | Holdout N | Utility Sealed | Utility Raw | Utility Retention | BB Leak Sealed | BB Leak Raw | BB Trend Holds |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for t in sorted(per_track):
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

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
