"""Run extraction attack stress tests with escalating budgets."""

from __future__ import annotations

import argparse
import json
import platform
import re
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

from provetok.data.schema import PaperRecord, load_records, save_records
from run_oral_adaptive_attack_vnext import run_adaptive_attack


WORD_RE = re.compile(r"[a-z0-9_]+")


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _truncate_text(text: str, *, budget: int) -> str:
    toks = WORD_RE.findall(str(text or "").lower())
    return " ".join(toks[: max(1, int(budget))])


def _budget_view(records: List[PaperRecord], *, budget: int) -> List[PaperRecord]:
    out: List[PaperRecord] = []
    kw_keep = max(1, int(budget) // 12)
    for rec in records:
        d = PaperRecord.from_dict(rec.to_dict())
        d.title = _truncate_text(d.title, budget=budget)
        d.background = _truncate_text(d.background, budget=budget)
        d.mechanism = _truncate_text(d.mechanism, budget=budget)
        d.experiment = _truncate_text(d.experiment, budget=budget)
        d.keywords = list(d.keywords or [])[:kw_keep]
        out.append(d)
    return out


def _curve_for_setup(
    *,
    setup_name: str,
    observed_path: Path,
    raw_path: Path,
    codebook_path: Path | None,
    budgets: List[int],
    tmp_dir: Path,
    max_observed: int | None,
    seed: int,
) -> List[dict]:
    observed = load_records(observed_path)
    curve: List[dict] = []
    for b in budgets:
        view = _budget_view(observed, budget=int(b))
        view_path = tmp_dir / f"{setup_name}_budget_{int(b)}.jsonl"
        save_records(view, view_path)
        atk = run_adaptive_attack(
            sealed_path=view_path,
            raw_path=raw_path,
            codebook_path=codebook_path,
            max_observed=max_observed,
            seed=int(seed),
        )
        curve.append(
            {
                "budget": int(b),
                "black_box": {
                    "retrieval_top1": float(atk["black_box"]["retrieval_top1"]),
                    "retrieval_top3": float(atk["black_box"]["retrieval_top3"]),
                    "keyword_recovery": float(atk["black_box"]["keyword_recovery"]),
                    "composite_leakage": float(atk["black_box"]["composite_leakage"]),
                },
                "white_box": {
                    "retrieval_top1": float(atk["white_box"]["retrieval_top1"]),
                    "retrieval_top3": float(atk["white_box"]["retrieval_top3"]),
                    "keyword_recovery": float(atk["white_box"]["keyword_recovery"]),
                    "composite_leakage": float(atk["white_box"]["composite_leakage"]),
                },
                "n_records_eval_retrieval": int(atk.get("n_records_eval_retrieval", 0)),
            }
        )
    return curve


def _curve_auc(curve: List[dict], *, channel: str, metric: str) -> float:
    vals = [float(p[channel][metric]) for p in curve]
    return statistics.mean(vals) if vals else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run extraction stress tests under budget escalation.")
    parser.add_argument("--dataset_dir", default="runs/EXP-031/public")
    parser.add_argument("--defended_dir", default="runs/EXP-027")
    parser.add_argument("--output_dir", default="runs/EXP-037")
    parser.add_argument("--budgets", nargs="+", type=int, default=[32, 64, 128, 256])
    parser.add_argument("--max_observed", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    dataset_dir = Path(args.dataset_dir)
    defended_dir = Path(args.defended_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / "tmp_budget_views"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    setups = {
        "A_sealed": {
            "observed": dataset_dir / "track_A_sealed.jsonl",
            "raw": dataset_dir / "track_A_raw.jsonl",
            "codebook": dataset_dir / "track_A_sealed.codebook.json",
        },
        "B_sealed": {
            "observed": dataset_dir / "track_B_sealed.jsonl",
            "raw": dataset_dir / "track_B_raw.jsonl",
            "codebook": dataset_dir / "track_B_sealed.codebook.json",
        },
        "A_defended": {
            "observed": defended_dir / "defended_A.jsonl",
            "raw": dataset_dir / "track_A_raw.jsonl",
            "codebook": dataset_dir / "track_A_sealed.codebook.json",
        },
        "B_defended": {
            "observed": defended_dir / "defended_B.jsonl",
            "raw": dataset_dir / "track_B_raw.jsonl",
            "codebook": dataset_dir / "track_B_sealed.codebook.json",
        },
    }

    max_observed = int(args.max_observed) if int(args.max_observed) > 0 else None
    curves: Dict[str, List[dict]] = {}
    for name, cfg in setups.items():
        obs = Path(cfg["observed"])
        if not obs.exists():
            continue
        cb = Path(cfg["codebook"]) if Path(cfg["codebook"]).exists() else None
        curves[name] = _curve_for_setup(
            setup_name=name,
            observed_path=obs,
            raw_path=Path(cfg["raw"]),
            codebook_path=cb,
            budgets=[int(b) for b in args.budgets],
            tmp_dir=tmp_dir,
            max_observed=max_observed,
            seed=int(args.seed),
        )

    def _track_delta(track: str, metric: str) -> float:
        sealed = curves.get(f"{track}_sealed", [])
        defended = curves.get(f"{track}_defended", [])
        if not sealed or not defended:
            return 0.0
        s = float(sealed[-1]["white_box"][metric])
        d = float(defended[-1]["white_box"][metric])
        return d - s

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "defended_dir": str(defended_dir),
        "budgets": [int(b) for b in args.budgets],
        "max_observed": max_observed,
        "seed": int(args.seed),
        "curves": curves,
        "aggregates": {
            name: {
                "auc_black_box_top1": round(_curve_auc(curve, channel="black_box", metric="retrieval_top1"), 4),
                "auc_white_box_top1": round(_curve_auc(curve, channel="white_box", metric="retrieval_top1"), 4),
                "auc_black_box_composite": round(_curve_auc(curve, channel="black_box", metric="composite_leakage"), 4),
                "auc_white_box_composite": round(_curve_auc(curve, channel="white_box", metric="composite_leakage"), 4),
            }
            for name, curve in curves.items()
        },
        "defended_minus_sealed_at_max_budget": {
            "A_white_box_top1": round(_track_delta("A", "retrieval_top1"), 4),
            "B_white_box_top1": round(_track_delta("B", "retrieval_top1"), 4),
            "A_white_box_composite": round(_track_delta("A", "composite_leakage"), 4),
            "B_white_box_composite": round(_track_delta("B", "composite_leakage"), 4),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Extraction Attack Stress Test (EXP-037)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- defended_dir: `{defended_dir}`",
        f"- budgets: `{[int(b) for b in args.budgets]}`",
        f"- max_observed: `{max_observed}`",
        "",
        "| Setup | Budget | BB top1 | WB top1 | BB composite | WB composite |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, curve in sorted(curves.items()):
        for row in curve:
            md.append(
                "| {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(
                    name,
                    int(row["budget"]),
                    float(row["black_box"]["retrieval_top1"]),
                    float(row["white_box"]["retrieval_top1"]),
                    float(row["black_box"]["composite_leakage"]),
                    float(row["white_box"]["composite_leakage"]),
                )
            )
    md.extend(
        [
            "",
            "## Defended - Sealed @ Max Budget (White-Box)",
            f"- A top1 delta: `{summary['defended_minus_sealed_at_max_budget']['A_white_box_top1']}`",
            f"- B top1 delta: `{summary['defended_minus_sealed_at_max_budget']['B_white_box_top1']}`",
            f"- A composite delta: `{summary['defended_minus_sealed_at_max_budget']['A_white_box_composite']}`",
            f"- B composite delta: `{summary['defended_minus_sealed_at_max_budget']['B_white_box_composite']}`",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ru = resource.getrusage(resource.RUSAGE_SELF)
    run_meta = {
        "started_ts_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "ended_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_sec": round(float(time.time() - t0), 3),
        "maxrss_kb": int(getattr(ru, "ru_maxrss", 0) or 0),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
        "dataset_dir": str(dataset_dir),
        "defended_dir": str(defended_dir),
        "budgets": [int(b) for b in args.budgets],
        "max_observed": max_observed,
        "seed": int(args.seed),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

