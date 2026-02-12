"""Run white-box defense experiment on a scale (non-toy) dataset (vNext).

This is a dataset-parametric vNext variant of `run_oral_whitebox_defense.py`.

Inputs:
- --dataset_dir containing track_{A,B}_{raw,sealed}.jsonl + track_{A,B}_sealed.codebook.json

Outputs (under --output_dir):
- defended_{A,B}.jsonl
- attack_defended_{A,B}.json
- summary.json
- summary.md
- per_seed_utility.json
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
from typing import Dict, List

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


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _apply_whitebox_defense(records: List[PaperRecord]) -> List[PaperRecord]:
    # Keep consistent with micro EXP-016 for comparability.
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.background = "Sealed abstract: methodological content redacted for white-box robustness."
        d.mechanism = "Sealed mechanism: key lexical anchors removed in public release."
        d.experiment = "Sealed evaluation: experiment details redacted in this release."
        d.keywords = []
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
    parser = argparse.ArgumentParser(description="Run vNext white-box defense experiment on a scale dataset.")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--output_dir", default="runs/EXP-027")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(args.dataset_dir)

    per_track: Dict[str, Dict[str, float]] = {}
    utility_rows: List[dict] = []
    leakage_pass = []

    for tid in ["A", "B"]:
        raw_path = dataset_dir / f"track_{tid}_raw.jsonl"
        sealed_path = dataset_dir / f"track_{tid}_sealed.jsonl"
        cb_path = dataset_dir / f"track_{tid}_sealed.codebook.json"
        codebook = cb_path if cb_path.exists() else None

        raw = load_records(raw_path)
        sealed = load_records(sealed_path)
        defended = _apply_whitebox_defense(sealed)

        defended_path = out_dir / f"defended_{tid}.jsonl"
        save_records(defended, defended_path)

        atk_def = run_adaptive_attack(
            sealed_path=defended_path,
            raw_path=raw_path,
            codebook_path=codebook,
            max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
            seed=int(args.attack_seed),
        )
        atk_raw = run_adaptive_attack(
            sealed_path=raw_path,
            raw_path=raw_path,
            codebook_path=None,
            max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
            seed=int(args.attack_seed),
        )

        util_def = []
        util_raw = []
        for seed in args.seeds:
            u_def = _frontier_utility(defended, raw, seed=int(seed))
            u_raw = _frontier_utility(raw, raw, seed=int(seed))
            util_def.append(u_def)
            util_raw.append(u_raw)
            utility_rows.append(
                {
                    "track": tid,
                    "seed": int(seed),
                    "utility_defended": round(float(u_def), 4),
                    "utility_raw": round(float(u_raw), 4),
                }
            )

        wb_def = float(atk_def["white_box"]["composite_leakage"])
        wb_raw = float(atk_raw["white_box"]["composite_leakage"])
        leakage_pass.append(wb_def < wb_raw)

        per_track[tid] = {
            "white_box_leakage_defended": round(wb_def, 4),
            "white_box_leakage_raw": round(wb_raw, 4),
            "white_box_delta_defended_minus_raw": round(wb_def - wb_raw, 4),
            "black_box_leakage_defended": round(float(atk_def["black_box"]["composite_leakage"]), 4),
            "black_box_leakage_raw": round(float(atk_raw["black_box"]["composite_leakage"]), 4),
            "utility_mean_defended": round(statistics.mean(util_def), 4),
            "utility_mean_raw": round(statistics.mean(util_raw), 4),
            "utility_retention_defended_vs_raw": round(statistics.mean(util_def) / statistics.mean(util_raw), 4)
            if statistics.mean(util_raw)
            else 0.0,
        }

        (out_dir / f"attack_defended_{tid}.json").write_text(
            json.dumps(atk_def, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / f"attack_raw_{tid}.json").write_text(
            json.dumps(atk_raw, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "dataset_dir": str(dataset_dir),
        "tracks": per_track,
        "overall": {
            "white_box_improves_all_tracks": bool(all(leakage_pass)),
            "defense": "semantic redaction (background/mechanism/experiment templates + empty keywords)",
            "seeds": args.seeds,
            "attack_settings": {"max_observed": int(args.attack_max_observed), "seed": int(args.attack_seed)},
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
        "# White-Box Defense (vNext, EXP-027)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- seeds: `{args.seeds}`",
        f"- attack_max_observed: `{args.attack_max_observed}`",
        "",
        "| Track | WB Leakage (Defended) | WB Leakage (Raw) | Delta (Def-Raw) | Utility Defended | Utility Raw | Utility Retention |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for t in ["A", "B"]:
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
        "seeds": args.seeds,
        "attack_settings": summary["overall"]["attack_settings"],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

