"""Run oral-ready component ablations on a scale (non-toy) dataset (vNext).

This is a dataset-parametric vNext variant of `run_oral_ablations.py`.

Inputs:
- --dataset_dir containing track_{A,B}_{raw,sealed}.jsonl + track_{A,B}_sealed.codebook.json

Outputs (under --output_dir):
- ablation_results.csv
- ablation_results.md
- per_run_metrics.json
- variants/{track}/{variant}.jsonl
- attacks/{track}_{variant}.json
- manual_logging_ablation.json (unless --skip_manual_logging_ablation)
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


def _make_variant_records(variant: str, sealed: List[PaperRecord], raw: List[PaperRecord]) -> List[PaperRecord]:
    raw_by_id = {r.paper_id: r for r in raw}
    out: List[PaperRecord] = []
    for s in sealed:
        r = raw_by_id.get(s.paper_id)
        row = _clone_record(s)
        if r is None:
            out.append(row)
            continue

        if variant == "full_sealed":
            out.append(row)
            continue

        if variant == "no_lexical_seal":
            row.background = r.background
            row.mechanism = r.mechanism
            row.keywords = list(r.keywords or [])

        if variant == "no_structure_seal":
            row.title = r.title
            row.phase = r.phase
            row.dependencies = list(r.dependencies or [])
            row.venue = r.venue
            row.authors = list(r.authors) if r.authors else None

        if variant == "no_numeric_seal":
            row.experiment = r.experiment
            row.year = r.year
            row.results = r.results

        out.append(row)
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


def _manual_rows(path: Path) -> Dict[str, float]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    total = len(rows)
    manual = [
        r
        for r in rows
        if r.get("reviewer_id") and r.get("reason_tag") and r.get("action") in {"include", "exclude"}
    ]
    return {
        "total_rows": total,
        "manual_rows": len(manual),
        "manual_ratio": round((len(manual) / total), 4) if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scale (vNext) component ablations for oral/paper evidence.")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--output_dir", default="runs/EXP-025")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--attack_max_observed", type=int, default=200)
    parser.add_argument("--attack_seed", type=int, default=42)
    parser.add_argument("--skip_manual_logging_ablation", action="store_true")
    args = parser.parse_args()

    t0 = time.time()
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
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

    variants = ["full_sealed", "no_lexical_seal", "no_structure_seal", "no_numeric_seal"]
    per_run: List[dict] = []
    agg: List[dict] = []

    for variant in variants:
        utilities = []
        leak_black = []
        leak_white = []
        for tid, cfg in tracks.items():
            raw = cfg["raw"]
            sealed = cfg["sealed"]
            var_records = _make_variant_records(variant, sealed, raw)
            var_path = out_root / "variants" / tid / f"{variant}.jsonl"
            var_path.parent.mkdir(parents=True, exist_ok=True)
            save_records(var_records, var_path)

            atk = run_adaptive_attack(
                sealed_path=var_path,
                raw_path=cfg["raw_path"],
                codebook_path=cfg["codebook"],
                max_observed=int(args.attack_max_observed) if int(args.attack_max_observed) > 0 else None,
                seed=int(args.attack_seed),
            )
            leak_black.append(float(atk["black_box"]["composite_leakage"]))
            leak_white.append(float(atk["white_box"]["composite_leakage"]))
            atk_path = out_root / "attacks" / f"{tid}_{variant}.json"
            atk_path.parent.mkdir(parents=True, exist_ok=True)
            atk_path.write_text(json.dumps(atk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            for seed in args.seeds:
                u = _frontier_utility(var_records, raw, seed=int(seed))
                utilities.append(u)
                per_run.append(
                    {
                        "variant": variant,
                        "track": tid,
                        "seed": int(seed),
                        "utility": round(float(u), 4),
                        "leakage_black_box": round(float(atk["black_box"]["composite_leakage"]), 4),
                        "leakage_white_box": round(float(atk["white_box"]["composite_leakage"]), 4),
                    }
                )

        agg.append(
            {
                "variant": variant,
                "utility_mean": round(statistics.mean(utilities), 4),
                "utility_std": round(statistics.stdev(utilities), 4) if len(utilities) > 1 else 0.0,
                "leakage_black_box": round(statistics.mean(leak_black), 4),
                "leakage_white_box": round(statistics.mean(leak_white), 4),
            }
        )

    manual_summary = {}
    if not args.skip_manual_logging_ablation:
        manual_on_dir = out_root / "manual_on"
        manual_off_dir = out_root / "manual_off"
        cmd_base = [sys.executable, "provetok/scripts/run_exp_manual_decisions_offline.py", "--track", "both"]
        repo_root = str(Path(__file__).resolve().parents[2])

        subprocess.run(
            cmd_base + ["--run_dir", str(manual_on_dir)],
            check=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            cmd_base + ["--run_dir", str(manual_off_dir), "--disable_manual_decisions"],
            check=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        manual_on_log = manual_on_dir / "exports" / "exp-006-manual-decisions" / "public" / "selection_log_extended.jsonl"
        manual_off_log = manual_off_dir / "exports" / "exp-006-manual-decisions" / "public" / "selection_log_extended.jsonl"
        on_stats = _manual_rows(manual_on_log)
        off_stats = _manual_rows(manual_off_log)
        manual_summary = {
            "manual_on": on_stats,
            "manual_off": off_stats,
            "auditability_gap_manual_ratio": round(on_stats["manual_ratio"] - off_stats["manual_ratio"], 4),
        }

        (out_root / "manual_logging_ablation.json").write_text(
            json.dumps(manual_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    (out_root / "per_run_metrics.json").write_text(
        json.dumps(per_run, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    csv_path = out_root / "ablation_results.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "utility_mean",
                "utility_std",
                "leakage_black_box",
                "leakage_white_box",
            ],
        )
        w.writeheader()
        for row in agg:
            w.writerow(row)

    md_lines = [
        "# Oral Ablations (vNext, EXP-025)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- seeds: `{args.seeds}`",
        f"- attack_max_observed: `{args.attack_max_observed}`",
        "",
        "| Variant | Utility (mean±std) | Leakage Black-Box | Leakage White-Box |",
        "|---|---:|---:|---:|",
    ]
    for row in agg:
        md_lines.append(
            "| `{v}` | {u:.4f} ± {s:.4f} | {lb:.4f} | {lw:.4f} |".format(
                v=row["variant"],
                u=row["utility_mean"],
                s=row["utility_std"],
                lb=row["leakage_black_box"],
                lw=row["leakage_white_box"],
            )
        )

    if manual_summary:
        on_stats = manual_summary["manual_on"]
        off_stats = manual_summary["manual_off"]
        md_lines.extend(
            [
                "",
                "## Manual Logging Ablation",
                "",
                f"- manual_on ratio: `{on_stats['manual_ratio']}` ({on_stats['manual_rows']}/{on_stats['total_rows']})",
                f"- manual_off ratio: `{off_stats['manual_ratio']}` ({off_stats['manual_rows']}/{off_stats['total_rows']})",
                f"- auditability gap: `{manual_summary['auditability_gap_manual_ratio']}`",
            ]
        )

    (out_root / "ablation_results.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

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
        "attack_settings": {"max_observed": int(args.attack_max_observed), "seed": int(args.attack_seed)},
        "variants": variants,
        "manual_logging_ablation": bool(manual_summary),
    }
    (out_root / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {csv_path}")
    print(f"Saved: {out_root / 'ablation_results.md'}")


if __name__ == "__main__":
    main()

