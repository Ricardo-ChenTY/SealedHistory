"""LLM-based validity/invariance diagnostics (raw vs sealed vs metadata-only).

This addresses reviewer concerns that:
- "metadata/statistics alone can get high scores" (validity),
- sealed transforms introduce reversible patterns that strong attackers exploit.

We run a temperature-0 LLM proposer on multiple views and score outputs with the
same rubric used elsewhere in the repo (heuristic MVP rubric).

Outputs (under --out_dir):
- summary.json / summary.md
- run_meta.json
- items.jsonl (per-item traces; safe excerpts only, no secrets)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records
from provetok.eval.rubric import AutoRubricScorer, RubricWeights
from provetok.utils.llm_client import LLMClient, LLMConfig


DEFAULT_VIEWS = ["raw", "sealed", "structure_only", "metadata_only"]


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _sha256_text(s: str) -> str:
    return hashlib.sha256(str(s or "").encode("utf-8")).hexdigest()


def _require_api_key() -> Tuple[str, str]:
    # Prefer OPENAI_* envs (matches repo .env); fallback to LLM_* envs.
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key, "OPENAI_API_KEY"
    key = os.environ.get("LLM_API_KEY", "").strip()
    if key:
        return key, "LLM_API_KEY"
    raise RuntimeError("Missing LLM API key: set OPENAI_API_KEY (preferred) or LLM_API_KEY")


def _normalize_api_base(api_base: str) -> str:
    s = str(api_base or "").strip().rstrip("/")
    if not s:
        return s
    if s.endswith("/v1"):
        return s
    return s + "/v1"


def _clone_record(rec: PaperRecord) -> PaperRecord:
    return PaperRecord.from_dict(rec.to_dict())


def _structure_only_view(records: List[PaperRecord]) -> List[PaperRecord]:
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.title = str(d.title or "")
        d.background = ""
        d.mechanism = ""
        d.experiment = ""
        d.keywords = []
        out.append(d)
    return out


def _metadata_only_view(records: List[PaperRecord]) -> List[PaperRecord]:
    out: List[PaperRecord] = []
    for rec in records:
        d = _clone_record(rec)
        d.title = str(d.title or "")
        d.background = ""
        d.mechanism = ""
        d.experiment = ""
        d.dependencies = []
        d.keywords = []
        out.append(d)
    return out


def _truncate(s: str, n: int) -> str:
    t = str(s or "").replace("\n", " ").strip()
    if len(t) <= int(n):
        return t
    return t[: int(n)].rstrip() + "…"


def _format_context(records: List[PaperRecord], *, k: int) -> str:
    view = records[-int(k) :] if k > 0 else records
    lines: List[str] = []
    for rec in view:
        deps = ", ".join([str(x) for x in (rec.dependencies or [])][:8])
        year = "" if rec.year is None else str(rec.year)
        venue = "" if rec.venue is None else str(rec.venue)
        header = f"[{rec.paper_id}] phase={rec.phase} year={year} venue={venue}"
        lines.append(header)
        lines.append(f"  title: {_truncate(rec.title, 120)}")
        if rec.background:
            lines.append(f"  background: {_truncate(rec.background, 220)}")
        if rec.mechanism:
            lines.append(f"  mechanism: {_truncate(rec.mechanism, 220)}")
        if rec.experiment:
            lines.append(f"  experiment: {_truncate(rec.experiment, 180)}")
        if deps:
            lines.append(f"  dependencies: {deps}")
    return "\n".join(lines).strip()


def _parse_float(s: str) -> float:
    m = re.search(r"[-+]?(?:\d+\.\d+|\d+)", str(s or ""))
    return float(m.group(0)) if m else 0.0


def _parse_deps(s: str) -> List[str]:
    t = str(s or "").strip()
    if "[" in t and "]" in t:
        i = t.find("[")
        j = t.rfind("]")
        if 0 <= i < j:
            t = t[i + 1 : j]
    parts = [p.strip() for p in re.split(r"[,\n]+", t) if p.strip()]
    out: List[str] = []
    for p in parts:
        tok = re.sub(r"[^A-Za-z0-9_:\\-]+", "", p)
        if tok:
            out.append(tok)
    # stable order, de-dup
    seen = set()
    uniq = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq[:12]


def _parse_fields(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    # Accept both "KEY: ..." and "KEY = ..." styles, and tolerate keys appearing
    # on a single line.
    fields = {
        "title": "",
        "background": "",
        "mechanism": "",
        "experiment_plan": "",
        "predicted_improvement": 0.0,
        "dependencies": [],
    }

    pat = re.compile(
        r"(TITLE|BACKGROUND|MECHANISM|EXPERIMENT_PLAN|PREDICTED_IMPROVEMENT|DEPENDENCIES)\s*[:=]\s*",
        re.I,
    )
    matches = list(pat.finditer(raw))
    by_key: Dict[str, str] = {}
    for i, m in enumerate(matches):
        key = str(m.group(1) or "").strip().upper()
        start = int(m.end())
        end = int(matches[i + 1].start()) if i + 1 < len(matches) else len(raw)
        val = str(raw[start:end]).strip()
        if key:
            by_key[key] = val

    fields["title"] = by_key.get("TITLE", "")
    fields["background"] = by_key.get("BACKGROUND", "")
    fields["mechanism"] = by_key.get("MECHANISM", "")
    fields["experiment_plan"] = by_key.get("EXPERIMENT_PLAN", "")
    fields["predicted_improvement"] = _parse_float(by_key.get("PREDICTED_IMPROVEMENT", "0"))
    fields["dependencies"] = _parse_deps(by_key.get("DEPENDENCIES", ""))
    return fields


def _feedback_from_target(target: PaperRecord) -> Dict[str, Any]:
    extra = getattr(target.results, "extra", {}) or {}
    ablations: Dict[str, float] = {}
    if isinstance(extra, dict):
        for k, v in extra.items():
            if isinstance(v, (int, float)):
                ablations[str(k)] = float(v)
    return {
        "success": True,
        "delta_vs_baseline": float(getattr(target.results, "delta_vs_prev", 0.0) or 0.0),
        "ablation_results": ablations,
        "notes": {"target_paper_id": target.paper_id, "target_phase": target.phase},
    }


def _score_one(
    *,
    scorer: AutoRubricScorer,
    weights: RubricWeights,
    accept_threshold: float,
    proposal_fields: Dict[str, Any],
    target: PaperRecord,
) -> Dict[str, Any]:
    proposal = {
        "title": str(proposal_fields.get("title") or ""),
        "background": str(proposal_fields.get("background") or ""),
        "mechanism": str(proposal_fields.get("mechanism") or ""),
        "experiment_plan": str(proposal_fields.get("experiment_plan") or ""),
        "predicted_improvement": float(proposal_fields.get("predicted_improvement") or 0.0),
        "dependencies": [str(x) for x in (proposal_fields.get("dependencies") or []) if str(x).strip()],
    }
    feedback = _feedback_from_target(target)
    rub = scorer.score_proposal(proposal, feedback, target=target)
    total = float(rub.weighted_total(weights))
    accepted = bool(total >= float(accept_threshold))
    out = {
        "accepted": accepted,
        "rubric": rub.to_dict(),
        "total": round(total, 4),
        "threshold": float(accept_threshold),
    }
    return out


def _run_view(
    *,
    llm: LLMClient,
    model_name: str,
    view_name: str,
    track: str,
    observed: List[PaperRecord],
    raw: List[PaperRecord],
    n_items: int,
    context_k: int,
    accept_threshold: float,
    max_tokens: int,
    sleep_sec: float,
    progress: Dict[str, int],
    progress_every: int,
    items_fh,
) -> Tuple[Dict[str, Any], List[dict], Dict[str, int]]:
    prompt_template = (
        "You are a research scientist working in a sealed domain. "
        "You can only use the papers shown below.\n\n"
        "PAPERS (most recent last):\n{context}\n\n"
        "Task: propose the next research paper that logically follows.\n"
        "Requirements:\n"
        "- Identify a limitation in existing work\n"
        "- Propose a mechanism to address it\n"
        "- Specify dependencies as paper_ids\n"
        "- Provide a predicted_improvement float (negative allowed)\n\n"
        "Output EXACTLY these 6 lines (no extra text):\n"
        "TITLE: ...\n"
        "BACKGROUND: ...\n"
        "MECHANISM: ...\n"
        "EXPERIMENT_PLAN: ...\n"
        "PREDICTED_IMPROVEMENT: 0.05\n"
        "DEPENDENCIES: [paper_id_1, paper_id_2]\n"
    )

    scorer = AutoRubricScorer(weights=RubricWeights())
    weights = scorer.weights

    items: List[dict] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    n = min(int(n_items), len(raw), len(observed))
    for idx in range(n):
        progress["n_calls"] += 1
        if int(progress_every) > 0 and progress["n_calls"] % int(progress_every) == 0:
            print(
                f"LLM calls: {int(progress['n_calls'])} "
                f"(dataset={str(model_name)} track={str(track)} view={str(view_name)} "
                f"idx={int(idx) + 1}/{int(n)})"
            )
        ctx_records = observed[: idx + 1]
        context = _format_context(ctx_records, k=int(context_k))
        prompt = prompt_template.format(context=context)

        resp = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=int(max_tokens))
        for kk in usage_total:
            usage_total[kk] += int((resp.usage or {}).get(kk) or 0)

        fields = _parse_fields(resp.content)
        target = raw[idx]
        scored = _score_one(
            scorer=scorer,
            weights=weights,
            accept_threshold=float(accept_threshold),
            proposal_fields=fields,
            target=target,
        )

        item = {
            "dataset": model_name,
            "track": str(track),
            "view": str(view_name),
            "item_idx": int(idx),
            "paper_id": str(getattr(observed[idx], "paper_id", "") or ""),
            "target_paper_id": str(getattr(target, "paper_id", "") or ""),
            "prompt_sha256": _sha256_text(prompt),
            "response_excerpt": _truncate(resp.content, 320),
            "parsed": {
                "predicted_improvement": float(fields.get("predicted_improvement") or 0.0),
                "n_deps": len(fields.get("dependencies") or []),
            },
            "rubric": dict(scored.get("rubric") or {}),
            "total": float(scored.get("total") or 0.0),
            "accepted": bool(scored.get("accepted")),
        }
        items.append(item)
        items_fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        items_fh.flush()

        if float(sleep_sec) > 0:
            time.sleep(float(sleep_sec))

    totals = [float(it["total"]) for it in items]
    accepts = [1.0 if bool(it["accepted"]) else 0.0 for it in items]

    per_dim: Dict[str, List[float]] = {}
    for it in items:
        for k, v in (it.get("rubric") or {}).items():
            per_dim.setdefault(str(k), []).append(float(v))

    summary = {
        "n_items": len(items),
        "utility_mean": round(statistics.mean(totals), 4) if totals else 0.0,
        "utility_std": round(statistics.pstdev(totals), 4) if len(totals) >= 2 else 0.0,
        "accept_rate": round(statistics.mean(accepts), 4) if accepts else 0.0,
        "per_dimension_avg": {
            k: round(statistics.mean(vs), 4) if vs else 0.0 for k, vs in sorted(per_dim.items())
        },
    }
    return summary, items, usage_total


def _load_micro(track: str) -> Tuple[List[PaperRecord], List[PaperRecord]]:
    raw_path = Path(f"provetok/data/raw/micro_history_{track.lower()}.jsonl")
    sealed_path = Path(f"provetok/data/sealed/micro_history_{track.lower()}.sealed.jsonl")
    raw = load_records(raw_path)
    sealed = load_records(sealed_path)
    return raw, sealed


def _load_scale(dataset_dir: Path, track: str) -> Tuple[List[PaperRecord], List[PaperRecord]]:
    raw_path = dataset_dir / f"track_{track}_raw.jsonl"
    sealed_path = dataset_dir / f"track_{track}_sealed.jsonl"
    raw = load_records(raw_path)
    sealed = load_records(sealed_path)
    return raw, sealed


def main() -> None:
    p = argparse.ArgumentParser(description="Run LLM validity/invariance diagnostics across multiple views.")
    p.add_argument("--out_dir", default="runs/EXP-040")
    p.add_argument("--overwrite", action="store_true")

    p.add_argument("--tracks", default="A,B")
    p.add_argument("--views", default=",".join(DEFAULT_VIEWS))

    p.add_argument("--scale_dataset_dir", default="runs/EXP-031/public")
    p.add_argument("--skip_scale", action="store_true")

    p.add_argument("--n_items_micro", type=int, default=12)
    p.add_argument("--n_items_scale", type=int, default=8)
    p.add_argument("--context_k", type=int, default=4)
    p.add_argument("--accept_threshold", type=float, default=0.5)

    p.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "deepseek-chat"))
    p.add_argument("--api_base", default=os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1"))
    p.add_argument("--timeout_sec", type=int, default=60)
    p.add_argument("--sleep_sec", type=float, default=0.2)
    p.add_argument("--progress_every", type=int, default=8)
    p.add_argument("--max_tokens", type=int, default=380)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.overwrite:
        for name in ["summary.json", "summary.md", "run_meta.json", "items.jsonl"]:
            pth = out_dir / name
            if pth.exists():
                pth.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key, api_key_env_used = _require_api_key()
    api_base = _normalize_api_base(str(args.api_base))
    llm = LLMClient(
        LLMConfig(
            model=str(args.model),
            api_base=api_base,
            api_key=api_key,
            temperature=0.0,
            max_tokens=int(args.max_tokens),
            timeout=int(args.timeout_sec),
        )
    )
    if not llm.is_configured():
        raise RuntimeError("LLM client not configured; ensure `openai` is installed and API key/base URL are valid")

    tracks = [t.strip() for t in str(args.tracks).split(",") if t.strip()]
    views = [v.strip() for v in str(args.views).split(",") if v.strip()]

    t0 = time.time()

    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    items_all: List[dict] = []
    progress = {"n_calls": 0}

    micro: Dict[str, Any] = {}
    items_fh = open(out_dir / "items.jsonl", "w", encoding="utf-8")
    for track in tracks:
        raw, sealed = _load_micro(track)
        view_map = {
            "raw": raw,
            "sealed": sealed,
            "structure_only": _structure_only_view(sealed),
            "metadata_only": _metadata_only_view(sealed),
        }
        per_view = {}
        for view_name in views:
            if view_name not in view_map:
                continue
            s, items, usage = _run_view(
                llm=llm,
                model_name="micro",
                view_name=view_name,
                track=track,
                observed=view_map[view_name],
                raw=raw,
                n_items=int(args.n_items_micro),
                context_k=int(args.context_k),
                accept_threshold=float(args.accept_threshold),
                max_tokens=int(args.max_tokens),
                sleep_sec=float(args.sleep_sec),
                progress=progress,
                progress_every=int(args.progress_every),
                items_fh=items_fh,
            )
            per_view[view_name] = s
            items_all.extend(items)
            for kk in usage_total:
                usage_total[kk] += int(usage.get(kk) or 0)
        micro[track] = {"per_view": per_view}

    scale: Dict[str, Any] = {}
    if not bool(args.skip_scale):
        dataset_dir = Path(args.scale_dataset_dir)
        for track in tracks:
            raw, sealed = _load_scale(dataset_dir, track)
            view_map = {
                "raw": raw,
                "sealed": sealed,
                "structure_only": _structure_only_view(sealed),
                "metadata_only": _metadata_only_view(sealed),
            }
            per_view = {}
            for view_name in views:
                if view_name not in view_map:
                    continue
                s, items, usage = _run_view(
                    llm=llm,
                    model_name="scale",
                    view_name=view_name,
                    track=track,
                    observed=view_map[view_name],
                    raw=raw,
                    n_items=int(args.n_items_scale),
                    context_k=int(args.context_k),
                    accept_threshold=float(args.accept_threshold),
                    max_tokens=int(args.max_tokens),
                    sleep_sec=float(args.sleep_sec),
                    progress=progress,
                    progress_every=int(args.progress_every),
                    items_fh=items_fh,
                )
                per_view[view_name] = s
                items_all.extend(items)
                for kk in usage_total:
                    usage_total[kk] += int(usage.get(kk) or 0)
            scale[track] = {"per_view": per_view}

    items_fh.close()

    summary = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "llm": {
                "model": str(args.model),
                "api_base": str(api_base),
                "api_key_env_used": api_key_env_used,
            },
            "tracks": tracks,
            "views": views,
            "n_items_micro": int(args.n_items_micro),
            "n_items_scale": int(args.n_items_scale),
            "context_k": int(args.context_k),
            "accept_threshold": float(args.accept_threshold),
            "max_tokens": int(args.max_tokens),
            "timeout_sec": int(args.timeout_sec),
            "sleep_sec": float(args.sleep_sec),
            "progress_every": int(args.progress_every),
            "usage_total": usage_total,
        },
        "micro": micro,
        "scale": scale,
        "items_preview": items_all[:12],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _fmt(v: float) -> str:
        return f"{float(v):.4f}"

    md: List[str] = [
        "# LLM Validity / Invariance (EXP-040)",
        "",
        f"- model: `{str(args.model)}`",
        f"- api_base: `{str(api_base)}`",
        f"- tracks: `{', '.join(tracks)}`",
        f"- views: `{', '.join(views)}`",
        f"- context_k: `{int(args.context_k)}`",
        f"- n_items_micro: `{int(args.n_items_micro)}`",
        f"- n_items_scale: `{int(args.n_items_scale)}`",
        f"- usage_total: `{usage_total}`",
        "",
        "## Micro",
        "",
        "| Track | View | Utility Mean | Utility Std | Accept Rate |",
        "|---|---|---:|---:|---:|",
    ]
    for track in tracks:
        per_view = (micro.get(track) or {}).get("per_view") or {}
        for view_name in views:
            if view_name not in per_view:
                continue
            r = per_view[view_name]
            md.append(
                "| {} | {} | {} | {} | {} |".format(
                    track,
                    view_name,
                    _fmt(r.get("utility_mean", 0.0)),
                    _fmt(r.get("utility_std", 0.0)),
                    _fmt(r.get("accept_rate", 0.0)),
                )
            )

    if scale:
        md.extend(
            [
                "",
                "## Scale",
                "",
                "| Track | View | Utility Mean | Utility Std | Accept Rate |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for track in tracks:
            per_view = (scale.get(track) or {}).get("per_view") or {}
            for view_name in views:
                if view_name not in per_view:
                    continue
                r = per_view[view_name]
                md.append(
                    "| {} | {} | {} | {} | {} |".format(
                        track,
                        view_name,
                        _fmt(r.get("utility_mean", 0.0)),
                        _fmt(r.get("utility_std", 0.0)),
                        _fmt(r.get("accept_rate", 0.0)),
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
