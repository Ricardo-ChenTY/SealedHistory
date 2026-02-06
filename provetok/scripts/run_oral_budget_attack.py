"""Run adaptive multi-budget attack curves (EXP-018)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records


WORD_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return WORD_RE.findall(str(text or "").lower())


def _record_tokens(rec: PaperRecord, reverse_map: Dict[str, str] | None = None) -> List[str]:
    base = _tokenize(" ".join([rec.title, rec.background, rec.mechanism, rec.experiment, " ".join(rec.keywords or [])]))
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


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _reverse_map(codebook: Path | None) -> Dict[str, str]:
    if codebook is None or not codebook.exists():
        return {}
    obj = json.loads(codebook.read_text(encoding="utf-8"))
    forward = obj.get("forward") or {}
    return {str(v).strip().lower(): str(k).strip().lower() for k, v in forward.items()}


def _top1_rate(
    observed: List[PaperRecord],
    raw: List[PaperRecord],
    budget: int,
    reverse: Dict[str, str] | None = None,
) -> float:
    raw_index = {r.paper_id: _record_tokens(r) for r in raw}
    pids = sorted(raw_index.keys())
    n = 0
    hits = 0
    for rec in observed:
        if rec.paper_id not in raw_index:
            continue
        q = _record_tokens(rec, reverse_map=reverse)[:budget]
        scored = [(_jaccard(q, raw_index[pid]), pid) for pid in pids]
        scored.sort(key=lambda x: (-x[0], x[1]))
        pred = scored[0][1] if scored else ""
        hits += int(pred == rec.paper_id)
        n += 1
    return (hits / n) if n else 0.0


def _curve(observed_path: Path, raw_path: Path, codebook: Path | None, budgets: List[int]) -> dict:
    observed = load_records(observed_path)
    raw = load_records(raw_path)
    reverse = _reverse_map(codebook)
    black = []
    white = []
    for b in budgets:
        black.append({"budget": b, "top1": round(_top1_rate(observed, raw, budget=b, reverse=None), 4)})
        white.append({"budget": b, "top1": round(_top1_rate(observed, raw, budget=b, reverse=reverse), 4)})
    return {"black_box": black, "white_box": white}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXP-018 adaptive budget attack curves.")
    parser.add_argument("--output_dir", default="runs/EXP-018")
    parser.add_argument("--budgets", nargs="+", type=int, default=[8, 16, 32, 64, 128])
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    setups = {
        "A_sealed": {
            "observed": Path("provetok/data/sealed/micro_history_a.sealed.jsonl"),
            "raw": Path("provetok/data/raw/micro_history_a.jsonl"),
            "codebook": Path("provetok/data/sealed/micro_history_a.sealed.codebook.json"),
        },
        "B_sealed": {
            "observed": Path("provetok/data/sealed/micro_history_b.sealed.jsonl"),
            "raw": Path("provetok/data/raw/micro_history_b.jsonl"),
            "codebook": Path("provetok/data/sealed/micro_history_b.sealed.codebook.json"),
        },
        "A_defended": {
            "observed": Path("runs/EXP-016/defended_A.jsonl"),
            "raw": Path("provetok/data/raw/micro_history_a.jsonl"),
            "codebook": Path("provetok/data/sealed/micro_history_a.sealed.codebook.json"),
        },
        "B_defended": {
            "observed": Path("runs/EXP-016/defended_B.jsonl"),
            "raw": Path("provetok/data/raw/micro_history_b.jsonl"),
            "codebook": Path("provetok/data/sealed/micro_history_b.sealed.codebook.json"),
        },
    }

    out = {"budgets": args.budgets, "curves": {}}
    for name, cfg in setups.items():
        if not cfg["observed"].exists():
            continue
        out["curves"][name] = _curve(
            observed_path=cfg["observed"],
            raw_path=cfg["raw"],
            codebook=cfg["codebook"],
            budgets=args.budgets,
        )

    (out_dir / "budget_curves.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md = [
        "# Adaptive Budget Attack Curves (EXP-018)",
        "",
        "| Setup | Budget | Top1 Black-Box | Top1 White-Box |",
        "|---|---:|---:|---:|",
    ]
    for name, curves in out["curves"].items():
        bb = {x["budget"]: x["top1"] for x in curves["black_box"]}
        wb = {x["budget"]: x["top1"] for x in curves["white_box"]}
        for b in args.budgets:
            if b not in bb or b not in wb:
                continue
            md.append("| `{}` | {} | {:.4f} | {:.4f} |".format(name, b, bb[b], wb[b]))
    (out_dir / "budget_curves.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'budget_curves.json'}")
    print(f"Saved: {out_dir / 'budget_curves.md'}")


if __name__ == "__main__":
    main()
