"""Run contamination tagging traceability diagnostics (DyePack-style proxy)."""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

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


def _keyword_index(records: List[PaperRecord]) -> Dict[str, Set[str]]:
    index: Dict[str, Set[str]] = {}
    for rec in records:
        pid = str(rec.paper_id or "")
        if not pid:
            continue
        for kw in rec.keywords or []:
            tok = str(kw or "").strip().lower()
            if not tok:
                continue
            index.setdefault(tok, set()).add(pid)
    return index


def _primary_tag(rec: PaperRecord, token_index: Dict[str, Set[str]]) -> str:
    cands: List[tuple[int, str]] = []
    for kw in rec.keywords or []:
        tok = str(kw or "").strip().lower()
        if tok in token_index:
            cands.append((len(token_index[tok]), tok))
    if not cands:
        return ""
    cands.sort(key=lambda x: (x[0], x[1]))
    return str(cands[0][1])


def _collect_negative_queries(
    records: List[PaperRecord],
    *,
    keyword_vocab: Set[str],
    max_negatives: int,
) -> List[str]:
    negs: List[str] = []
    seen: Set[str] = set()
    for rec in records:
        toks = _tokenize(" ".join([str(rec.title or ""), str(rec.background or ""), str(rec.mechanism or "")]))
        for tok in toks:
            if tok in keyword_vocab:
                continue
            if tok in seen:
                continue
            if len(tok) < 4:
                continue
            seen.add(tok)
            negs.append(tok)
            if len(negs) >= int(max_negatives):
                return negs
    return negs


def _summarize_track(records: List[PaperRecord], *, max_negatives: int) -> dict:
    token_index = _keyword_index(records)
    vocab = set(token_index.keys())

    n_records = len(records)
    n_with_keywords = sum(1 for r in records if (r.keywords or []))
    n_assignable = 0
    n_traceable = 0
    n_ambiguous = 0
    top1_hits = 0

    rows_preview: List[dict] = []
    for rec in records:
        pid = str(rec.paper_id or "")
        if not pid:
            continue
        tag = _primary_tag(rec, token_index)
        if not tag:
            continue
        n_assignable += 1
        owners = sorted(token_index.get(tag, set()))
        if len(owners) == 1:
            n_traceable += 1
        else:
            n_ambiguous += 1
        pred = owners[0] if owners else ""
        top1_hits += 1 if pred == pid else 0
        if len(rows_preview) < 20:
            rows_preview.append(
                {
                    "paper_id": pid,
                    "tag": tag,
                    "n_candidate_papers": len(owners),
                    "top1_prediction": pred,
                    "top1_hit": bool(pred == pid),
                }
            )

    negatives = _collect_negative_queries(records, keyword_vocab=vocab, max_negatives=max_negatives)
    false_pos = 0
    for q in negatives:
        owners = token_index.get(q, set())
        if len(owners) == 1:
            false_pos += 1

    return {
        "n_records": n_records,
        "n_records_with_keywords": n_with_keywords,
        "n_keyword_tokens": sum(len(v) for v in token_index.values()),
        "n_unique_tags": sum(1 for _, v in token_index.items() if len(v) == 1),
        "n_assignable_records": n_assignable,
        "traceable_coverage": round(n_traceable / n_records, 4) if n_records else 0.0,
        "assignable_traceability_rate": round(n_traceable / n_assignable, 4) if n_assignable else 0.0,
        "ambiguity_rate_on_assignable": round(n_ambiguous / n_assignable, 4) if n_assignable else 0.0,
        "top1_traceability_accuracy": round(top1_hits / n_assignable, 4) if n_assignable else 0.0,
        "negative_query_count": len(negatives),
        "false_positive_rate_on_negatives": round(false_pos / len(negatives), 4) if negatives else 0.0,
        "preview": rows_preview,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run contamination tagging traceability diagnostics.")
    parser.add_argument("--dataset_dir", default="runs/EXP-031/public")
    parser.add_argument("--output_dir", default="runs/EXP-036")
    parser.add_argument("--max_negatives", type=int, default=300)
    args = parser.parse_args()

    t0 = time.time()
    dataset_dir = Path(args.dataset_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_track: Dict[str, dict] = {}
    for track in ["A", "B"]:
        sealed_path = dataset_dir / f"track_{track}_sealed.jsonl"
        records = load_records(sealed_path)
        per_track[track] = _summarize_track(records, max_negatives=int(args.max_negatives))

    trace_cov = [float(v["traceable_coverage"]) for v in per_track.values()]
    amb_rates = [float(v["ambiguity_rate_on_assignable"]) for v in per_track.values()]
    fpr = [float(v["false_positive_rate_on_negatives"]) for v in per_track.values()]

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_dir": str(dataset_dir),
        "per_track": per_track,
        "overall": {
            "mean_traceable_coverage": round(statistics.mean(trace_cov), 4) if trace_cov else 0.0,
            "mean_ambiguity_rate_on_assignable": round(statistics.mean(amb_rates), 4) if amb_rates else 0.0,
            "mean_false_positive_rate_on_negatives": round(statistics.mean(fpr), 4) if fpr else 0.0,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Contamination Tagging Traceability (EXP-036)",
        "",
        f"- dataset_dir: `{dataset_dir}`",
        f"- max_negatives: `{int(args.max_negatives)}`",
        "",
        "| Track | N | Traceable Coverage | Ambiguity Rate | Top1 Accuracy | FPR (negatives) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for track in ["A", "B"]:
        row = per_track.get(track, {})
        md.append(
            "| {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(
                track,
                int(row.get("n_records", 0)),
                float(row.get("traceable_coverage", 0.0)),
                float(row.get("ambiguity_rate_on_assignable", 0.0)),
                float(row.get("top1_traceability_accuracy", 0.0)),
                float(row.get("false_positive_rate_on_negatives", 0.0)),
            )
        )
    md.extend(
        [
            "",
            "## Overall",
            f"- mean_traceable_coverage: `{summary['overall']['mean_traceable_coverage']}`",
            f"- mean_ambiguity_rate_on_assignable: `{summary['overall']['mean_ambiguity_rate_on_assignable']}`",
            f"- mean_false_positive_rate_on_negatives: `{summary['overall']['mean_false_positive_rate_on_negatives']}`",
        ]
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
        "max_negatives": int(args.max_negatives),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved: {out_dir / 'summary.json'}")
    print(f"Saved: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()

