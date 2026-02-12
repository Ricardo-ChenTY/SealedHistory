"""Run dynamic time-window evaluation on scale datasets.

This script evaluates utility/leakage on multiple temporal slices:
- historical
- rolling
- recent
"""

from __future__ import annotations

import argparse
import json
import platform
import random
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


def _value_at_quantile(values: List[int], q: float) -> int:
    xs = sorted(int(v) for v in values)
    if not xs:
        return 0
    idx = min(len(xs) - 1, max(0, int(round(float(q) * (len(xs) - 1)))))
    return int(xs[idx])


def _window_ids(raw: List[PaperRecord], *, quantile_mid: float, quantile_recent: float) -> Dict[str, Set[str]]:
    years = [int(r.year) for r in raw if r.year is not None]
    if years:
        y_mid = _value_at_quantile(years, quantile_mid)
        y_recent = _value_at_quantile(years, quantile_recent)
        out = {
            "historical": {r.paper_id for r in raw if r.paper_id and r.year is not None and int(r.year) < y_mid},
            "rolling": {r.paper_id for r in raw if r.paper_id and r.year is not None and y_mid <= int(r.year) < y_recent},
            "recent": {r.paper_id for r in raw if r.paper_id and r.year is not None and int(r.year) >= y_recent},
        }
        return out

    ordered = sorted(raw, key=lambda r: str(r.paper_id or ""))
    n = len(ordered)
    cut_mid = int(round(n * float(quantile_mid)))
    cut_recent = int(round(n * float(quantile_recent)))
    out = {
        "historical": {r.paper_id for r in ordered[:cut_mid] if r.paper_id},
        "rolling": {r.paper_id for r in ordered[cut_mid:cut_recent] if r.paper_id},
        "recent": {r.paper_id for r in ordered[cut_recent:] if r.paper_id},
    }
    return out


def _subset(records: List[PaperRecord], ids: Set[str]) -> List[PaperRecord]:
    return [r for r in records if r.paper_id in ids]


def _subsample(records: List[PaperRecord], *, max_n: int, seed: int) -> List[PaperRecord]:
    if max_n <= 0 or len(records) <= int(max_n):
        return records
    rng = random.Random(int(seed))
    out = list(records)
    rng.shuffle(out)
    return out[: int(max_n)]


def _run_utility(observed: List[PaperRecord], raw: List[PaperRecord], *, seeds: List[int], max_cycles: int) -> List[float]:
    vals: List[float] = []
    for s in seeds:
        env = BenchmarkEnvironment(
            sealed_records=observed,
            real_records=raw,
            budget=max(20, len(raw) + 3),
            fast_mode=True,
        )
        trace = run_agent_loop(FrontierSynthesisAgent(seed=int(s)), env, max_cycles=int(max_cycles))
        rub = AutoRubricScorer().score_run(trace, raw)
        vals.append(float(rub.get("total", 0.0)))
    return vals


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dynamic time-window evaluation.")
    parser.add_argument("--dataset_dir", default="runs/EXP-031/public")
    parser.add_argument("--output_dir", default="runs/EXP-035")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--quantile_mid", type=float, default=0.5)
    parser.add_argument("--quantile_recent", type=float, default=0.8)
    parser.add_argument("--max_records_per_window", type=int, default=240)
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    parser.add_argument("--max_cycles", type=int, default=50)
    args = parser.parse_args()

    t0 = time.time()
    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = out_dir / "window_inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    per_track: Dict[str, Dict[str, dict]] = {}
    for track in ["A", "B"]:
        raw_path = dataset_dir / f"track_{track}_raw.jsonl"
        sealed_path = dataset_dir / f"track_{track}_sealed.jsonl"
        codebook_path = dataset_dir / f"track_{track}_sealed.codebook.json"

        raw = load_records(raw_path)
        sealed = load_records(sealed_path)
        windows = _window_ids(raw, quantile_mid=float(args.quantile_mid), quantile_recent=float(args.quantile_recent))

        per_track[track] = {}
        for wi, window_name in enumerate(["historical", "rolling", "recent"]):
            ids = windows.get(window_name, set())
            raw_w = _subset(raw, ids)
            sealed_w = _subset(sealed, ids)
            raw_w = _subsample(raw_w, max_n=int(args.max_records_per_window), seed=100 + wi)
            sealed_w = _subsample(sealed_w, max_n=int(args.max_records_per_window), seed=200 + wi)

            raw_window_path = inputs_dir / f"{track}_{window_name}_raw.jsonl"
            sealed_window_path = inputs_dir / f"{track}_{window_name}_sealed.jsonl"
            save_records(raw_w, raw_window_path)
            save_records(sealed_w, sealed_window_path)

            utility_raw = _run_utility(raw_w, raw_w, seeds=[int(s) for s in args.seeds], max_cycles=int(args.max_cycles))
            utility_sealed = _run_utility(sealed_w, raw_w, seeds=[int(s) for s in args.seeds], max_cycles=int(args.max_cycles))

            atk_raw = run_adaptive_attack(
                sealed_path=raw_window_path,
                raw_path=raw_window_path,
                codebook_path=None,
                max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
                seed=int(args.attack_seed),
            )
            atk_sealed = run_adaptive_attack(
                sealed_path=sealed_window_path,
                raw_path=raw_window_path,
                codebook_path=codebook_path if codebook_path.exists() else None,
                max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
                seed=int(args.attack_seed),
            )

            mean_raw = statistics.mean(utility_raw) if utility_raw else 0.0
            mean_sealed = statistics.mean(utility_sealed) if utility_sealed else 0.0
            per_track[track][window_name] = {
                "n_records": len(raw_w),
                "utility_raw_mean": round(mean_raw, 4),
                "utility_sealed_mean": round(mean_sealed, 4),
                "utility_retention": round(mean_sealed / mean_raw, 4) if mean_raw else 0.0,
                "black_box_leakage_raw": round(float(atk_raw["black_box"]["composite_leakage"]), 4),
                "black_box_leakage_sealed": round(float(atk_sealed["black_box"]["composite_leakage"]), 4),
                "white_box_leakage_raw": round(float(atk_raw["white_box"]["composite_leakage"]), 4),
                "white_box_leakage_sealed": round(float(atk_sealed["white_box"]["composite_leakage"]), 4),
                "black_box_trend_holds": bool(
                    float(atk_sealed["black_box"]["composite_leakage"]) < float(atk_raw["black_box"]["composite_leakage"])
                ),
            }

    all_ret = []
    all_bb_trend = []
    for t in per_track.values():
        for w in t.values():
            all_ret.append(float(w["utility_retention"]))
            all_bb_trend.append(bool(w["black_box_trend_holds"]))

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "quantiles": {"mid": float(args.quantile_mid), "recent": float(args.quantile_recent)},
        "seeds": [int(s) for s in args.seeds],
        "attack_settings": {"max_observed": int(args.attack_max_observed), "seed": int(args.attack_seed)},
        "per_track": per_track,
        "overall": {
            "avg_utility_retention": round(statistics.mean(all_ret), 4) if all_ret else 0.0,
            "black_box_trend_holds_all_windows": bool(all(all_bb_trend)) if all_bb_trend else False,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Dynamic Time-Window Evaluation (EXP-035)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- quantile_mid: `{args.quantile_mid}`",
        f"- quantile_recent: `{args.quantile_recent}`",
        f"- seeds: `{args.seeds}`",
        "",
        "| Track | Window | N | Utility Sealed | Utility Raw | Retention | BB Sealed | BB Raw | BB Trend Holds |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for track in ["A", "B"]:
        for window in ["historical", "rolling", "recent"]:
            row = per_track.get(track, {}).get(window)
            if not row:
                continue
            md.append(
                "| {} | {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {} |".format(
                    track,
                    window,
                    int(row["n_records"]),
                    float(row["utility_sealed_mean"]),
                    float(row["utility_raw_mean"]),
                    float(row["utility_retention"]),
                    float(row["black_box_leakage_sealed"]),
                    float(row["black_box_leakage_raw"]),
                    "yes" if row["black_box_trend_holds"] else "no",
                )
            )
    md.extend(
        [
            "",
            "## Overall",
            f"- avg_utility_retention: `{summary['overall']['avg_utility_retention']}`",
            f"- black_box_trend_holds_all_windows: `{summary['overall']['black_box_trend_holds_all_windows']}`",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ru = resource.getrusage(resource.RUSAGE_SELF)
    run_meta = {
        "started_ts_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(float(time.time() - t0), 3),
        "maxrss_kb": int(getattr(ru, "ru_maxrss", 0) or 0),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
        "dataset_dir": str(dataset_dir),
        "seeds": [int(s) for s in args.seeds],
        "quantile_mid": float(args.quantile_mid),
        "quantile_recent": float(args.quantile_recent),
        "max_records_per_window": int(args.max_records_per_window),
        "attack_max_observed": int(args.attack_max_observed),
        "attack_seed": int(args.attack_seed),
        "max_cycles": int(args.max_cycles),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

