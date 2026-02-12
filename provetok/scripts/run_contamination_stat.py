"""Run contamination statistics (ConStat-style proxy) on per-run metrics.

This script quantifies whether utility gains co-move with leakage gains by
comparing paired runs (same track/seed) between two configs.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _bootstrap_ci(values: List[float], *, n_boot: int, seed: int) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(int(seed))
    n = len(values)
    means: List[float] = []
    for _ in range(int(n_boot)):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.mean(sample))
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return float(lo), float(hi)


def _contamination_score(delta_utility: float, delta_leakage: float, *, scale: float) -> float:
    u = max(0.0, float(delta_utility))
    l = max(0.0, float(delta_leakage))
    u_norm = u / (u + float(scale)) if u > 0 else 0.0
    l_norm = l / (l + float(scale)) if l > 0 else 0.0
    return float(u_norm * l_norm)


def _pair_rows(rows: List[dict], *, left: str, right: str) -> List[dict]:
    left_map: Dict[Tuple[str, int], dict] = {}
    right_map: Dict[Tuple[str, int], dict] = {}

    for row in rows:
        cfg = str(row.get("config_id") or "")
        track = str(row.get("track") or "")
        seed = int(row.get("seed") or 0)
        key = (track, seed)
        if cfg == left:
            left_map[key] = row
        if cfg == right:
            right_map[key] = row

    paired: List[dict] = []
    for key in sorted(left_map.keys()):
        if key not in right_map:
            continue
        l = left_map[key]
        r = right_map[key]
        paired.append(
            {
                "track": key[0],
                "seed": key[1],
                "left_utility": float(l.get("utility") or 0.0),
                "right_utility": float(r.get("utility") or 0.0),
                "left_leakage_black_box": float(l.get("leakage_black_box") or 0.0),
                "right_leakage_black_box": float(r.get("leakage_black_box") or 0.0),
            }
        )
    return paired


def _summarize_pairs(
    pairs: List[dict],
    *,
    utility_penalty_lambda: float,
    score_scale: float,
    n_boot: int,
    seed: int,
) -> dict:
    deltas_utility = [float(p["left_utility"] - p["right_utility"]) for p in pairs]
    deltas_leakage = [float(p["left_leakage_black_box"] - p["right_leakage_black_box"]) for p in pairs]
    scores = [
        _contamination_score(du, dl, scale=score_scale)
        for du, dl in zip(deltas_utility, deltas_leakage)
    ]

    left_corrected = [
        float(p["left_utility"]) - float(utility_penalty_lambda) * float(p["left_leakage_black_box"])
        for p in pairs
    ]
    right_corrected = [
        float(p["right_utility"]) - float(utility_penalty_lambda) * float(p["right_leakage_black_box"])
        for p in pairs
    ]
    corrected_gap = [l - r for l, r in zip(left_corrected, right_corrected)]

    ci_score = _bootstrap_ci(scores, n_boot=n_boot, seed=seed)
    ci_gap = _bootstrap_ci(corrected_gap, n_boot=n_boot, seed=seed + 1)

    return {
        "n_pairs": len(pairs),
        "mean_delta_utility_left_minus_right": round(statistics.mean(deltas_utility), 4) if deltas_utility else 0.0,
        "mean_delta_leakage_left_minus_right": round(statistics.mean(deltas_leakage), 4) if deltas_leakage else 0.0,
        "mean_contamination_score": round(statistics.mean(scores), 4) if scores else 0.0,
        "contamination_score_ci95": [round(ci_score[0], 4), round(ci_score[1], 4)],
        "mean_corrected_utility_gap_left_minus_right": round(statistics.mean(corrected_gap), 4) if corrected_gap else 0.0,
        "corrected_utility_gap_ci95": [round(ci_gap[0], 4), round(ci_gap[1], 4)],
        "high_risk_fraction": round(sum(1 for x in scores if x >= 0.5) / len(scores), 4) if scores else 0.0,
        "utility_penalty_lambda": float(utility_penalty_lambda),
        "score_scale": float(score_scale),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run contamination statistics from per-run metrics.")
    parser.add_argument("--input", default="runs/EXP-022/per_run_metrics.json")
    parser.add_argument("--output_dir", default="runs/EXP-034")
    parser.add_argument("--left_config", default="raw_frontier")
    parser.add_argument("--right_config", default="sealed_frontier")
    parser.add_argument("--utility_penalty_lambda", type=float, default=0.2)
    parser.add_argument("--score_scale", type=float, default=0.05)
    parser.add_argument("--n_boot", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    src = Path(args.input)
    rows = json.loads(src.read_text(encoding="utf-8"))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = _pair_rows(rows, left=str(args.left_config), right=str(args.right_config))
    by_track: Dict[str, List[dict]] = {}
    for p in pairs:
        by_track.setdefault(str(p["track"]), []).append(p)

    per_track = {
        t: _summarize_pairs(
            ps,
            utility_penalty_lambda=float(args.utility_penalty_lambda),
            score_scale=float(args.score_scale),
            n_boot=int(args.n_boot),
            seed=int(args.seed) + i * 100,
        )
        for i, (t, ps) in enumerate(sorted(by_track.items()))
    }
    overall = _summarize_pairs(
        pairs,
        utility_penalty_lambda=float(args.utility_penalty_lambda),
        score_scale=float(args.score_scale),
        n_boot=int(args.n_boot),
        seed=int(args.seed),
    )

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": str(src),
        "left_config": str(args.left_config),
        "right_config": str(args.right_config),
        "overall": overall,
        "per_track": per_track,
        "paired_rows_preview": pairs[:20],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Contamination Statistics (EXP-034)",
        "",
        f"- input: `{src}`",
        f"- left_config: `{args.left_config}`",
        f"- right_config: `{args.right_config}`",
        "",
        "## Overall",
        "",
        f"- n_pairs: `{overall['n_pairs']}`",
        f"- mean_delta_utility_left_minus_right: `{overall['mean_delta_utility_left_minus_right']}`",
        f"- mean_delta_leakage_left_minus_right: `{overall['mean_delta_leakage_left_minus_right']}`",
        f"- mean_contamination_score: `{overall['mean_contamination_score']}`",
        f"- contamination_score_ci95: `{overall['contamination_score_ci95']}`",
        f"- mean_corrected_utility_gap_left_minus_right: `{overall['mean_corrected_utility_gap_left_minus_right']}`",
        f"- corrected_utility_gap_ci95: `{overall['corrected_utility_gap_ci95']}`",
        f"- high_risk_fraction: `{overall['high_risk_fraction']}`",
        "",
        "## Per-Track",
        "",
        "| Track | n_pairs | Mean Score | Score CI95 | Corrected Utility Gap |",
        "|---|---:|---:|---:|---:|",
    ]
    for t, r in sorted(per_track.items()):
        md.append(
            "| {} | {} | {:.4f} | [{:.4f}, {:.4f}] | {:.4f} |".format(
                t,
                int(r["n_pairs"]),
                float(r["mean_contamination_score"]),
                float(r["contamination_score_ci95"][0]),
                float(r["contamination_score_ci95"][1]),
                float(r["mean_corrected_utility_gap_left_minus_right"]),
            )
        )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    run_meta = {
        "started_ts_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(float(time.time() - t0), 3),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
        "input": str(src),
        "left_config": str(args.left_config),
        "right_config": str(args.right_config),
        "utility_penalty_lambda": float(args.utility_penalty_lambda),
        "score_scale": float(args.score_scale),
        "n_boot": int(args.n_boot),
        "seed": int(args.seed),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

