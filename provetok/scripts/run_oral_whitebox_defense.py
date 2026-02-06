"""Run white-box robustness enhancement experiment (EXP-016).

Goal:
- Introduce a deterministic defense transform on sealed records.
- Verify white-box leakage improves vs raw on both tracks.
- Report utility trade-off with the frontier agent.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List

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


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _apply_whitebox_defense(records: List[PaperRecord]) -> List[PaperRecord]:
    """Strong redaction defense to reduce recoverable lexical signal."""
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.background = "Sealed abstract: methodological content redacted for white-box robustness."
        d.mechanism = "Sealed mechanism: key lexical anchors removed in public release."
        d.experiment = "Sealed evaluation: experiment details redacted in this release."
        d.keywords = []
        out.append(d)
    return out


def _run_frontier_utility(observed_path: Path, raw_path: Path, seed: int) -> float:
    observed = load_records(observed_path)
    raw = load_records(raw_path)
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
    parser = argparse.ArgumentParser(description="Run EXP-016 white-box defense experiment.")
    parser.add_argument("--output_dir", default="runs/EXP-016")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_track: Dict[str, Dict[str, float]] = {}
    utility_rows: List[dict] = []
    leakage_pass = []

    for track_id, paths in TRACKS.items():
        sealed = load_records(paths["sealed"])
        defended = _apply_whitebox_defense(sealed)
        defended_path = out_dir / f"defended_{track_id}.jsonl"
        save_records(defended, defended_path)

        attack_def = run_adaptive_attack(defended_path, paths["raw"], paths["codebook"])
        attack_raw = run_adaptive_attack(paths["raw"], paths["raw"], None)

        util_def = []
        util_raw = []
        for seed in args.seeds:
            u_def = _run_frontier_utility(defended_path, paths["raw"], seed=seed)
            u_raw = _run_frontier_utility(paths["raw"], paths["raw"], seed=seed)
            util_def.append(u_def)
            util_raw.append(u_raw)
            utility_rows.append(
                {
                    "track": track_id,
                    "seed": seed,
                    "utility_defended": round(u_def, 4),
                    "utility_raw": round(u_raw, 4),
                }
            )

        wb_def = float(attack_def["white_box"]["composite_leakage"])
        wb_raw = float(attack_raw["white_box"]["composite_leakage"])
        leakage_pass.append(wb_def < wb_raw)

        per_track[track_id] = {
            "white_box_leakage_defended": round(wb_def, 4),
            "white_box_leakage_raw": round(wb_raw, 4),
            "white_box_delta_defended_minus_raw": round(wb_def - wb_raw, 4),
            "black_box_leakage_defended": round(float(attack_def["black_box"]["composite_leakage"]), 4),
            "black_box_leakage_raw": round(float(attack_raw["black_box"]["composite_leakage"]), 4),
            "utility_mean_defended": round(statistics.mean(util_def), 4),
            "utility_mean_raw": round(statistics.mean(util_raw), 4),
            "utility_retention_defended_vs_raw": round(
                statistics.mean(util_def) / statistics.mean(util_raw), 4
            )
            if statistics.mean(util_raw)
            else 0.0,
        }

        (out_dir / f"attack_defended_{track_id}.json").write_text(
            json.dumps(attack_def, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "tracks": per_track,
        "overall": {
            "white_box_improves_all_tracks": bool(all(leakage_pass)),
            "defense": "semantic redaction (background/mechanism/experiment templates + empty keywords)",
            "seeds": args.seeds,
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "per_seed_utility.json").write_text(
        json.dumps(utility_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md = [
        "# White-Box Defense (EXP-016)",
        "",
        "| Track | WB Leakage (Defended) | WB Leakage (Raw) | Delta (Def-Raw) | Utility Defended | Utility Raw | Utility Retention |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for t in sorted(per_track):
        r = per_track[t]
        md.append(
            "| {t} | {wbd:.4f} | {wbr:.4f} | {d:.4f} | {ud:.4f} | {ur:.4f} | {ret:.4f} |".format(
                t=t,
                wbd=r["white_box_leakage_defended"],
                wbr=r["white_box_leakage_raw"],
                d=r["white_box_delta_defended_minus_raw"],
                ud=r["utility_mean_defended"],
                ur=r["utility_mean_raw"],
                ret=r["utility_retention_defended_vs_raw"],
            )
        )
    md.extend(
        [
            "",
            "## Verdict",
            f"- white_box_improves_all_tracks: `{summary['overall']['white_box_improves_all_tracks']}`",
            f"- defense: `{summary['overall']['defense']}`",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
