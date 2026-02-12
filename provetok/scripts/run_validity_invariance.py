"""Validity / measurement-invariance diagnostics for sealed vs raw views.

Goal: quantify whether the *relative ordering* of agents/models is preserved
between raw and sealed views, and run a metadata-only sanity baseline to
address validity concerns.

This script is intentionally lightweight: it runs the same benchmark loop used
elsewhere in this repo (no training) and produces a single summary artifact.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.agents.base import CopyLastAgent, DependencyAwareAgent, FrontierSynthesisAgent, RandomAgent, run_agent_loop
from provetok.data.schema import PaperRecord, load_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.eval.rubric import AutoRubricScorer


DEFAULT_AGENTS = ["random", "copylast", "dependency", "frontier"]


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


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


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _structure_only_view(records: List[PaperRecord]) -> List[PaperRecord]:
    """Keep graph + ids + metadata, remove rich text fields."""
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.title = "Redacted title (structure-only)"
        d.background = ""
        d.mechanism = ""
        d.experiment = ""
        d.keywords = []
        out.append(d)
    return out


def _metadata_only_view(records: List[PaperRecord]) -> List[PaperRecord]:
    """Keep only minimal metadata (year/venue/authors) and ids; remove graph + text."""
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.title = "Metadata-only title"
        d.background = ""
        d.mechanism = ""
        d.experiment = ""
        d.dependencies = []
        d.keywords = []
        out.append(d)
    return out


def _load_views(dataset_dir: Path, track: str) -> Dict[str, List[PaperRecord]]:
    raw_path = dataset_dir / f"track_{track}_raw.jsonl"
    sealed_path = dataset_dir / f"track_{track}_sealed.jsonl"

    raw = load_records(raw_path)
    sealed = load_records(sealed_path)

    return {
        "raw": raw,
        "sealed": sealed,
        "structure_only": _structure_only_view(sealed),
        "metadata_only": _metadata_only_view(sealed),
    }


def _run_one(
    *,
    observed: List[PaperRecord],
    raw: List[PaperRecord],
    agent_name: str,
    seed: int,
    budget: int,
    max_cycles: int,
) -> Dict[str, float]:
    env = BenchmarkEnvironment(
        sealed_records=observed,
        real_records=raw,
        budget=int(budget),
        fast_mode=True,
    )
    agent = _agent_by_name(agent_name, seed=int(seed))
    trace = run_agent_loop(agent, env, max_cycles=int(max_cycles))
    rubric = AutoRubricScorer().score_run(trace, raw)

    total = float(rubric.get("total") or 0.0)
    per_dim = dict(rubric.get("per_dimension_avg") or {})
    per_dim = {str(k): float(v) for k, v in per_dim.items()}
    per_dim["total"] = total
    return per_dim


def _avg(values: List[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def _ranks(values: Dict[str, float]) -> Dict[str, float]:
    """Average ranks for ties; higher value => higher rank (1..n)."""
    items = [(k, float(v)) for k, v in values.items()]
    items.sort(key=lambda kv: kv[1])

    ranks: Dict[str, float] = {}
    i = 0
    n = len(items)
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for t in range(i, j + 1):
            ranks[items[t][0]] = avg_rank
        i = j + 1

    return ranks


def _pearson(x: List[float], y: List[float]) -> float:
    if not x or not y or len(x) != len(y):
        return 0.0
    mx = statistics.mean(x)
    my = statistics.mean(y)
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    if vx <= 0.0 or vy <= 0.0:
        return 0.0
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return float(cov / math.sqrt(vx * vy))


def _spearman(values_a: Dict[str, float], values_b: Dict[str, float]) -> float:
    keys = [k for k in sorted(values_a.keys()) if k in values_b]
    ra = _ranks({k: float(values_a[k]) for k in keys})
    rb = _ranks({k: float(values_b[k]) for k in keys})
    return _pearson([ra[k] for k in keys], [rb[k] for k in keys])


def _kendall_tau_a(values_a: Dict[str, float], values_b: Dict[str, float]) -> float:
    keys = [k for k in sorted(values_a.keys()) if k in values_b]
    n = len(keys)
    if n < 2:
        return 0.0

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            ki = keys[i]
            kj = keys[j]
            da = float(values_a[ki]) - float(values_a[kj])
            db = float(values_b[ki]) - float(values_b[kj])
            if da == 0.0 or db == 0.0:
                continue
            if (da > 0 and db > 0) or (da < 0 and db < 0):
                concordant += 1
            else:
                discordant += 1

    denom = concordant + discordant
    return float((concordant - discordant) / denom) if denom > 0 else 0.0


def _summarize_track(track_rows: List[dict]) -> dict:
    by_view: Dict[str, Dict[str, List[float]]] = {}
    for r in track_rows:
        view = str(r["view"])
        agent = str(r["agent"])
        by_view.setdefault(view, {}).setdefault(agent, []).append(float(r["utility_total"]))

    mean_by_view_agent: Dict[str, Dict[str, float]] = {
        v: {a: _avg(xs) for a, xs in sorted(m.items())} for v, m in sorted(by_view.items())
    }

    raw = mean_by_view_agent.get("raw", {})
    sealed = mean_by_view_agent.get("sealed", {})
    structure_only = mean_by_view_agent.get("structure_only", {})
    metadata_only = mean_by_view_agent.get("metadata_only", {})

    return {
        "mean_utility": mean_by_view_agent,
        "rank_corr_raw_vs_sealed": {
            "spearman": round(_spearman(raw, sealed), 4) if raw and sealed else 0.0,
            "kendall_tau_a": round(_kendall_tau_a(raw, sealed), 4) if raw and sealed else 0.0,
        },
        "rank_corr_raw_vs_structure_only": {
            "spearman": round(_spearman(raw, structure_only), 4) if raw and structure_only else 0.0,
            "kendall_tau_a": round(_kendall_tau_a(raw, structure_only), 4) if raw and structure_only else 0.0,
        },
        "rank_corr_raw_vs_metadata_only": {
            "spearman": round(_spearman(raw, metadata_only), 4) if raw and metadata_only else 0.0,
            "kendall_tau_a": round(_kendall_tau_a(raw, metadata_only), 4) if raw and metadata_only else 0.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run validity invariance diagnostics (rank correlations).")
    parser.add_argument("--dataset_dir", default="runs/EXP-031/public")
    parser.add_argument("--output_dir", default="runs/EXP-039")
    parser.add_argument("--agents", default=",".join(DEFAULT_AGENTS))
    parser.add_argument("--tracks", default="A,B")
    parser.add_argument("--seeds", default="11,22,33")
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--max_cycles", type=int, default=80)
    args = parser.parse_args()

    t0 = time.time()
    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    agents = [a.strip() for a in str(args.agents).split(",") if a.strip()]
    tracks = [t.strip() for t in str(args.tracks).split(",") if t.strip()]
    seeds = [int(s.strip()) for s in str(args.seeds).split(",") if s.strip()]

    rows: List[dict] = []

    for track in tracks:
        views = _load_views(dataset_dir, track)
        raw = views["raw"]
        for view_name, observed in sorted(views.items()):
            for agent in agents:
                for seed in seeds:
                    m = _run_one(
                        observed=observed,
                        raw=raw,
                        agent_name=agent,
                        seed=int(seed),
                        budget=int(args.budget),
                        max_cycles=int(args.max_cycles),
                    )
                    rows.append(
                        {
                            "track": str(track),
                            "view": str(view_name),
                            "agent": str(agent),
                            "seed": int(seed),
                            "utility_total": float(m.get("total") or 0.0),
                            "per_dimension_avg": {k: float(v) for k, v in m.items() if k != "total"},
                        }
                    )

    by_track: Dict[str, List[dict]] = {}
    for r in rows:
        by_track.setdefault(str(r["track"]), []).append(r)

    per_track = {t: _summarize_track(rs) for t, rs in sorted(by_track.items())}

    overall_rows = list(rows)
    overall = _summarize_track(overall_rows)

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "agents": list(agents),
        "tracks": list(tracks),
        "seeds": list(seeds),
        "n_rows": len(rows),
        "overall": overall,
        "per_track": per_track,
        "rows_preview": rows[:20],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md: List[str] = [
        "# Validity / Invariance (EXP-039)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- agents: `{', '.join(agents)}`",
        f"- tracks: `{', '.join(tracks)}`",
        f"- seeds: `{', '.join(str(s) for s in seeds)}`",
        "",
        "## Overall rank correlations",
        "",
        f"- raw vs sealed spearman: `{overall['rank_corr_raw_vs_sealed']['spearman']}`",
        f"- raw vs sealed kendall_tau_a: `{overall['rank_corr_raw_vs_sealed']['kendall_tau_a']}`",
        f"- raw vs structure_only spearman: `{overall['rank_corr_raw_vs_structure_only']['spearman']}`",
        f"- raw vs metadata_only spearman: `{overall['rank_corr_raw_vs_metadata_only']['spearman']}`",
        "",
        "## Per-track rank correlations",
        "",
        "| Track | raw~sealed (spearman) | raw~structure_only | raw~metadata_only |",
        "|---|---:|---:|---:|",
    ]
    for t, r in sorted(per_track.items()):
        md.append(
            "| {} | {:.4f} | {:.4f} | {:.4f} |".format(
                t,
                float(r["rank_corr_raw_vs_sealed"]["spearman"]),
                float(r["rank_corr_raw_vs_structure_only"]["spearman"]),
                float(r["rank_corr_raw_vs_metadata_only"]["spearman"]),
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
        "dataset_dir": str(dataset_dir),
        "agents": list(agents),
        "tracks": list(tracks),
        "seeds": list(seeds),
        "budget": int(args.budget),
        "max_cycles": int(args.max_cycles),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

