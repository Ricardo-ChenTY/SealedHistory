"""Run oral-ready component ablations.

Ablation axes:
- no_lexical_seal
- no_structure_seal
- no_numeric_seal
- manual decision logging on/off (auditability axis)
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
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


def _run_frontier_utility(observed_path: Path, raw_path: Path, seed: int) -> float:
    observed = load_records(observed_path)
    raw = load_records(raw_path)
    env = BenchmarkEnvironment(
        sealed_records=observed,
        real_records=raw,
        budget=max(40, len(raw) + 4),
        fast_mode=True,
    )
    agent = FrontierSynthesisAgent(seed=seed)
    trace = run_agent_loop(agent, env, max_cycles=80)
    scorer = AutoRubricScorer()
    rubric = scorer.score_run(trace, raw)
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
    parser = argparse.ArgumentParser(description="Run component ablations for oral evidence.")
    parser.add_argument("--output_dir", default="runs/EXP-013")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    args = parser.parse_args()

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    variants = ["full_sealed", "no_lexical_seal", "no_structure_seal", "no_numeric_seal"]
    per_run: List[dict] = []
    agg: List[dict] = []

    for variant in variants:
        utilities = []
        leak_black = []
        leak_white = []
        for track, paths in TRACKS.items():
            sealed = load_records(paths["sealed"])
            raw = load_records(paths["raw"])
            var_records = _make_variant_records(variant, sealed, raw)
            var_path = out_root / "variants" / track / f"{variant}.jsonl"
            var_path.parent.mkdir(parents=True, exist_ok=True)
            save_records(var_records, var_path)

            attack = run_adaptive_attack(var_path, paths["raw"], paths["codebook"])
            leak_black.append(float(attack["black_box"]["composite_leakage"]))
            leak_white.append(float(attack["white_box"]["composite_leakage"]))
            attack_path = out_root / "attacks" / f"{track}_{variant}.json"
            attack_path.parent.mkdir(parents=True, exist_ok=True)
            attack_path.write_text(json.dumps(attack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            for seed in args.seeds:
                u = _run_frontier_utility(var_path, paths["raw"], seed)
                utilities.append(u)
                per_run.append(
                    {
                        "variant": variant,
                        "track": track,
                        "seed": seed,
                        "utility": round(u, 4),
                        "leakage_black_box": round(float(attack["black_box"]["composite_leakage"]), 4),
                        "leakage_white_box": round(float(attack["white_box"]["composite_leakage"]), 4),
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

    # Manual decision logging ablation (auditability axis).
    manual_on_dir = out_root / "manual_on"
    manual_off_dir = out_root / "manual_off"
    cmd_base = [sys.executable, "provetok/scripts/run_exp_manual_decisions_offline.py", "--track", "both"]

    subprocess.run(
        cmd_base + ["--run_dir", str(manual_on_dir)],
        check=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
    )
    subprocess.run(
        cmd_base + ["--run_dir", str(manual_off_dir), "--disable_manual_decisions"],
        check=True,
        cwd=str(Path(__file__).resolve().parents[2]),
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

    per_run_path = out_root / "per_run_metrics.json"
    per_run_path.write_text(json.dumps(per_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = out_root / "ablation_results.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "utility_mean",
                "utility_std",
                "leakage_black_box",
                "leakage_white_box",
            ],
        )
        writer.writeheader()
        for row in agg:
            writer.writerow(row)

    md_lines = [
        "# Oral Ablations (EXP-013)",
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

    print(f"Saved: {csv_path}")
    print(f"Saved: {out_root / 'ablation_results.md'}")
    print(f"Saved: {out_root / 'manual_logging_ablation.json'}")


if __name__ == "__main__":
    main()
