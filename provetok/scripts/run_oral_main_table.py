"""Run oral-ready main results table.

Outputs:
- runs/EXP-011/main_results.csv
- runs/EXP-011/main_results.md
- runs/EXP-011/per_run_metrics.json
- runs/EXP-011/summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from provetok.agents.base import CopyLastAgent, DependencyAwareAgent, FrontierSynthesisAgent, RandomAgent, run_agent_loop
from provetok.data.schema import load_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer, ParetoPoint, save_eval_report
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

CONFIGS = [
    {
        "config_id": "sealed_frontier",
        "label": "SealedHistory (main)",
        "agent": "frontier",
        "data_view": "sealed",
    },
    {
        "config_id": "raw_frontier",
        "label": "Raw (upper bound)",
        "agent": "frontier",
        "data_view": "raw",
    },
    {
        "config_id": "sealed_dependency",
        "label": "Strong baseline #1 (dependency)",
        "agent": "dependency",
        "data_view": "sealed",
    },
    {
        "config_id": "sealed_copylast",
        "label": "Strong baseline #2 (copylast)",
        "agent": "copylast",
        "data_view": "sealed",
    },
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


def _run_benchmark_once(
    observed_path: Path,
    raw_path: Path,
    agent_name: str,
    seed: int,
    out_eval_path: Path,
) -> dict:
    observed = load_records(observed_path)
    raw = load_records(raw_path)

    env = BenchmarkEnvironment(
        sealed_records=observed,
        real_records=raw,
        budget=max(40, len(raw) + 4),
        fast_mode=True,
    )
    agent = _agent_by_name(agent_name, seed=seed)
    trace = run_agent_loop(agent, env, max_cycles=80)

    scorer = AutoRubricScorer()
    rubric = scorer.score_run(trace, raw)
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


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run oral main-table experiments.")
    parser.add_argument("--output_dir", default="runs/EXP-011")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    args = parser.parse_args()

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    attack_cache: Dict[str, dict] = {}
    for track_id, paths in TRACKS.items():
        sealed_attack = run_adaptive_attack(paths["sealed"], paths["raw"], paths["codebook"])
        raw_attack = run_adaptive_attack(paths["raw"], paths["raw"], None)
        (out_root / "attacks").mkdir(parents=True, exist_ok=True)
        (out_root / "attacks" / f"{track_id}_sealed.json").write_text(
            json.dumps(sealed_attack, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_root / "attacks" / f"{track_id}_raw.json").write_text(
            json.dumps(raw_attack, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        attack_cache[f"{track_id}:sealed"] = sealed_attack
        attack_cache[f"{track_id}:raw"] = raw_attack

    per_run: List[dict] = []
    for cfg in CONFIGS:
        for track_id, paths in TRACKS.items():
            observed_path = paths[cfg["data_view"]]
            raw_path = paths["raw"]
            for seed in args.seeds:
                out_eval = out_root / cfg["config_id"] / track_id / f"seed_{seed}" / "eval_report.json"
                out_eval.parent.mkdir(parents=True, exist_ok=True)
                bench = _run_benchmark_once(
                    observed_path=observed_path,
                    raw_path=raw_path,
                    agent_name=cfg["agent"],
                    seed=seed,
                    out_eval_path=out_eval,
                )
                atk = attack_cache[f"{track_id}:{cfg['data_view']}"]
                per_run.append(
                    {
                        "config_id": cfg["config_id"],
                        "label": cfg["label"],
                        "track": track_id,
                        "seed": seed,
                        "agent": cfg["agent"],
                        "data_view": cfg["data_view"],
                        "utility": round(bench["utility"], 4),
                        "n_proposals": bench["n_proposals"],
                        "n_accepted": bench["n_accepted"],
                        "leakage_black_box": atk["black_box"]["composite_leakage"],
                        "leakage_white_box": atk["white_box"]["composite_leakage"],
                        "eval_report": str(out_eval),
                    }
                )

    agg_rows: List[dict] = []
    for cfg in CONFIGS:
        rows = [r for r in per_run if r["config_id"] == cfg["config_id"]]
        utilities = [r["utility"] for r in rows]
        by_track = {}
        for r in rows:
            by_track[r["track"]] = {
                "black": r["leakage_black_box"],
                "white": r["leakage_white_box"],
            }
        black_vals = [v["black"] for _, v in sorted(by_track.items())]
        white_vals = [v["white"] for _, v in sorted(by_track.items())]
        agg_rows.append(
            {
                "config_id": cfg["config_id"],
                "label": cfg["label"],
                "agent": cfg["agent"],
                "data_view": cfg["data_view"],
                "utility_mean": round(statistics.mean(utilities), 4),
                "utility_std": round(statistics.stdev(utilities), 4) if len(utilities) > 1 else 0.0,
                "leakage_black_box": round(statistics.mean(black_vals), 4),
                "leakage_white_box": round(statistics.mean(white_vals), 4),
                "n_runs": len(utilities),
            }
        )

    per_run_path = out_root / "per_run_metrics.json"
    per_run_path.write_text(json.dumps(per_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        "# Oral Main Results (EXP-011)",
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
    summary = {
        "seeds": args.seeds,
        "tracks": sorted(TRACKS.keys()),
        "main_config": "sealed_frontier",
        "raw_upper_bound": "raw_frontier",
        "main_vs_raw": {
            "utility_gap_raw_minus_main": round(
                by_cfg["raw_frontier"]["utility_mean"] - by_cfg["sealed_frontier"]["utility_mean"],
                4,
            ),
            "black_box_leakage_gap_raw_minus_main": round(
                by_cfg["raw_frontier"]["leakage_black_box"] - by_cfg["sealed_frontier"]["leakage_black_box"],
                4,
            ),
            "white_box_leakage_gap_raw_minus_main": round(
                by_cfg["raw_frontier"]["leakage_white_box"] - by_cfg["sealed_frontier"]["leakage_white_box"],
                4,
            ),
        },
    }
    summary_path = out_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {csv_path}")
    print(f"Saved: {md_path}")
    print(f"Saved: {per_run_path}")
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
