"""Compute confidence intervals and significance tests for oral main results (EXP-017)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Dict, List


def _bootstrap_ci_diff(a: List[float], b: List[float], n_boot: int = 5000, seed: int = 42) -> Dict[str, float]:
    rng = random.Random(seed)
    n_a = len(a)
    n_b = len(b)
    diffs = []
    for _ in range(n_boot):
        sa = [a[rng.randrange(n_a)] for _ in range(n_a)]
        sb = [b[rng.randrange(n_b)] for _ in range(n_b)]
        diffs.append(statistics.mean(sa) - statistics.mean(sb))
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs))]
    return {"ci95_low": round(lo, 4), "ci95_high": round(hi, 4)}


def _permutation_p_value(a: List[float], b: List[float], n_perm: int = 5000, seed: int = 42) -> float:
    rng = random.Random(seed)
    obs = statistics.mean(a) - statistics.mean(b)
    pool = list(a) + list(b)
    n_a = len(a)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        da = pool[:n_a]
        db = pool[n_a:]
        diff = statistics.mean(da) - statistics.mean(db)
        if abs(diff) >= abs(obs):
            ge += 1
    return round((ge + 1) / (n_perm + 1), 4)


def _cohen_d(a: List[float], b: List[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    va = statistics.variance(a)
    vb = statistics.variance(b)
    pooled = ((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)
    if pooled <= 0:
        return 0.0
    return (statistics.mean(a) - statistics.mean(b)) / math.sqrt(pooled)


def _read_per_run(path: Path) -> List[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_main_csv(path: Path) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows[row["config_id"]] = row
    return rows


def _utility_rows(per_run: List[dict], config_id: str) -> List[float]:
    return [float(r["utility"]) for r in per_run if r["config_id"] == config_id]


def _compare(per_run: List[dict], left: str, right: str) -> dict:
    a = _utility_rows(per_run, left)
    b = _utility_rows(per_run, right)
    if not a or not b:
        return {"left": left, "right": right, "error": "missing rows"}
    out = {
        "left": left,
        "right": right,
        "n_left": len(a),
        "n_right": len(b),
        "mean_left": round(statistics.mean(a), 4),
        "mean_right": round(statistics.mean(b), 4),
        "mean_diff_left_minus_right": round(statistics.mean(a) - statistics.mean(b), 4),
        "cohen_d": round(_cohen_d(a, b), 4),
        "p_perm_two_sided": _permutation_p_value(a, b),
    }
    out.update(_bootstrap_ci_diff(a, b))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXP-017 significance and CI analysis.")
    parser.add_argument("--per_run", default="runs/EXP-011/per_run_metrics.json")
    parser.add_argument("--main_csv", default="runs/EXP-011/main_results.csv")
    parser.add_argument("--defense_summary", default="runs/EXP-016/summary.json")
    parser.add_argument("--output_dir", default="runs/EXP-017")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_run = _read_per_run(Path(args.per_run))
    csv_rows = _read_main_csv(Path(args.main_csv))
    defense = json.loads(Path(args.defense_summary).read_text(encoding="utf-8")) if Path(args.defense_summary).exists() else {}

    comparisons = [
        _compare(per_run, "sealed_frontier", "raw_frontier"),
        _compare(per_run, "sealed_frontier", "sealed_dependency"),
        _compare(per_run, "sealed_frontier", "sealed_copylast"),
    ]

    leakage_rows = {}
    for cid in ("sealed_frontier", "raw_frontier", "sealed_dependency", "sealed_copylast"):
        r = csv_rows.get(cid)
        if not r:
            continue
        leakage_rows[cid] = {
            "black_box": round(float(r["leakage_black_box"]), 4),
            "white_box": round(float(r["leakage_white_box"]), 4),
        }

    summary = {
        "comparisons": comparisons,
        "leakage_snapshot": leakage_rows,
        "defense_snapshot": defense.get("tracks", {}),
        "notes": [
            "Permutation p-values are two-sided.",
            "CI is bootstrap 95% for mean difference (left - right).",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Statistical Confidence & Significance (EXP-017)",
        "",
        "| Comparison (left-right) | Mean Left | Mean Right | Diff | 95% CI | p-value | Cohen's d |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in comparisons:
        if "error" in c:
            continue
        md.append(
            "| `{l}`-`{r}` | {ml:.4f} | {mr:.4f} | {d:.4f} | [{lo:.4f}, {hi:.4f}] | {p:.4f} | {cd:.4f} |".format(
                l=c["left"],
                r=c["right"],
                ml=c["mean_left"],
                mr=c["mean_right"],
                d=c["mean_diff_left_minus_right"],
                lo=c["ci95_low"],
                hi=c["ci95_high"],
                p=c["p_perm_two_sided"],
                cd=c["cohen_d"],
            )
        )
    md.extend(
        [
            "",
            "## Leakage Snapshot",
            "",
            "| Config | Black-Box Leakage | White-Box Leakage |",
            "|---|---:|---:|",
        ]
    )
    for cid, row in leakage_rows.items():
        md.append("| `{}` | {:.4f} | {:.4f} |".format(cid, row["black_box"], row["white_box"]))

    if defense.get("tracks"):
        md.extend(
            [
                "",
                "## White-Box Defense Snapshot (EXP-016)",
                "",
                "| Track | WB Defended | WB Raw | Delta |",
                "|---|---:|---:|---:|",
            ]
        )
        for t, r in sorted(defense["tracks"].items()):
            md.append(
                "| {} | {:.4f} | {:.4f} | {:.4f} |".format(
                    t,
                    r["white_box_leakage_defended"],
                    r["white_box_leakage_raw"],
                    r["white_box_delta_defended_minus_raw"],
                )
            )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
