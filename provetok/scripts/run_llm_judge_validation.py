"""Validate automated judge scores against human ratings (item-level)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _safe_float(v: str) -> float:
    s = str(v or "").strip()
    return float(s) if s else 0.0


def _pearson(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    return float(num / (denx * deny)) if denx > 0 and deny > 0 else 0.0


def _ranks(vals: List[float]) -> List[float]:
    idx = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[idx[j + 1]] == vals[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[idx[k]] = avg
        i = j + 1
    return out


def _spearman(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    return _pearson(_ranks(xs), _ranks(ys))


def _cohen_kappa_binary(xs: List[float], ys: List[float], *, threshold: float) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    x = [1 if float(v) >= float(threshold) else 0 for v in xs]
    y = [1 if float(v) >= float(threshold) else 0 for v in ys]
    n = len(x)
    po = sum(1 for a, b in zip(x, y) if a == b) / n
    px = sum(x) / n
    py = sum(y) / n
    pe = px * py + (1.0 - px) * (1.0 - py)
    return float((po - pe) / (1.0 - pe)) if (1.0 - pe) > 0 else 0.0


def _read_rows(path: Path) -> List[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _human_item_scores(rows: List[dict]) -> Dict[str, float]:
    by_item: Dict[str, List[float]] = {}
    for row in rows:
        item = str(row.get("item_id") or "").strip()
        if not item:
            continue
        by_item.setdefault(item, []).append(_safe_float(str(row.get("overall") or "0")))
    return {k: statistics.mean(v) for k, v in by_item.items() if v}


def _heuristic_item_scores(rows: List[dict]) -> Dict[str, float]:
    dims = ["problem_shift", "mechanism_class", "dependency", "claim_validity", "ablation", "clarity"]
    by_item: Dict[str, List[float]] = {}
    for row in rows:
        item = str(row.get("item_id") or "").strip()
        if not item:
            continue
        vals = [_safe_float(str(row.get(d) or "0")) for d in dims]
        by_item.setdefault(item, []).append(statistics.mean(vals))
    return {k: statistics.mean(v) for k, v in by_item.items() if v}


def _external_judge_scores(path: Path) -> Dict[str, float]:
    rows = _read_rows(path)
    by_item: Dict[str, List[float]] = {}
    for row in rows:
        item = str(row.get("item_id") or "").strip()
        if not item:
            continue
        score = _safe_float(str(row.get("judge_overall") or row.get("overall") or "0"))
        by_item.setdefault(item, []).append(score)
    return {k: statistics.mean(v) for k, v in by_item.items() if v}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate automated judge against human ratings.")
    parser.add_argument("--ratings_csv", default="docs/templates/human_eval_sheet.csv")
    parser.add_argument("--judge_csv", default="", help="Optional CSV with columns item_id, judge_overall.")
    parser.add_argument("--output_dir", default="runs/EXP-038")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min_kappa", type=float, default=0.2)
    parser.add_argument("--min_spearman", type=float, default=0.6)
    args = parser.parse_args()

    t0 = time.time()
    ratings_csv = Path(args.ratings_csv)
    rows = _read_rows(ratings_csv)
    human = _human_item_scores(rows)

    judge_source = "heuristic_from_rubric_dims"
    judge = _heuristic_item_scores(rows)
    if str(args.judge_csv or "").strip():
        judge_csv = Path(str(args.judge_csv))
        judge = _external_judge_scores(judge_csv)
        judge_source = str(judge_csv)

    common_items = sorted(set(human.keys()) & set(judge.keys()))
    xs = [float(human[k]) for k in common_items]
    ys = [float(judge[k]) for k in common_items]

    mae = statistics.mean([abs(a - b) for a, b in zip(xs, ys)]) if xs else 0.0
    pearson = _pearson(xs, ys)
    spearman = _spearman(xs, ys)
    kappa = _cohen_kappa_binary(xs, ys, threshold=float(args.threshold))
    pass_judge = bool(kappa >= float(args.min_kappa) and spearman >= float(args.min_spearman))

    per_item = [
        {
            "item_id": item,
            "human_mean_overall": round(float(human[item]), 4),
            "judge_score": round(float(judge[item]), 4),
            "abs_error": round(abs(float(human[item]) - float(judge[item])), 4),
        }
        for item in common_items
    ]
    per_item.sort(key=lambda r: (-float(r["abs_error"]), str(r["item_id"])))

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ratings_csv": str(ratings_csv),
        "judge_source": judge_source,
        "n_rows": len(rows),
        "n_items_human": len(human),
        "n_items_judge": len(judge),
        "n_items_common": len(common_items),
        "threshold": float(args.threshold),
        "metrics": {
            "mae": round(float(mae), 4),
            "pearson_r": round(float(pearson), 4),
            "spearman_r": round(float(spearman), 4),
            "cohen_kappa_binary": round(float(kappa), 4),
        },
        "pass_rule": {
            "min_kappa": float(args.min_kappa),
            "min_spearman": float(args.min_spearman),
            "pass": pass_judge,
        },
        "largest_errors": per_item[:30],
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# LLM-as-a-Judge Validation (EXP-038)",
        "",
        f"- ratings_csv: `{ratings_csv}`",
        f"- judge_source: `{judge_source}`",
        f"- n_items_common: `{len(common_items)}`",
        "",
        "## Metrics",
        f"- mae: `{summary['metrics']['mae']}`",
        f"- pearson_r: `{summary['metrics']['pearson_r']}`",
        f"- spearman_r: `{summary['metrics']['spearman_r']}`",
        f"- cohen_kappa_binary@{float(args.threshold)}: `{summary['metrics']['cohen_kappa_binary']}`",
        "",
        "## Pass Rule",
        f"- min_kappa: `{float(args.min_kappa)}`",
        f"- min_spearman: `{float(args.min_spearman)}`",
        f"- pass: `{summary['pass_rule']['pass']}`",
        "",
        "| Item | Human Mean | Judge Score | Abs Error |",
        "|---|---:|---:|---:|",
    ]
    for row in per_item[:20]:
        md.append(
            "| {} | {:.4f} | {:.4f} | {:.4f} |".format(
                row["item_id"],
                float(row["human_mean_overall"]),
                float(row["judge_score"]),
                float(row["abs_error"]),
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
        "ratings_csv": str(ratings_csv),
        "judge_source": judge_source,
        "threshold": float(args.threshold),
        "min_kappa": float(args.min_kappa),
        "min_spearman": float(args.min_spearman),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

