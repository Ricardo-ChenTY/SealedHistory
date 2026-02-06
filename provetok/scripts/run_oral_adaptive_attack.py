"""Run adaptive leakage attacks for oral-readiness evidence.

This script implements two deterministic attacker settings:
1) Black-box attacker: sees sealed text only, no codebook.
2) White-box attacker: sees sealed text and codebook mapping.

Metrics:
- retrieval_top1: recover correct raw paper_id via lexical retrieval
- retrieval_top3: top-3 hit rate
- keyword_recovery: recover raw keywords from sealed keywords
- composite_leakage: average of the three metrics
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records


WORD_RE = re.compile(r"[a-z0-9_]+")


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
    base_tokens = _tokenize(" ".join(text_parts))
    if not reverse_map:
        return base_tokens

    restored: List[str] = []
    for tok in base_tokens:
        real = reverse_map.get(tok)
        if real:
            restored.extend(_tokenize(real))
        else:
            restored.append(tok)
    return restored


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _build_raw_index(raw_records: List[PaperRecord]) -> Dict[str, List[str]]:
    return {r.paper_id: _record_tokens(r, reverse_map=None) for r in raw_records if r.paper_id}


def _retrieval_metrics(
    observed: List[PaperRecord],
    raw_index: Dict[str, List[str]],
    reverse_map: Dict[str, str] | None = None,
) -> Tuple[float, float]:
    n = 0
    hit1 = 0
    hit3 = 0
    pids = sorted(raw_index.keys())

    for rec in observed:
        if rec.paper_id not in raw_index:
            continue
        n += 1
        q = _record_tokens(rec, reverse_map=reverse_map)
        scored = [
            (_jaccard(q, raw_index[pid]), pid)
            for pid in pids
        ]
        scored.sort(key=lambda x: (-x[0], x[1]))
        top1 = scored[0][1] if scored else ""
        top3 = {pid for _, pid in scored[:3]}
        if top1 == rec.paper_id:
            hit1 += 1
        if rec.paper_id in top3:
            hit3 += 1

    if n == 0:
        return 0.0, 0.0
    return hit1 / n, hit3 / n


def _keyword_recovery_rate(
    observed: List[PaperRecord],
    raw_by_id: Dict[str, PaperRecord],
    reverse_map: Dict[str, str] | None = None,
) -> float:
    total = 0
    hits = 0
    for rec in observed:
        raw = raw_by_id.get(rec.paper_id)
        if raw is None:
            continue
        raw_kw = {str(k).strip().lower() for k in (raw.keywords or []) if str(k).strip()}
        for kw in (rec.keywords or []):
            total += 1
            src = str(kw).strip().lower()
            guess = reverse_map.get(src, src) if reverse_map else src
            if guess in raw_kw:
                hits += 1
    if total == 0:
        return 0.0
    return hits / total


def _composite(top1: float, top3: float, kw: float) -> float:
    return (top1 + top3 + kw) / 3.0


def _load_reverse_map(codebook_path: Path | None) -> Dict[str, str]:
    if codebook_path is None or not codebook_path.exists():
        return {}
    obj = json.loads(codebook_path.read_text(encoding="utf-8"))
    forward = obj.get("forward") or {}
    reverse = {str(v).strip().lower(): str(k).strip().lower() for k, v in forward.items()}
    return reverse


def run_adaptive_attack(
    sealed_path: Path,
    raw_path: Path,
    codebook_path: Path | None = None,
) -> dict:
    sealed = load_records(sealed_path)
    raw = load_records(raw_path)
    raw_index = _build_raw_index(raw)
    raw_by_id = {r.paper_id: r for r in raw}

    black_top1, black_top3 = _retrieval_metrics(sealed, raw_index, reverse_map=None)
    black_kw = _keyword_recovery_rate(sealed, raw_by_id, reverse_map=None)

    reverse = _load_reverse_map(codebook_path)
    if reverse:
        white_top1, white_top3 = _retrieval_metrics(sealed, raw_index, reverse_map=reverse)
        white_kw = _keyword_recovery_rate(sealed, raw_by_id, reverse_map=reverse)
    else:
        white_top1, white_top3, white_kw = black_top1, black_top3, black_kw

    return {
        "n_records": len([r for r in sealed if r.paper_id in raw_by_id]),
        "black_box": {
            "retrieval_top1": round(black_top1, 4),
            "retrieval_top3": round(black_top3, 4),
            "keyword_recovery": round(black_kw, 4),
            "composite_leakage": round(_composite(black_top1, black_top3, black_kw), 4),
        },
        "white_box": {
            "retrieval_top1": round(white_top1, 4),
            "retrieval_top3": round(white_top3, 4),
            "keyword_recovery": round(white_kw, 4),
            "composite_leakage": round(_composite(white_top1, white_top3, white_kw), 4),
        },
        "assumptions": {
            "black_box": "No codebook, only sealed public text.",
            "white_box": "Attacker additionally has codebook mapping.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run adaptive black-box/white-box leakage attacks.")
    parser.add_argument("--sealed", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--codebook", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = run_adaptive_attack(
        sealed_path=Path(args.sealed),
        raw_path=Path(args.raw),
        codebook_path=Path(args.codebook) if args.codebook else None,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Adaptive attack report saved to {out}")
    print(
        "black_box(composite)={:.4f}, white_box(composite)={:.4f}".format(
            result["black_box"]["composite_leakage"],
            result["white_box"]["composite_leakage"],
        )
    )


if __name__ == "__main__":
    main()
