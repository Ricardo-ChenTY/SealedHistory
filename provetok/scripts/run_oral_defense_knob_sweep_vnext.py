"""Sweep defense strength knobs and output utility-vs-leakage tradeoff curve (vNext).

This is intended to satisfy oral checklist E8/E10 on a scale dataset.

Inputs:
- --dataset_dir containing track_{A,B}_{raw,sealed}.jsonl + track_{A,B}_sealed.codebook.json

Defense levels (increasing strength):
  0: no extra defense (use sealed as-is)
  1: drop keywords
  2: drop keywords + redact background
  3: + redact mechanism
  4: + redact experiment

Outputs (under --output_dir):
- tradeoff_curve.json
- tradeoff_curve.csv
- tradeoff_curve.md
- tradeoff_curve.png
- run_meta.json
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from provetok.agents.base import FrontierSynthesisAgent, run_agent_loop
from provetok.data.schema import PaperRecord, load_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer
from run_oral_adaptive_attack_vnext import run_adaptive_attack


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _apply_defense(records: List[PaperRecord], level: int) -> List[PaperRecord]:
    lvl = int(level)
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        if lvl >= 1:
            d.keywords = []
        if lvl >= 2:
            d.background = "Redacted background (defense knob >=2)."
        if lvl >= 3:
            d.mechanism = "Redacted mechanism (defense knob >=3)."
        if lvl >= 4:
            d.experiment = "Redacted experiment (defense knob >=4)."
        out.append(d)
    return out


def _frontier_utility(observed: List[PaperRecord], raw: List[PaperRecord], seed: int) -> float:
    env = BenchmarkEnvironment(
        sealed_records=observed,
        real_records=raw,
        budget=max(40, len(raw) + 4),
        fast_mode=True,
    )
    trace = run_agent_loop(FrontierSynthesisAgent(seed=seed), env, max_cycles=80)
    rubric = AutoRubricScorer().score_run(trace, raw)
    return float(rubric.get("total", 0.0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vNext defense knob sweep (utility vs leakage curve).")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--output_dir", default="runs/EXP-023")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_dir = Path(args.dataset_dir)

    tracks = {}
    for tid in ["A", "B"]:
        raw_path = dataset_dir / f"track_{tid}_raw.jsonl"
        sealed_path = dataset_dir / f"track_{tid}_sealed.jsonl"
        cb_path = dataset_dir / f"track_{tid}_sealed.codebook.json"
        tracks[tid] = {
            "raw_path": raw_path,
            "sealed_path": sealed_path,
            "codebook": cb_path if cb_path.exists() else None,
            "raw": load_records(raw_path),
            "sealed": load_records(sealed_path),
        }

    # Precompute raw baseline utility per track.
    raw_util = {}
    for tid in ["A", "B"]:
        vals = [_frontier_utility(tracks[tid]["raw"], tracks[tid]["raw"], seed=s) for s in args.seeds]
        raw_util[tid] = statistics.mean(vals) if vals else 0.0

    points: List[dict] = []
    levels = [0, 1, 2, 3, 4]
    for lvl in levels:
        per_track = {}
        for tid in ["A", "B"]:
            raw = tracks[tid]["raw"]
            sealed = tracks[tid]["sealed"]
            defended = _apply_defense(sealed, level=lvl)

            # Utility
            u_vals = [_frontier_utility(defended, raw, seed=s) for s in args.seeds]
            u_mean = statistics.mean(u_vals) if u_vals else 0.0
            u_ret = (u_mean / raw_util[tid]) if raw_util[tid] else 0.0

            # Leakage (offline)
            tmp_path = out_dir / f"defense_level_{lvl}_{tid}.jsonl"
            from provetok.data.schema import save_records

            save_records(defended, tmp_path)

            atk = run_adaptive_attack(
                sealed_path=tmp_path,
                raw_path=tracks[tid]["raw_path"],
                codebook_path=tracks[tid]["codebook"],
                max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
                seed=int(args.attack_seed),
            )

            per_track[tid] = {
                "utility_mean": round(u_mean, 4),
                "utility_retention_vs_raw": round(u_ret, 4),
                "black_box_leakage": atk["black_box"]["composite_leakage"],
                "white_box_leakage": atk["white_box"]["composite_leakage"],
            }

        overall = {
            "utility_retention_vs_raw_avg": round(
                statistics.mean([per_track[t]["utility_retention_vs_raw"] for t in ["A", "B"]]), 4
            ),
            "black_box_leakage_avg": round(statistics.mean([per_track[t]["black_box_leakage"] for t in ["A", "B"]]), 4),
            "white_box_leakage_avg": round(statistics.mean([per_track[t]["white_box_leakage"] for t in ["A", "B"]]), 4),
        }
        points.append({"level": lvl, "per_track": per_track, "overall": overall})

    curve = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "seeds": args.seeds,
        "tracks": ["A", "B"],
        "attack_settings": {"max_observed": int(args.attack_max_observed), "seed": int(args.attack_seed)},
        "levels": points,
    }

    (out_dir / "tradeoff_curve.json").write_text(json.dumps(curve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # CSV flatten
    csv_path = out_dir / "tradeoff_curve.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "level",
                "utility_retention_vs_raw_avg",
                "black_box_leakage_avg",
                "white_box_leakage_avg",
            ],
        )
        w.writeheader()
        for p in points:
            o = p["overall"]
            w.writerow(
                {
                    "level": p["level"],
                    "utility_retention_vs_raw_avg": o["utility_retention_vs_raw_avg"],
                    "black_box_leakage_avg": o["black_box_leakage_avg"],
                    "white_box_leakage_avg": o["white_box_leakage_avg"],
                }
            )

    # Plot (slide-ready)
    xs = [p["overall"]["utility_retention_vs_raw_avg"] for p in points]
    bb = [p["overall"]["black_box_leakage_avg"] for p in points]
    wb = [p["overall"]["white_box_leakage_avg"] for p in points]
    levels_s = [str(p["level"]) for p in points]

    fig = plt.figure(figsize=(7.2, 4.2), dpi=200)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, bb, marker="o", label="black-box leakage")
    ax.plot(xs, wb, marker="s", label="white-box leakage")
    for i, lab in enumerate(levels_s):
        ax.annotate(lab, (xs[i], bb[i]), textcoords="offset points", xytext=(5, 4), fontsize=8)
    ax.set_xlabel("Utility retention vs raw (avg over tracks)")
    ax.set_ylabel("Composite leakage (avg over tracks)")
    ax.set_title("Defense Strength Knob Sweep (vNext)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    (out_dir / "tradeoff_curve.png").write_bytes(b"")  # placeholder to ensure path exists
    fig.savefig(out_dir / "tradeoff_curve.png")
    plt.close(fig)

    md = [
        "# Defense Knob Sweep (vNext, EXP-023)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- seeds: `{args.seeds}`",
        f"- attack_max_observed: `{args.attack_max_observed}`",
        "",
        "| Level | Utility Retention (avg) | Leakage Black-Box (avg) | Leakage White-Box (avg) |",
        "|---:|---:|---:|---:|",
    ]
    for p in points:
        o = p["overall"]
        md.append(
            "| {lvl} | {u:.4f} | {bb:.4f} | {wb:.4f} |".format(
                lvl=int(p["level"]),
                u=float(o["utility_retention_vs_raw_avg"]),
                bb=float(o["black_box_leakage_avg"]),
                wb=float(o["white_box_leakage_avg"]),
            )
        )
    md.extend(["", f"Plot: `{out_dir / 'tradeoff_curve.png'}`"])
    (out_dir / "tradeoff_curve.md").write_text("\n".join(md) + "\n", encoding="utf-8")

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
        "levels": levels,
        "attack_settings": curve["attack_settings"],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'tradeoff_curve.json'}")
    print(f"Saved: {out_dir / 'tradeoff_curve.png'}")


if __name__ == "__main__":
    main()

