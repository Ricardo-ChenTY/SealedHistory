"""Cross-domain trend check for oral readiness (Track A/B)."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize cross-domain trends from EXP-011 outputs.")
    parser.add_argument("--input", default="runs/EXP-011/per_run_metrics.json")
    parser.add_argument("--output_dir", default="runs/EXP-014")
    args = parser.parse_args()

    src = Path(args.input)
    rows = json.loads(src.read_text(encoding="utf-8"))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tracks = sorted({r["track"] for r in rows})
    cfg_main = "sealed_frontier"
    cfg_raw = "raw_frontier"

    summary = {"tracks": {}, "overall": {}}
    for t in tracks:
        r_main = [r for r in rows if r["track"] == t and r["config_id"] == cfg_main]
        r_raw = [r for r in rows if r["track"] == t and r["config_id"] == cfg_raw]
        if not r_main or not r_raw:
            continue
        main_u = statistics.mean([r["utility"] for r in r_main])
        raw_u = statistics.mean([r["utility"] for r in r_raw])
        main_lb = statistics.mean([r["leakage_black_box"] for r in r_main])
        raw_lb = statistics.mean([r["leakage_black_box"] for r in r_raw])
        main_lw = statistics.mean([r["leakage_white_box"] for r in r_main])
        raw_lw = statistics.mean([r["leakage_white_box"] for r in r_raw])
        summary["tracks"][t] = {
            "utility_main": round(main_u, 4),
            "utility_raw": round(raw_u, 4),
            "utility_retention_main_vs_raw": round(main_u / raw_u, 4) if raw_u else 0.0,
            "black_box_leakage_main": round(main_lb, 4),
            "black_box_leakage_raw": round(raw_lb, 4),
            "white_box_leakage_main": round(main_lw, 4),
            "white_box_leakage_raw": round(raw_lw, 4),
            "trend_holds_black_box": bool(main_lb < raw_lb),
            "trend_holds_white_box": bool(main_lw < raw_lw),
        }

    per_track = list(summary["tracks"].values())
    summary["overall"] = {
        "n_tracks": len(per_track),
        "trend_holds_all_tracks_black_box": all(x["trend_holds_black_box"] for x in per_track) if per_track else False,
        "trend_holds_all_tracks_white_box": all(x["trend_holds_white_box"] for x in per_track) if per_track else False,
        "avg_utility_retention_main_vs_raw": round(
            statistics.mean([x["utility_retention_main_vs_raw"] for x in per_track]), 4
        )
        if per_track
        else 0.0,
    }

    json_path = out_dir / "cross_domain_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Cross-Domain Generalization (EXP-014)",
        "",
        "| Track | Main Utility | Raw Utility | Utility Retention | Main Leakage (BB/WB) | Raw Leakage (BB/WB) | Trend Holds |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for t in tracks:
        row = summary["tracks"].get(t)
        if not row:
            continue
        md_lines.append(
            "| {t} | {mu:.4f} | {ru:.4f} | {ret:.4f} | {mlb:.4f}/{mlw:.4f} | {rlb:.4f}/{rlw:.4f} | {ok} |".format(
                t=t,
                mu=row["utility_main"],
                ru=row["utility_raw"],
                ret=row["utility_retention_main_vs_raw"],
                mlb=row["black_box_leakage_main"],
                mlw=row["white_box_leakage_main"],
                rlb=row["black_box_leakage_raw"],
                rlw=row["white_box_leakage_raw"],
                ok="yes" if row["trend_holds_black_box"] and row["trend_holds_white_box"] else "no",
            )
        )
    md_lines.extend(
        [
            "",
            "## Overall",
            f"- trend_holds_all_tracks_black_box: `{summary['overall']['trend_holds_all_tracks_black_box']}`",
            f"- trend_holds_all_tracks_white_box: `{summary['overall']['trend_holds_all_tracks_white_box']}`",
            f"- avg_utility_retention_main_vs_raw: `{summary['overall']['avg_utility_retention_main_vs_raw']}`",
        ]
    )
    md_path = out_dir / "cross_domain_summary.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")


if __name__ == "__main__":
    main()
