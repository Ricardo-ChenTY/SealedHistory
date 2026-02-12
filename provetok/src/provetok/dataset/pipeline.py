"""Online dataset pipeline (S2/arXiv).

This pipeline is best-effort: it aims to produce all plan.md artifacts, while
remaining runnable without network (via `--offline` and cached snapshots).
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
import time
import copy
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import (
    PaperRecordInternalV2,
    load_records_internal_v2,
    save_records_internal_v2,
    save_records_v2,
)
from provetok.dataset.fulltext import cache_fulltext_for_mapping_rows, write_fulltext_index_for_mapping_rows
from provetok.dataset.formula_graph import extract_formula_graph_from_source_paths
from provetok.dataset.legacy import default_taxonomy
from provetok.dataset.paths import DatasetPaths
from provetok.dataset.record_builder import build_record_v2_from_abstract
from provetok.dataset.selection import (
    assign_local_ids,
    derive_dependency_closed_core_paper_ids,
    load_manual_decisions,
    match_manual_decision,
    parse_s2_work,
    select_works,
)
from provetok.sources.http import SnapshotWriter
from provetok.sources.s2_client import S2Client, S2Config
from provetok.utils.llm_client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


_INT_RE = re.compile(r"^[+-]?\d+$")


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    s = str(value).strip()
    if not s:
        return None
    if _INT_RE.fullmatch(s):
        return int(s)
    return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_jsonl_snapshot(path: Path) -> List[Dict[str, Any]]:
    works: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                works.append(json.loads(line))
    return works


def _build_s2_query(track_cfg: Dict[str, Any], *, track_id: str) -> Dict[str, Any]:
    """Build S2 query parameters from track config."""
    s2 = track_cfg.get("s2") or {}

    keywords = [str(x).strip() for x in (s2.get("keywords") or []) if str(x).strip()]
    query = str(s2.get("query") or "").strip()
    if not query:
        # Keep query simple for broad gateway compatibility.
        query = keywords[0] if keywords else ""
    if not query:
        # Safe fallback: keep query deterministic even when config omits keywords.
        query = "computer vision transformers" if track_id == "A" else "language model transformers"

    fos = s2.get("fields_of_study") or []
    if isinstance(fos, str):
        fos = [fos]
    fos = [str(x).strip() for x in fos if str(x).strip()]
    fields_of_study = ",".join(fos) if fos else ""

    year_from = _parse_int(s2.get("year_from"))
    year_to = _parse_int(s2.get("year_to"))
    year = ""
    if year_from is not None and year_to is not None:
        year = f"{year_from}-{year_to}"
    elif year_from is not None:
        year = f"{year_from}-"
    elif year_to is not None:
        year = f"-{year_to}"

    min_citation_count = _parse_int(s2.get("min_citation_count"))
    open_access_pdf_only = bool(s2.get("open_access_pdf_only", False))
    max_results = _parse_int(s2.get("max_results"))
    if max_results is None or max_results <= 0:
        max_results = 10000

    return {
        "query": query,
        "fields_of_study": fields_of_study,
        "year": year,
        "min_citation_count": min_citation_count,
        "open_access_pdf_only": open_access_pdf_only,
        "max_results": int(max_results),
    }


def build_online_dataset(raw_cfg: Dict[str, Any], paths: DatasetPaths, offline: bool, track: str) -> None:
    targets = ["A", "B"] if track == "both" else [track]

    # Always write a public taxonomy scaffold (also used to normalize tags).
    taxonomy = default_taxonomy()
    _write_json(paths.public_dir / "taxonomy.json", taxonomy)

    def _sha256_json(obj: Any) -> str:
        blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    sources_cfg = raw_cfg.get("sources") or {}
    s2_cfg_raw = sources_cfg.get("s2") or {}
    primary_source = str(sources_cfg.get("primary", "s2")).strip().lower()
    if primary_source != "s2":
        logger.warning("Unsupported sources.primary=%s; forcing s2 mode", primary_source)
        primary_source = "s2"
    logger.info("Dataset online source backend: %s", primary_source)

    s2_api_key_env = str(s2_cfg_raw.get("api_key_env", "S2_API_KEY"))
    s2_api_key = os.environ.get(s2_api_key_env, "")
    s2_cfg = S2Config(
        base_url=str(s2_cfg_raw.get("base_url", "https://ai4scholar.net/graph/v1")),
        api_key=s2_api_key,
        rate_limit_qps=float(s2_cfg_raw.get("rate_limit_qps", 1.0)),
    )
    s2_enable_batch_enrich = bool(s2_cfg_raw.get("enable_batch_enrich", True))
    s2_batch_chunk = int(s2_cfg_raw.get("batch_chunk_size", 500) or 500)
    if s2_batch_chunk <= 0:
        s2_batch_chunk = 500
    if s2_batch_chunk > 500:
        s2_batch_chunk = 500

    manual_path = str((raw_cfg.get("selection") or {}).get("manual_decisions_file") or "")
    manual_decisions = load_manual_decisions(Path(manual_path)) if manual_path else {}

    sel_cfg = raw_cfg.get("selection") or {}
    topic_k = int(sel_cfg.get("topic_coverage_k", 8))
    centrality_weights = dict(sel_cfg.get("centrality_weights") or {"pagerank": 1.0, "indegree": 0.5})

    track_cfg = raw_cfg.get("tracks") or {}

    selection_rows_by_tier: Dict[str, List[Dict[str, Any]]] = {"extended": [], "core": []}
    dep_edges_by_tier: Dict[str, List[str]] = {"extended": [], "core": []}

    def _confidence_score(row: Dict[str, Any]) -> float:
        """Compute a deterministic, publish-safe confidence score in [0, 1].

        This score is used for *internal* prioritization (e.g. selecting the
        dependency-closed core subset from the extended pool). It must never
        depend on any non-deterministic model outputs.
        """

        abstract = str(row.get("abstract") or "")
        abs_len = len(abstract.strip())
        has_abstract = abs_len >= 200

        s2_enriched = bool(row.get("s2_id"))
        has_doi = bool(row.get("doi"))
        has_arxiv = bool(row.get("arxiv_id"))

        has_ft = bool(row.get("pdf_sha256")) or bool(row.get("source_paths") or [])

        cited = int(row.get("cited_by_count", 0) or 0)

        score = 0.0
        score += 0.30 if has_abstract else (0.15 if abs_len > 0 else 0.0)
        score += 0.20 if s2_enriched else 0.0
        score += 0.10 if has_doi else 0.0
        score += 0.10 if has_arxiv else 0.0
        score += 0.25 if has_ft else 0.0
        # Tiny bump for highly-cited works (stabilizes core selection when other signals tie).
        if cited >= 1000:
            score += 0.05
        elif cited >= 200:
            score += 0.03
        elif cited >= 50:
            score += 0.01

        return max(0.0, min(1.0, float(score)))

    def _normalize_doi(doi: Optional[str]) -> str:
        s = str(doi or "").strip()
        if not s:
            return ""
        low = s.lower()
        for prefix in ("https://doi.org/", "http://doi.org/"):
            if low.startswith(prefix):
                s = s[len(prefix) :]
                break
        if s.lower().startswith("doi:"):
            s = s[4:]
        return s.strip().lower()

    def _normalize_arxiv_id(arxiv_id: Optional[str]) -> str:
        s = str(arxiv_id or "").strip()
        if not s:
            return ""
        low = s.lower()
        if low.startswith("arxiv:"):
            s = s[6:]
        return s.strip().lower()

    # ------------------------------------------------------------------
    # Strict record build configuration (LLM + paraphrase policy)
    rb = raw_cfg.get("record_build") or {}
    llm_mode = str(rb.get("mode", "llm"))
    require_llm = bool(rb.get("require_llm", False))
    strict_paraphrase = bool(rb.get("strict_paraphrase", False))
    max_retries = int(rb.get("max_retries", 0) or 0)
    prompt_version = str(rb.get("prompt_version") or "")
    forbid_names = bool(rb.get("forbid_names", False))
    name_allowlist = rb.get("name_allowlist") or []
    if not isinstance(name_allowlist, list):
        name_allowlist = []

    if strict_paraphrase and not require_llm:
        raise ValueError("record_build.strict_paraphrase=true requires record_build.require_llm=true")

    llm: Optional[LLMClient] = None
    if llm_mode == "llm":
        if offline:
            if require_llm:
                raise ValueError("offline mode is not compatible with record_build.require_llm=true")
            logger.info("Offline mode: LLM disabled; using deterministic fallbacks")
        else:
            api_key_env = str(rb.get("llm_api_key_env", "LLM_API_KEY"))
            api_key = os.environ.get(api_key_env, "")
            if not api_key:
                if require_llm:
                    raise RuntimeError(
                        f"record_build.require_llm=true but {api_key_env} is empty; set the env var to enable LLM record builds"
                    )
                logger.info("LLM disabled: %s is empty; using deterministic fallbacks", api_key_env)
            else:
                candidate = LLMClient(
                    LLMConfig(
                        model=str(rb.get("llm_model", "deepseek-chat")),
                        api_base=str(rb.get("llm_api_base", "https://api.deepseek.com/v1")),
                        api_key=api_key,
                        temperature=0.0,
                    )
                )
                if not candidate.is_configured():
                    if require_llm:
                        raise RuntimeError(
                            "record_build.require_llm=true but LLM client is not configured; ensure `openai` is installed and the API key is valid"
                        )
                    logger.warning("LLM client not configured; falling back to deterministic placeholders")
                else:
                    llm = candidate
    elif require_llm or strict_paraphrase:
        raise ValueError("record_build.require_llm/strict_paraphrase require record_build.mode=llm")

    # Fulltext selection strictness (plan.md hard constraint when enabled).
    ft_cfg = raw_cfg.get("fulltext") or {}
    ext_ft_cfg = ft_cfg.get("extended") or {}
    if not isinstance(ext_ft_cfg, dict):
        ext_ft_cfg = {}
    require_fulltext_success = bool(ext_ft_cfg.get("require_success", ft_cfg.get("require_success", False)))

    # Backfill knobs: how many candidates to consider and batch fulltext downloads.
    pool_mult = float(sel_cfg.get("backfill_pool_multiplier", 5.0))
    batch_size = int(sel_cfg.get("backfill_batch_size", 8) or 8)
    if batch_size <= 0:
        batch_size = 8

    run_cfg = raw_cfg.get("run") or {}
    resume_from_checkpoint = bool(run_cfg.get("resume_from_checkpoint", True))

    extended_selected_all: List[Dict[str, Any]] = []
    core_selected_all: List[Dict[str, Any]] = []

    for t in targets:
        cfg_t = track_cfg.get(t) or {}
        core_size = int(cfg_t.get("core_size") or cfg_t.get("target_min") or 25)
        extended_size = int(cfg_t.get("extended_size") or cfg_t.get("target_max") or cfg_t.get("target_min") or 40)
        if extended_size < core_size:
            extended_size = core_size
        s2_snapshot_dir = paths.private_dir / "raw_snapshots" / "s2"
        s2_snapshot_path = s2_snapshot_dir / f"works_track_{t}.jsonl"
        s2_requests_path = s2_snapshot_dir / f"requests_track_{t}.jsonl"
        # Legacy offline compatibility: always materialize the OpenAlex snapshot paths
        # (even if OpenAlex is not used by the pipeline). These may be empty.
        oa_snapshot_dir = paths.private_dir / "raw_snapshots" / "openalex"
        oa_works_path = oa_snapshot_dir / f"works_track_{t}.jsonl"
        oa_requests_path = oa_snapshot_dir / f"requests_track_{t}.jsonl"
        ckpt_dir = paths.private_dir / "checkpoints"
        ckpt_rows_path = ckpt_dir / f"track_{t}_extended_rows.jsonl"
        ckpt_records_path = ckpt_dir / f"track_{t}_extended_records.internal.jsonl"
        resume_ckpt_available = bool(
            resume_from_checkpoint and ckpt_rows_path.exists() and ckpt_records_path.exists()
        )
        s2_snapshot_dir.mkdir(parents=True, exist_ok=True)
        oa_snapshot_dir.mkdir(parents=True, exist_ok=True)
        for p in (oa_works_path, oa_requests_path):
            if not p.exists():
                p.write_text("", encoding="utf-8")
        if not s2_requests_path.exists():
            s2_requests_path.write_text("", encoding="utf-8")
        elif not offline and not resume_ckpt_available:
            s2_requests_path.write_text("", encoding="utf-8")
        s2_snap = SnapshotWriter(s2_requests_path, "s2")
        s2 = S2Client(s2_cfg, snapshot=s2_snap)

        works: List[Dict[str, Any]] = []
        if offline:
            if s2_snapshot_path.exists():
                works = _load_jsonl_snapshot(s2_snapshot_path)
                logger.info("Loaded %d S2 works from snapshot for track %s", len(works), t)
            else:
                raise FileNotFoundError(f"Offline mode: missing {s2_snapshot_path}")
        elif resume_ckpt_available and s2_snapshot_path.exists():
            works = _load_jsonl_snapshot(s2_snapshot_path)
            logger.info("Resume mode: loaded %d S2 works from snapshot for track %s", len(works), t)
        else:
            s2_snapshot_path.write_text("", encoding="utf-8")
            s2_query = _build_s2_query(cfg_t, track_id=t)
            fields = (
                "paperId,title,abstract,year,venue,authors,citationCount,"
                "fieldsOfStudy,externalIds,url,openAccessPdf"
            )
            for w in s2.iter_search_bulk(
                query=str(s2_query["query"]),
                fields=fields,
                year=str(s2_query["year"] or ""),
                fields_of_study=str(s2_query["fields_of_study"] or ""),
                min_citation_count=s2_query["min_citation_count"],
                open_access_pdf=bool(s2_query["open_access_pdf_only"]),
                max_results=int(s2_query["max_results"]),
            ):
                works.append(w)
                with open(s2_snapshot_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(w, ensure_ascii=False) + "\n")
            logger.info("Fetched %d S2 works for track %s", len(works), t)

        candidates = [parse_s2_work(w) for w in works if w.get("paperId")]
        if not candidates:
            logger.warning("No candidates for track %s", t)
            continue

        def manual_decision_for_candidate(cand: Any) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
            return match_manual_decision(cand, manual_decisions)

        # Manual excludes are applied at candidate filtering time; log them deterministically.
        if manual_path:
            for c in candidates:
                matched_key, dec = manual_decision_for_candidate(c)
                if not dec:
                    continue
                action = str(dec.get("action") or "").strip().lower()
                if action != "exclude":
                    continue
                selection_rows_by_tier["extended"].append(
                    {
                        "ts_unix": int(time.time()),
                        "track_id": t,
                        "tier": "extended",
                        "paper_key": c.paper_key,
                        "openalex_id": c.openalex_id,
                        "doi": c.doi,
                        "arxiv_id": c.arxiv_id,
                        "action": "exclude",
                        "reason_tag": str(dec.get("reason_tag") or "manual_exclude"),
                        "reviewer_id": str(dec.get("reviewer_id") or ""),
                        "evidence": {
                            "matched_key": matched_key,
                            "manual_decisions_file": manual_path,
                            "note": str(dec.get("evidence") or dec.get("note") or ""),
                        },
                    }
                )

        pool_size = max(extended_size, int(round(extended_size * pool_mult)))
        pool_size = max(1, min(pool_size, len(candidates)))

        ref_year = _parse_int(((cfg_t.get("s2") or {}).get("year_to") or 0) or 0)
        if ref_year == 0:
            ref_year = None

        selected_pool, selection_signals = select_works(
            candidates,
            target_min=pool_size,
            target_max=pool_size,
            topic_coverage_k=topic_k,
            centrality_weights=centrality_weights,
            manual_decisions=manual_decisions,
            ref_year=ref_year,
            return_signals=True,
        )
        oa_to_pid = assign_local_ids(selected_pool, track_prefix=t)

        # Manual includes are enforced in select_works; log the includes that made it into the pool.
        if manual_path:
            for c in selected_pool:
                matched_key, dec = manual_decision_for_candidate(c)
                if not dec:
                    continue
                action = str(dec.get("action") or "").strip().lower()
                if action != "include":
                    continue
                selection_rows_by_tier["extended"].append(
                    {
                        "ts_unix": int(time.time()),
                        "track_id": t,
                        "tier": "extended",
                        "paper_id": oa_to_pid.get(c.openalex_id),
                        "paper_key": c.paper_key,
                        "openalex_id": c.openalex_id,
                        "doi": c.doi,
                        "arxiv_id": c.arxiv_id,
                        "action": "include",
                        "reason_tag": str(dec.get("reason_tag") or "manual_include"),
                        "reviewer_id": str(dec.get("reviewer_id") or ""),
                        "evidence": {
                            "matched_key": matched_key,
                            "manual_decisions_file": manual_path,
                            "note": str(dec.get("evidence") or dec.get("note") or ""),
                        },
                    }
                )

        # S2 client is initialized at the beginning of each track loop and reused
        # for both candidate retrieval and metadata enrichment.

        accepted_ext_rows: List[Dict[str, Any]] = []
        accepted_ext_records: Dict[str, PaperRecordInternalV2] = {}
        accepted_openalex_ids: set[str] = set()

        if resume_ckpt_available:
            ckpt_rows = _load_jsonl_snapshot(ckpt_rows_path)
            ckpt_records = load_records_internal_v2(ckpt_records_path)
            rec_by_pid = {str(r.public.paper_id or ""): r for r in ckpt_records if r.public.paper_id}
            for row in ckpt_rows:
                pid = str(row.get("paper_id") or "")
                rec = rec_by_pid.get(pid)
                if not pid or rec is None:
                    continue
                accepted_ext_rows.append(row)
                accepted_ext_records[pid] = rec
                oaid = str(row.get("openalex_id") or "")
                if oaid:
                    accepted_openalex_ids.add(oaid)
            logger.info(
                "Resumed %d accepted rows from checkpoint for track %s",
                len(accepted_ext_rows),
                t,
            )

        def append_resume_checkpoint(row: Dict[str, Any], rec: PaperRecordInternalV2) -> None:
            if not resume_from_checkpoint:
                return
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            with open(ckpt_rows_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            with open(ckpt_records_path, "a", encoding="utf-8") as f:
                f.write(rec.to_json() + "\n")

        def process_batch(rows: List[Dict[str, Any]]) -> None:
            nonlocal accepted_ext_rows, accepted_ext_records, accepted_openalex_ids
            updated = cache_fulltext_for_mapping_rows(
                raw_cfg,
                paths=paths,
                mapping_rows=rows,
                offline=offline,
                tier="extended",
                write_index=False,
            )
            for row in updated:
                if len(accepted_ext_rows) >= extended_size:
                    break

                paper_id = str(row.get("paper_id") or "")
                ft_status = str(row.get("fulltext_status") or "")
                ft_has = bool(row.get("pdf_sha256")) or bool(row.get("source_paths") or [])
                if require_fulltext_success and not ft_has:
                    reason = "exclude_fulltext_missing" if ft_status in ("missing", "skipped_offline") else "exclude_fulltext_error"
                    selection_rows_by_tier["extended"].append(
                        {
                            "ts_unix": int(time.time()),
                            "track_id": t,
                            "tier": "extended",
                            "paper_id": paper_id,
                            "paper_key": row.get("paper_key"),
                            "openalex_id": row.get("openalex_id"),
                            "doi": row.get("doi"),
                            "arxiv_id": row.get("arxiv_id"),
                            "action": "exclude",
                            "reason_tag": reason,
                            "evidence": {"fulltext_status": ft_status, "fulltext_error": row.get("fulltext_error")},
                        }
                    )
                    continue

                row["confidence_score"] = _confidence_score(row)

                deps = list(row.get("dependencies") or [])
                title = str(row.get("title") or paper_id)
                abstract = str(row.get("abstract") or "")

                rec = build_record_v2_from_abstract(
                    paper_id=paper_id,
                    track_id=t,
                    title=title,
                    abstract=abstract,
                    dependencies=deps,
                    llm=llm,
                    ids={
                        "doi": row.get("doi"),
                        "arxiv_id": row.get("arxiv_id"),
                        "openalex_id": row.get("openalex_id"),
                        "s2_id": row.get("s2_id"),
                        "landing_page_url": row.get("landing_page_url"),
                    },
                    strict_paraphrase=strict_paraphrase,
                    max_retries=max_retries,
                    prompt_version=prompt_version or None,
                    taxonomy=taxonomy,
                    forbid_names=forbid_names,
                    name_allowlist=[str(x) for x in name_allowlist if str(x).strip()],
                )

                # Best-effort: build formula_graph from arXiv sources (if available).
                src_paths = list(row.get("source_paths") or [])
                has_arxiv_source = any(str(p).lower().endswith(".source") for p in src_paths) or str(
                    row.get("fulltext_source") or ""
                ) == "arxiv"

                if offline:
                    row["formula_graph_status"] = "skipped_offline"
                    row["formula_graph_reason"] = "offline"
                elif has_arxiv_source:
                    fg, fg_status, fg_reason = extract_formula_graph_from_source_paths(src_paths)
                    rec.public.formula_graph = fg
                    row["formula_graph_status"] = fg_status
                    row["formula_graph_reason"] = fg_reason
                    row["formula_graph_n_nodes"] = len(fg.nodes)
                    row["formula_graph_n_edges"] = len(fg.edges)
                    if fg_status != "ok":
                        _append_jsonl(
                            paths.private_dir / "manual_formula_queue.jsonl",
                            {
                                "ts_unix": int(time.time()),
                                "paper_id": paper_id,
                                "track_id": t,
                                "tier": "extended",
                                "arxiv_id": row.get("arxiv_id"),
                                "fulltext_source": row.get("fulltext_source"),
                                "fulltext_status": row.get("fulltext_status"),
                                "formula_graph_status": fg_status,
                                "reason": fg_reason,
                                "source_paths": src_paths,
                            },
                        )
                else:
                    row["formula_graph_status"] = "skipped_non_arxiv"
                    row["formula_graph_reason"] = "no_arxiv_source"

                accepted_ext_rows.append(row)
                accepted_ext_records[paper_id] = rec
                oaid = str(row.get("openalex_id") or "")
                if oaid:
                    accepted_openalex_ids.add(oaid)
                append_resume_checkpoint(row, rec)
                selection_rows_by_tier["extended"].append(
                    {
                        "ts_unix": int(time.time()),
                        "track_id": t,
                        "tier": "extended",
                        "paper_id": paper_id,
                        "paper_key": row.get("paper_key"),
                        "openalex_id": row.get("openalex_id"),
                        "doi": row.get("doi"),
                        "arxiv_id": row.get("arxiv_id"),
                        "action": "include",
                        "reason_tag": "include_strict_fulltext_and_record_ok",
                        "evidence": {
                            "pool_size": pool_size,
                            "selection_signals": row.get("selection_signals"),
                        },
                    }
                )

        s2_meta_by_id: Dict[str, Dict[str, Any]] = {}
        s2_meta_by_doi: Dict[str, Dict[str, Any]] = {}
        s2_meta_by_arxiv: Dict[str, Dict[str, Any]] = {}
        if (not offline) and selected_pool and s2_enable_batch_enrich and len(accepted_ext_rows) < extended_size:
            batch_ids: List[str] = []
            for c in selected_pool:
                if str(c.openalex_id) in accepted_openalex_ids:
                    continue
                if c.s2_id:
                    batch_ids.append(c.s2_id)
                elif c.doi:
                    batch_ids.append(f"DOI:{c.doi}")
                elif c.arxiv_id:
                    batch_ids.append(f"ARXIV:{c.arxiv_id}")

            batch_fields = (
                "paperId,title,abstract,year,venue,authors,citationCount,references,"
                "fieldsOfStudy,externalIds,url,openAccessPdf"
            )
            for meta in s2.iter_paper_batch(batch_ids, fields=batch_fields, chunk_size=s2_batch_chunk):
                pid = str(meta.get("paperId") or "").strip()
                if pid:
                    s2_meta_by_id[pid] = meta

                ext = meta.get("externalIds") or {}
                if isinstance(ext, dict):
                    doi_norm = _normalize_doi(ext.get("DOI") or ext.get("Doi"))
                    if doi_norm:
                        s2_meta_by_doi[doi_norm] = meta
                    arxiv_norm = _normalize_arxiv_id(ext.get("ArXiv") or ext.get("arXiv"))
                    if arxiv_norm:
                        s2_meta_by_arxiv[arxiv_norm] = meta

            logger.info("Batch-enriched %d selected papers for track %s", len(s2_meta_by_id), t)
        elif (not offline) and selected_pool and (not s2_enable_batch_enrich) and len(accepted_ext_rows) < extended_size:
            logger.info("Batch enrichment disabled for track %s; using search/bulk metadata only", t)

        pending: List[Dict[str, Any]] = []

        for c in selected_pool:
            if len(accepted_ext_rows) >= extended_size:
                break
            if str(c.openalex_id) in accepted_openalex_ids:
                continue

            paper_id = oa_to_pid[c.openalex_id]

            deps = []
            for ref in c.referenced_works:
                if ref in oa_to_pid:
                    deps.append(oa_to_pid[ref])

            s2_meta: Optional[Dict[str, Any]] = None
            meta_from_batch = False
            if c.s2_id and c.s2_id in s2_meta_by_id:
                s2_meta = s2_meta_by_id[c.s2_id]
                meta_from_batch = True
            if s2_meta is None:
                doi_norm = _normalize_doi(c.doi)
                if doi_norm and doi_norm in s2_meta_by_doi:
                    s2_meta = s2_meta_by_doi[doi_norm]
                    meta_from_batch = True
            if s2_meta is None:
                arxiv_norm = _normalize_arxiv_id(c.arxiv_id)
                if arxiv_norm and arxiv_norm in s2_meta_by_arxiv:
                    s2_meta = s2_meta_by_arxiv[arxiv_norm]
                    meta_from_batch = True
            if s2_meta is None and isinstance(c.raw, dict):
                s2_meta = dict(c.raw)

            s2_meta_sha256 = _sha256_json(s2_meta) if isinstance(s2_meta, dict) and s2_meta else None

            abstract = str(c.raw.get("abstract") or "").strip()
            abstract_source = "s2_search_bulk" if abstract else ""
            if (not abstract) and isinstance(s2_meta, dict):
                abstract = str(s2_meta.get("abstract") or "").strip()
                if abstract:
                    abstract_source = "s2_batch" if meta_from_batch else "s2_search_bulk"

            arxiv_id = c.arxiv_id
            doi = c.doi
            s2_id = c.s2_id or None
            author_pdf_url = None
            landing = None
            s2_refs: List[str] = []
            if isinstance(s2_meta, dict):
                s2_id = s2_meta.get("paperId") or s2_id
                landing = s2_meta.get("url") or None
                ext = s2_meta.get("externalIds") or {}
                if isinstance(ext, dict):
                    doi = doi or ext.get("DOI") or ext.get("Doi") or None
                    arxiv_id = arxiv_id or ext.get("ArXiv") or ext.get("arXiv") or None
                oa_pdf = s2_meta.get("openAccessPdf") or {}
                if isinstance(oa_pdf, dict):
                    author_pdf_url = oa_pdf.get("url") or None
                refs = s2_meta.get("references") or []
                if isinstance(refs, list):
                    for r in refs:
                        if isinstance(r, dict) and r.get("paperId"):
                            s2_refs.append(str(r["paperId"]))

            row = {
                "tier": "extended",
                "paper_id": paper_id,
                "paper_key": c.paper_key,
                "track_id": t,
                "openalex_id": c.openalex_id,
                "source_work_sha256": _sha256_json(c.raw),
                "doi": doi,
                "arxiv_id": arxiv_id,
                "s2_id": s2_id,
                "s2_meta_sha256": s2_meta_sha256,
                "s2_reference_ids": s2_refs,
                "landing_page_url": landing,
                "author_pdf_url": author_pdf_url,
                "title": c.title,
                "year": c.publication_year,
                "cited_by_count": c.cited_by_count,
                "dependencies": deps,
                "concept_ids": list(c.concept_ids),
                "selection_signals": selection_signals.get(c.openalex_id) if isinstance(selection_signals, dict) else None,
                "abstract": abstract,
                "abstract_source": abstract_source,
            }
            pending.append(row)
            if len(pending) >= batch_size:
                process_batch(pending)
                pending = []

        if pending and len(accepted_ext_rows) < extended_size:
            process_batch(pending)
            pending = []

        if not accepted_ext_rows:
            logger.warning("No extended rows selected for track %s (target=%d)", t, extended_size)
            continue

        accepted_pids = {str(r.get("paper_id") or "") for r in accepted_ext_rows if r.get("paper_id")}

        # Prune dependencies to the final accepted set.
        for row in accepted_ext_rows:
            row["dependencies"] = [d for d in (row.get("dependencies") or []) if d in accepted_pids]
        for pid, rec in accepted_ext_records.items():
            rec.public.dependencies = [d for d in (rec.public.dependencies or []) if d in accepted_pids]

        # Rank is computed within-tier (extended) per track.
        ranked_ext = sorted(
            accepted_ext_rows,
            key=lambda r: (-int(r.get("cited_by_count", 0) or 0), str(r.get("paper_id") or "")),
        )
        ext_rank_map = {str(r.get("paper_id")): i + 1 for i, r in enumerate(ranked_ext) if r.get("paper_id")}

        ext_internal: List[PaperRecordInternalV2] = []
        ext_public = []
        for row in accepted_ext_rows:
            pid = str(row.get("paper_id") or "")
            rec = accepted_ext_records.get(pid)
            if rec is None:
                continue
            rec.public.results.primary_metric_rank = int(ext_rank_map.get(pid, 0))
            rec.public.provenance["tier"] = "extended"
            rec.public.provenance["pipeline"] = "online_v2_strict"
            rec.public.provenance["abstract_source"] = row.get("abstract_source")
            rec.public.provenance["fulltext_source"] = row.get("fulltext_source")
            rec.public.provenance["fulltext_status"] = row.get("fulltext_status")
            snap_refs = {
                "source_work_sha256": row.get("source_work_sha256"),
                "s2_meta_sha256": row.get("s2_meta_sha256"),
            }
            rec.public.provenance["snapshot_refs"] = {k: v for k, v in snap_refs.items() if v}

            rec.pdf_sha256 = row.get("pdf_sha256")
            rec.source_paths = list(row.get("source_paths") or [])
            rec.retrieved_at_unix = row.get("retrieved_at_unix")
            rec.year = row.get("year")
            ext_internal.append(rec)
            ext_public.append(rec.public)

        save_records_internal_v2(ext_internal, paths.private_records_path(t, "extended"))
        save_records_v2(ext_public, paths.public_records_path(t, "extended"))

        # Persist private mapping rows for extended.
        _write_jsonl(paths.private_mapping_path(t, "extended"), accepted_ext_rows)

        # Dependency graph edges for extended.
        for row in accepted_ext_rows:
            pid = str(row.get("paper_id") or "")
            for dep_pid in row.get("dependencies") or []:
                dep_edges_by_tier["extended"].append(f"{dep_pid} {pid}")

        # Derive core subset (dependency-closed).
        core_pids = derive_dependency_closed_core_paper_ids(accepted_ext_rows, core_size=core_size)
        core_set = set(core_pids)
        ext_by_pid = {str(r.get("paper_id")): r for r in accepted_ext_rows if r.get("paper_id")}

        core_rows: List[Dict[str, Any]] = []
        for pid in core_pids:
            r = ext_by_pid.get(pid)
            if not r:
                continue
            rr = dict(r)
            rr["tier"] = "core"
            rr["dependencies"] = [d for d in (rr.get("dependencies") or []) if d in core_set]
            core_rows.append(rr)

        _write_jsonl(paths.private_mapping_path(t, "core"), core_rows)

        # Core selection log (include + exclude-from-core for auditability).
        meta_by_pid = {str(r.get("paper_id")): r for r in accepted_ext_rows if r.get("paper_id")}
        for pid in core_pids:
            meta = meta_by_pid.get(pid) or {}
            selection_rows_by_tier["core"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "core",
                    "paper_id": pid,
                    "paper_key": meta.get("paper_key"),
                    "openalex_id": meta.get("openalex_id"),
                    "doi": meta.get("doi"),
                    "arxiv_id": meta.get("arxiv_id"),
                    "action": "include",
                    "reason_tag": "core_subset_from_extended",
                    "evidence": {"source_tier": "extended", "core_size": core_size},
                }
            )
        for pid in sorted(accepted_pids - core_set):
            meta = meta_by_pid.get(pid) or {}
            selection_rows_by_tier["core"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "core",
                    "paper_id": pid,
                    "paper_key": meta.get("paper_key"),
                    "openalex_id": meta.get("openalex_id"),
                    "doi": meta.get("doi"),
                    "arxiv_id": meta.get("arxiv_id"),
                    "action": "exclude",
                    "reason_tag": "exclude_not_in_core_subset",
                    "evidence": {"core_size": core_size},
                }
            )

        # Rank is computed within-tier (core) per track.
        ranked_core = sorted(
            core_rows,
            key=lambda r: (-int(r.get("cited_by_count", 0) or 0), str(r.get("paper_id") or "")),
        )
        core_rank_map = {str(r.get("paper_id")): i + 1 for i, r in enumerate(ranked_core) if r.get("paper_id")}

        core_internal: List[PaperRecordInternalV2] = []
        core_public = []
        for pid in core_pids:
            base = accepted_ext_records.get(pid)
            if base is None:
                continue
            rec = copy.deepcopy(base)
            rec.public.dependencies = [d for d in (rec.public.dependencies or []) if d in core_set]
            rec.public.results.primary_metric_rank = int(core_rank_map.get(pid, 0))
            rec.public.provenance["tier"] = "core"
            rec.public.provenance["pipeline"] = "online_v2_strict"
            core_internal.append(rec)
            core_public.append(rec.public)

        save_records_internal_v2(core_internal, paths.private_records_path(t, "core"))
        save_records_v2(core_public, paths.public_records_path(t, "core"))

        # Export a concise per-track paper list (private).
        track_papers: List[Dict[str, Any]] = []
        now_ts = int(time.time())
        for row in accepted_ext_rows:
            track_papers.append(
                {
                    "ts_unix": now_ts,
                    "tier": "extended",
                    "track_id": t,
                    "paper_id": row.get("paper_id"),
                    "paper_key": row.get("paper_key"),
                    "openalex_id": row.get("openalex_id"),
                    "doi": row.get("doi"),
                    "arxiv_id": row.get("arxiv_id"),
                    "s2_id": row.get("s2_id"),
                    "landing_page_url": row.get("landing_page_url"),
                    "author_pdf_url": row.get("author_pdf_url"),
                    "year": row.get("year"),
                    "cited_by_count": row.get("cited_by_count"),
                    "fulltext_status": row.get("fulltext_status"),
                    "pdf_sha256": row.get("pdf_sha256"),
                    "retrieved_at_unix": row.get("retrieved_at_unix"),
                }
            )
        for row in core_rows:
            track_papers.append(
                {
                    "ts_unix": now_ts,
                    "tier": "core",
                    "track_id": t,
                    "paper_id": row.get("paper_id"),
                    "paper_key": row.get("paper_key"),
                    "openalex_id": row.get("openalex_id"),
                    "doi": row.get("doi"),
                    "arxiv_id": row.get("arxiv_id"),
                    "s2_id": row.get("s2_id"),
                    "landing_page_url": row.get("landing_page_url"),
                    "author_pdf_url": row.get("author_pdf_url"),
                    "year": row.get("year"),
                    "cited_by_count": row.get("cited_by_count"),
                    "fulltext_status": row.get("fulltext_status"),
                    "pdf_sha256": row.get("pdf_sha256"),
                    "retrieved_at_unix": row.get("retrieved_at_unix"),
                }
            )
        _write_jsonl(paths.private_track_papers_path(t), track_papers)

        # Track completed successfully; clear resume checkpoints.
        for p in (ckpt_rows_path, ckpt_records_path):
            if p.exists():
                p.unlink()

        # Dependency graph edges for core.
        for row in core_rows:
            pid = str(row.get("paper_id") or "")
            for dep_pid in row.get("dependencies") or []:
                dep_edges_by_tier["core"].append(f"{dep_pid} {pid}")

        extended_selected_all.extend(accepted_ext_rows)
        core_selected_all.extend(core_rows)

    # Write tier-level fulltext indices for the final selected papers only.
    write_fulltext_index_for_mapping_rows(paths=paths, mapping_rows=extended_selected_all, tier="extended")
    write_fulltext_index_for_mapping_rows(paths=paths, mapping_rows=core_selected_all, tier="core")

    _write_jsonl(paths.public_selection_log_path("extended"), selection_rows_by_tier["extended"])
    _write_jsonl(paths.public_selection_log_path("core"), selection_rows_by_tier["core"])

    for tier in ("extended", "core"):
        p = paths.public_dependency_graph_path(tier)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for e in dep_edges_by_tier[tier]:
                f.write(e + "\n")
