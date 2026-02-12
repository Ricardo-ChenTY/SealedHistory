"""Linkability / re-identification risk proxy for sealed releases.

Threat model angle (W2):
- Attacker sees the *public* sealed text.
- Attacker attempts to link it back to the original item (or external corpus)
  using only surface-level lexical similarity.

We approximate this with a TF-IDF retrieval attack:
  query = (sealed variant) text
  database = raw text (same dataset)

This is not a formal guarantee, but it turns “is it reversible / linkable?” into
hard numbers (hit@k, MRR, mean rank) across release variants.

Outputs (under --output_dir):
- summary.json / summary.md
- run_meta.json
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records


DEFAULT_VARIANTS = ["sealed", "sealed_l1only", "sealed_summary", "sealed_redact"]
DEFAULT_TOP_KS = [1, 5, 10]


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _tokenize(text: str) -> List[str]:
    toks = [t for t in re.findall(r"[A-Za-z0-9_]+", str(text or "").lower()) if t]
    out: List[str] = []
    for t in toks:
        if len(t) < 3:
            continue
        if t.isdigit():
            continue
        out.append(t)
    return out


def _record_text(rec: PaperRecord, *, fields: str) -> str:
    parts: List[str] = [
        str(rec.title or ""),
        str(rec.background or ""),
        str(rec.mechanism or ""),
        str(rec.experiment or ""),
    ]
    if fields == "text":
        return "\n".join(parts).strip()

    year = "" if rec.year is None else str(rec.year)
    venue = "" if rec.venue is None else str(rec.venue)
    authors = " ".join([str(a) for a in (rec.authors or []) if a])
    parts.extend([year, venue, authors])
    return "\n".join(parts).strip()


def _tfidf_index(
    docs: List[str], *, min_df: int, max_df_frac: float
) -> Tuple[Dict[str, float], Dict[str, List[Tuple[int, float]]], List[float]]:
    n_docs = len(docs)
    counters: List[Counter[str]] = []
    df: Counter[str] = Counter()
    for doc in docs:
        c = Counter(_tokenize(doc))
        counters.append(c)
        for t in c.keys():
            df[t] += 1

    idf: Dict[str, float] = {}
    max_df_count = int(math.floor(float(max_df_frac) * float(n_docs)))
    max_df_count = max(1, min(int(n_docs), int(max_df_count)))
    for t, dft in df.items():
        if int(dft) < int(min_df):
            continue
        if int(dft) > int(max_df_count):
            continue
        idf[t] = math.log((n_docs + 1.0) / (float(dft) + 1.0)) + 1.0

    inv: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    norms: List[float] = []
    for idx, c in enumerate(counters):
        sq = 0.0
        for t, tf in c.items():
            if t not in idf:
                continue
            ww = (1.0 + math.log(float(tf))) * float(idf.get(t) or 0.0)
            if ww == 0.0:
                continue
            inv[t].append((idx, ww))
            sq += ww * ww
        norms.append(math.sqrt(sq) if sq > 0 else 0.0)

    return idf, inv, norms


def _tfidf_query(
    query_text: str,
    *,
    idf: Dict[str, float],
    inv: Dict[str, List[Tuple[int, float]]],
    doc_norms: List[float],
    query_top_tokens: int,
) -> Dict[int, float]:
    q_counter = Counter(_tokenize(query_text))
    q_w: Dict[str, float] = {}
    q_sq = 0.0
    for t, tf in q_counter.items():
        ww = (1.0 + math.log(float(tf))) * float(idf.get(t) or 0.0)
        if ww == 0.0:
            continue
        q_w[t] = ww
        q_sq += ww * ww
    if int(query_top_tokens) > 0 and len(q_w) > int(query_top_tokens):
        top = sorted(q_w.items(), key=lambda kv: (-float(kv[1]), str(kv[0])))[: int(query_top_tokens)]
        q_w = {k: float(v) for k, v in top}
        q_sq = sum(float(v) * float(v) for v in q_w.values())

    q_norm = math.sqrt(q_sq) if q_sq > 0 else 0.0
    if q_norm == 0.0:
        return {}

    scores: Dict[int, float] = defaultdict(float)
    for t, qww in q_w.items():
        for doc_idx, dww in inv.get(t, []):
            scores[int(doc_idx)] += float(qww) * float(dww)

    out: Dict[int, float] = {}
    for doc_idx, dot in scores.items():
        denom = float(q_norm) * float(doc_norms[doc_idx] or 0.0)
        if denom == 0.0:
            continue
        out[int(doc_idx)] = float(dot) / denom
    return out


def _compute_metrics(ranks: List[int], *, top_ks: List[int]) -> Dict[str, Any]:
    n = len(ranks)
    if n == 0:
        return {
            "n_queries": 0,
            "hit_at": {str(k): 0.0 for k in top_ks},
            "mrr": 0.0,
            "mean_rank": 0.0,
            "median_rank": 0.0,
        }

    hits: Dict[str, float] = {}
    for k in top_ks:
        hits[str(k)] = round(sum(1 for r in ranks if int(r) <= int(k)) / float(n), 4)

    mrr = round(statistics.mean([1.0 / float(r) for r in ranks]), 6)
    mean_rank = round(statistics.mean([float(r) for r in ranks]), 3)
    median_rank = round(statistics.median([float(r) for r in ranks]), 3)
    return {
        "n_queries": int(n),
        "hit_at": hits,
        "mrr": mrr,
        "mean_rank": mean_rank,
        "median_rank": median_rank,
    }


def _load_scale(dataset_dir: Path, track: str, variant: str) -> List[PaperRecord]:
    if variant == "raw":
        p = dataset_dir / f"track_{track}_raw.jsonl"
    else:
        p = dataset_dir / f"track_{track}_{variant}.jsonl"
    return load_records(p)


def main() -> None:
    p = argparse.ArgumentParser(description="Compute TF-IDF re-identification metrics for sealed release variants.")
    p.add_argument("--dataset_dir", default="runs/EXP-031/public")
    p.add_argument("--output_dir", default="runs/EXP-041")
    p.add_argument("--overwrite", action="store_true")

    p.add_argument("--tracks", default="A,B")
    p.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    p.add_argument("--fields", choices=["text", "text_meta"], default="text")
    p.add_argument("--top_ks", default=",".join([str(k) for k in DEFAULT_TOP_KS]))
    p.add_argument("--min_df", type=int, default=2)
    p.add_argument("--max_df_frac", type=float, default=0.2)
    p.add_argument("--query_top_tokens", type=int, default=64)
    args = p.parse_args()

    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.exists() and bool(args.overwrite):
        for name in ["summary.json", "summary.md", "run_meta.json"]:
            fp = out_dir / name
            if fp.exists():
                fp.unlink()

    tracks = [t.strip() for t in str(args.tracks).split(",") if t.strip()]
    variants = [v.strip() for v in str(args.variants).split(",") if v.strip()]
    top_ks = [int(x.strip()) for x in str(args.top_ks).split(",") if x.strip()]
    top_ks = sorted(set([int(k) for k in top_ks if int(k) >= 1]))

    t0 = time.time()

    per_track: Dict[str, Any] = {}
    for track in tracks:
        raw = _load_scale(dataset_dir, track, "raw")
        raw_by_id = {str(r.paper_id): idx for idx, r in enumerate(raw)}
        raw_docs = [_record_text(r, fields=str(args.fields)) for r in raw]
        idf, inv, raw_norms = _tfidf_index(raw_docs, min_df=int(args.min_df), max_df_frac=float(args.max_df_frac))

        per_variant: Dict[str, Any] = {}
        for variant in variants:
            q_records = _load_scale(dataset_dir, track, variant)
            ranks: List[int] = []
            for q in q_records:
                qid = str(q.paper_id)
                if qid not in raw_by_id:
                    continue
                target_idx = int(raw_by_id[qid])
                q_text = _record_text(q, fields=str(args.fields))
                scores = _tfidf_query(
                    q_text,
                    idf=idf,
                    inv=inv,
                    doc_norms=raw_norms,
                    query_top_tokens=int(args.query_top_tokens),
                )
                target_score = float(scores.get(int(target_idx), 0.0))
                better = sum(1 for s in scores.values() if float(s) > target_score)
                if target_score == 0.0:
                    # Missing keys are zero-score docs; tie-break is by doc_idx ascending.
                    n_nonzero_less = sum(1 for i in scores.keys() if int(i) < int(target_idx))
                    tie_less = int(target_idx) - int(n_nonzero_less)
                else:
                    tie_less = sum(
                        1
                        for i, s in scores.items()
                        if float(s) == target_score and int(i) < int(target_idx)
                    )
                ranks.append(int(better) + int(tie_less) + 1)

            per_variant[str(variant)] = _compute_metrics(ranks, top_ks=top_ks)

        per_track[str(track)] = {"n_raw": int(len(raw)), "variants": per_variant}

    overall: Dict[str, Any] = {}
    for variant in variants:
        hits_at: Dict[str, List[float]] = defaultdict(list)
        mrrs: List[float] = []
        mean_ranks: List[float] = []
        for track in tracks:
            r = ((per_track.get(track) or {}).get("variants") or {}).get(variant) or {}
            for k, v in (r.get("hit_at") or {}).items():
                hits_at[str(k)].append(float(v))
            mrrs.append(float(r.get("mrr") or 0.0))
            mean_ranks.append(float(r.get("mean_rank") or 0.0))
        overall[variant] = {
            "hit_at_avg": {k: round(statistics.mean(vs), 4) if vs else 0.0 for k, vs in sorted(hits_at.items())},
            "mrr_avg": round(statistics.mean(mrrs), 6) if mrrs else 0.0,
            "mean_rank_avg": round(statistics.mean(mean_ranks), 3) if mean_ranks else 0.0,
        }

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "dataset_dir": str(dataset_dir),
            "tracks": tracks,
            "variants": variants,
            "fields": str(args.fields),
            "top_ks": top_ks,
            "min_df": int(args.min_df),
            "max_df_frac": float(args.max_df_frac),
            "query_top_tokens": int(args.query_top_tokens),
        },
        "per_track": per_track,
        "overall": overall,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md: List[str] = [
        "# Linkability / Re-identification (TF-IDF) (EXP-041)",
        "",
        f"- dataset_dir: `{str(dataset_dir)}`",
        f"- tracks: `{', '.join(tracks)}`",
        f"- variants: `{', '.join(variants)}`",
        f"- fields: `{str(args.fields)}`",
        f"- top_ks: `{top_ks}`",
        f"- min_df: `{int(args.min_df)}`",
        f"- max_df_frac: `{float(args.max_df_frac)}`",
        f"- query_top_tokens: `{int(args.query_top_tokens)}`",
        "",
        "## Overall (avg across tracks)",
        "",
        "| Variant | hit@1 | hit@5 | hit@10 | MRR | Mean Rank |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant in variants:
        r = overall.get(variant) or {}
        ha = r.get("hit_at_avg") or {}
        md.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                variant,
                f"{float(ha.get('1', 0.0)):.4f}",
                f"{float(ha.get('5', 0.0)):.4f}",
                f"{float(ha.get('10', 0.0)):.4f}",
                f"{float(r.get('mrr_avg', 0.0)):.6f}",
                f"{float(r.get('mean_rank_avg', 0.0)):.3f}",
            )
        )

    for track in tracks:
        md.extend(
            [
                "",
                f"## Track {track}",
                "",
                "| Variant | hit@1 | hit@5 | hit@10 | MRR | Mean Rank |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        trow = (per_track.get(track) or {}).get("variants") or {}
        for variant in variants:
            r = trow.get(variant) or {}
            ha = r.get("hit_at") or {}
            md.append(
                "| {} | {} | {} | {} | {} | {} |".format(
                    variant,
                    f"{float(ha.get('1', 0.0)):.4f}",
                    f"{float(ha.get('5', 0.0)):.4f}",
                    f"{float(ha.get('10', 0.0)):.4f}",
                    f"{float(r.get('mrr', 0.0)):.6f}",
                    f"{float(r.get('mean_rank', 0.0)):.3f}",
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
        "args": vars(args),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
