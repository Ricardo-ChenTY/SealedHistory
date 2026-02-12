"""Run adaptive multi-budget attack curves on a scale (non-toy) dataset (vNext).

This is a vNext variant of `run_oral_budget_attack.py` that adds:
- dataset_dir parameterization
- deterministic subsampling (max_observed) for scale runs

Setups:
- {A,B}_sealed: scale sealed records
- {A,B}_defended: defended records (defaults to `runs/EXP-027/defended_{A,B}.jsonl`)

Outputs (under --output_dir):
- budget_curves.json
- budget_curves.md
- run_meta.json
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import re
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records


WORD_RE = re.compile(r"[a-z0-9_]+")


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _tokenize(text: str) -> List[str]:
    return WORD_RE.findall(str(text or "").lower())


def _record_tokens(rec: PaperRecord, reverse_map: Dict[str, str] | None = None) -> List[str]:
    text_parts = [
        rec.title,
        rec.background,
        rec.mechanism,
        rec.experiment,
        " ".join(rec.keywords or []),
    ]
    base = _tokenize(" ".join(text_parts))
    if not reverse_map:
        return base
    out: List[str] = []
    for tok in base:
        real = reverse_map.get(tok)
        if real:
            out.extend(_tokenize(real))
        else:
            out.append(tok)
    return out


def _jaccard_set(a: Iterable[str], b: Iterable[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa) + len(sb) - inter
    return inter / union if union else 0.0


def _reverse_map(codebook: Path | None) -> Dict[str, str]:
    if codebook is None or not codebook.exists():
        return {}
    obj = json.loads(codebook.read_text(encoding="utf-8"))
    forward = obj.get("forward") or {}
    return {str(v).strip().lower(): str(k).strip().lower() for k, v in forward.items()}


def _subsample(records: List[PaperRecord], allowed_ids: set[str], *, max_observed: int | None, seed: int) -> List[PaperRecord]:
    obs = [r for r in records if r.paper_id in allowed_ids]
    if max_observed is None or max_observed <= 0 or len(obs) <= int(max_observed):
        return obs
    rng = random.Random(int(seed))
    rng.shuffle(obs)
    return obs[: int(max_observed)]


def _top1_rate(
    observed: List[PaperRecord],
    raw_index: Dict[str, List[str]],
    *,
    budget: int,
    reverse: Dict[str, str] | None,
) -> float:
    pids = sorted(raw_index.keys())
    n = 0
    hits = 0
    for rec in observed:
        if rec.paper_id not in raw_index:
            continue
        q = _record_tokens(rec, reverse_map=reverse)[: max(1, int(budget))]
        best_pid = ""
        best_score = -1.0
        for pid in pids:
            s = _jaccard_set(q, raw_index[pid])
            if s > best_score or (s == best_score and pid < best_pid):
                best_score = s
                best_pid = pid
        hits += int(best_pid == rec.paper_id)
        n += 1
    return (hits / n) if n else 0.0


def _curve(
    *,
    observed_path: Path,
    raw_path: Path,
    codebook: Path | None,
    budgets: List[int],
    max_observed: int | None,
    seed: int,
) -> Tuple[dict, int]:
    observed_all = load_records(observed_path)
    raw = load_records(raw_path)
    raw_index = {r.paper_id: _record_tokens(r, reverse_map=None) for r in raw if r.paper_id}
    allowed = set(raw_index.keys())
    observed = _subsample(observed_all, allowed, max_observed=max_observed, seed=seed)
    reverse = _reverse_map(codebook)

    black = []
    white = []
    for b in budgets:
        black.append({"budget": int(b), "top1": round(_top1_rate(observed, raw_index, budget=b, reverse=None), 4)})
        white.append({"budget": int(b), "top1": round(_top1_rate(observed, raw_index, budget=b, reverse=reverse), 4)})

    return {"black_box": black, "white_box": white}, len(observed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vNext (scale) adaptive budget attack curves.")
    parser.add_argument("--dataset_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--defended_dir", default="runs/EXP-027")
    parser.add_argument("--output_dir", default="runs/EXP-029")
    parser.add_argument("--budgets", nargs="+", type=int, default=[8, 16, 32, 64, 128])
    parser.add_argument("--max_observed", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(args.dataset_dir)
    defended_dir = Path(args.defended_dir)

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

    max_obs = int(args.max_observed) if int(args.max_observed) > 0 else None
    out = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "defended_dir": str(defended_dir),
        "budgets": [int(x) for x in args.budgets],
        "max_observed": max_obs,
        "seed": int(args.seed),
        "curves": {},
        "n_eval_records": {},
    }
    for name, cfg in setups.items():
        if not Path(cfg["observed"]).exists():
            continue
        curves, n_used = _curve(
            observed_path=Path(cfg["observed"]),
            raw_path=Path(cfg["raw"]),
            codebook=Path(cfg["codebook"]) if Path(cfg["codebook"]).exists() else None,
            budgets=args.budgets,
            max_observed=max_obs,
            seed=int(args.seed),
        )
        out["curves"][name] = curves
        out["n_eval_records"][name] = int(n_used)

    (out_dir / "budget_curves.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Adaptive Budget Attack Curves (vNext, EXP-029)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- defended_dir: `{defended_dir}`",
        f"- max_observed: `{max_obs}`",
        f"- seed: `{args.seed}`",
        "",
        "| Setup | Budget | Top1 Black-Box | Top1 White-Box |",
        "|---|---:|---:|---:|",
    ]
    for name, curves in out["curves"].items():
        bb = {x["budget"]: x["top1"] for x in curves["black_box"]}
        wb = {x["budget"]: x["top1"] for x in curves["white_box"]}
        for b in args.budgets:
            if int(b) not in bb or int(b) not in wb:
                continue
            md.append("| `{}` | {} | {:.4f} | {:.4f} |".format(name, int(b), float(bb[int(b)]), float(wb[int(b)])))
    (out_dir / "budget_curves.md").write_text("\n".join(md) + "\n", encoding="utf-8")

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
        "defended_dir": str(defended_dir),
        "budgets": [int(x) for x in args.budgets],
        "max_observed": max_obs,
        "seed": int(args.seed),
        "n_eval_records": out["n_eval_records"],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'budget_curves.json'}")
    print(f"Saved: {out_dir / 'budget_curves.md'}")


if __name__ == "__main__":
    main()

