"""Compute inter-rater agreement for oral human-eval sheets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _safe_float(v: str) -> float:
    s = str(v or "").strip()
    if not s:
        return 0.0
    return float(s)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Cohen's kappa for human eval.")
    parser.add_argument("--ratings_csv", default="docs/templates/human_eval_sheet.csv")
    parser.add_argument("--output_dir", default="runs/EXP-015")
    parser.add_argument("--threshold", type=float, default=0.5, help="overall >= threshold => accept")
    args = parser.parse_args()

    ratings_csv = Path(args.ratings_csv)
    rows = _read_rows(ratings_csv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    by_rater: dict[str, int] = {}
    by_item: dict[str, dict[str, float]] = {}
    for row in rows:
        item = str(row.get("item_id") or "").strip()
        rater = str(row.get("rater_id") or "").strip()
        if not item or not rater:
            continue
        overall = _safe_float(str(row.get("overall") or "0"))
        by_item.setdefault(item, {})[rater] = overall
        by_rater[rater] = by_rater.get(rater, 0) + 1

    raters = sorted(by_rater.keys(), key=lambda x: (-by_rater[x], x))
    result = {
        "ratings_csv": str(ratings_csv),
        "n_rows": len(rows),
        "n_items": len(by_item),
        "raters": raters,
        "status": "pending",
    }

    if len(raters) < 2:
        result["reason"] = "Need at least two raters."
    else:
        r1, r2 = raters[:2]
        paired = []
        for item, v in by_item.items():
            if r1 in v and r2 in v:
                paired.append((item, v[r1], v[r2]))

        if not paired:
            result["reason"] = f"No paired items between {r1} and {r2}."
        else:
            y1 = [1 if s1 >= args.threshold else 0 for _, s1, _ in paired]
            y2 = [1 if s2 >= args.threshold else 0 for _, _, s2 in paired]
            n = len(paired)
            agree = sum(1 for a, b in zip(y1, y2) if a == b)
            po = agree / n
            p1_pos = sum(y1) / n
            p2_pos = sum(y2) / n
            p1_neg = 1.0 - p1_pos
            p2_neg = 1.0 - p2_pos
            pe = p1_pos * p2_pos + p1_neg * p2_neg
            kappa = (po - pe) / (1.0 - pe) if (1.0 - pe) > 0 else 0.0

            result.update(
                {
                    "status": "ok",
                    "pair": [r1, r2],
                    "n_paired_items": n,
                    "threshold": args.threshold,
                    "percent_agreement": round(po, 4),
                    "cohen_kappa": round(kappa, 4),
                    "label_distribution": {
                        r1: {"accept": round(p1_pos, 4), "reject": round(p1_neg, 4)},
                        r2: {"accept": round(p2_pos, 4), "reject": round(p2_neg, 4)},
                    },
                    "mean_overall": {
                        r1: round(sum(s1 for _, s1, _ in paired) / n, 4),
                        r2: round(sum(s2 for _, _, s2 in paired) / n, 4),
                    },
                }
            )

    json_path = out_dir / "human_eval_report.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Human Eval Consistency (EXP-015)",
        "",
        f"- ratings_csv: `{ratings_csv}`",
        f"- status: `{result['status']}`",
    ]
    if result["status"] == "ok":
        md_lines.extend(
            [
                f"- pair: `{result['pair'][0]}` vs `{result['pair'][1]}`",
                f"- n_paired_items: `{result['n_paired_items']}`",
                f"- percent_agreement: `{result['percent_agreement']}`",
                f"- cohen_kappa: `{result['cohen_kappa']}`",
            ]
        )
    else:
        md_lines.append(f"- reason: `{result.get('reason', 'insufficient ratings')}`")

    md_path = out_dir / "human_eval_report.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")


if __name__ == "__main__":
    main()
