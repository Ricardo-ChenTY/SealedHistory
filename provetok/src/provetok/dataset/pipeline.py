"""Online dataset pipeline (OpenAlex/S2/OC/arXiv).

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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import PaperRecordInternalV2, save_records_internal_v2, save_records_v2
from provetok.dataset.fulltext import cache_fulltext_for_mapping_rows, write_fulltext_index_for_mapping_rows
from provetok.dataset.formula_graph import extract_formula_graph_from_source_paths
from provetok.dataset.legacy import default_taxonomy
from provetok.dataset.paths import DatasetPaths
from provetok.dataset.record_builder import RecordBuildError, build_record_v2_from_abstract
from provetok.dataset.selection import (
    assign_local_ids,
    derive_dependency_closed_core_paper_ids,
    load_manual_decisions,
    parse_openalex_work,
    select_works,
)
from provetok.sources.http import SnapshotWriter
from provetok.sources.openalex_client import OpenAlexClient, OpenAlexConfig
from provetok.sources.opencitations_client import OpenCitationsClient, OpenCitationsConfig
from provetok.sources.s2_client import S2Client, S2Config
from provetok.utils.llm_client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


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


def _load_openalex_snapshot(path: Path) -> List[Dict[str, Any]]:
    works: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                works.append(json.loads(line))
    return works


def _openalex_inverted_abstract(w: Dict[str, Any]) -> str:
    """Reconstruct abstract from OpenAlex inverted index if present."""
    inv = w.get("abstract_inverted_index")
    if not isinstance(inv, dict):
        return ""
    # inv: {token: [pos,...]}
    positions: Dict[int, str] = {}
    for token, pos_list in inv.items():
        if not isinstance(pos_list, list):
            continue
        for p in pos_list:
            if isinstance(p, int):
                positions[p] = token
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))


def _build_openalex_filter(track_cfg: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return (filter_str, search_str)."""
    oa = track_cfg.get("openalex") or {}
    concepts = [str(x) for x in (oa.get("concepts") or []) if x]
    venues = [str(x) for x in (oa.get("venues") or []) if x]
    keywords = [str(x) for x in (oa.get("keywords") or []) if x]
    year_from = oa.get("year_from")
    year_to = oa.get("year_to")

    parts: List[str] = []
    if concepts:
        parts.append("concept.id:" + "|".join(concepts))
    if venues:
        parts.append("host_venue.id:" + "|".join(venues))
    if year_from:
        parts.append(f"from_publication_date:{int(year_from)}-01-01")
    if year_to:
        parts.append(f"to_publication_date:{int(year_to)}-12-31")

    filter_str = ",".join(parts) if parts else None
    search_str = " ".join(keywords) if keywords else None
    return filter_str, search_str


def build_online_dataset(raw_cfg: Dict[str, Any], paths: DatasetPaths, offline: bool, track: str) -> None:
    targets = ["A", "B"] if track == "both" else [track]

    # Always write a public taxonomy scaffold (also used to normalize tags).
    taxonomy = default_taxonomy()
    _write_json(paths.public_dir / "taxonomy.json", taxonomy)

    def _sha256_json(obj: Any) -> str:
        try:
            blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except Exception:
            blob = str(obj).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    sources_cfg = raw_cfg.get("sources") or {}
    oa_cfg_raw = sources_cfg.get("openalex") or {}
    s2_cfg_raw = sources_cfg.get("s2") or {}

    openalex_cfg = OpenAlexConfig(
        base_url=str(oa_cfg_raw.get("base_url", "https://api.openalex.org")),
        mailto=str(oa_cfg_raw.get("mailto", "")),
        per_page=int(oa_cfg_raw.get("per_page", 200)),
        max_pages=int(oa_cfg_raw.get("max_pages", 50)),
        rate_limit_qps=float(oa_cfg_raw.get("rate_limit_qps", 3.0)),
    )

    s2_api_key_env = str(s2_cfg_raw.get("api_key_env", "S2_API_KEY"))
    s2_api_key = os.environ.get(s2_api_key_env, "")
    s2_cfg = S2Config(
        base_url=str(s2_cfg_raw.get("base_url", "https://api.semanticscholar.org/graph/v1")),
        api_key=s2_api_key,
        rate_limit_qps=float(s2_cfg_raw.get("rate_limit_qps", 1.0)),
    )

    manual_path = str((raw_cfg.get("selection") or {}).get("manual_decisions_file") or "")
    manual_decisions = load_manual_decisions(Path(manual_path)) if manual_path else {}

    sel_cfg = raw_cfg.get("selection") or {}
    topic_k = int(sel_cfg.get("topic_coverage_k", 8))
    centrality_weights = dict(sel_cfg.get("centrality_weights") or {"pagerank": 1.0, "indegree": 0.5})

    track_cfg = raw_cfg.get("tracks") or {}
    sizes_by_track: Dict[str, Dict[str, int]] = {}

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

    extended_selected_all: List[Dict[str, Any]] = []
    core_selected_all: List[Dict[str, Any]] = []

    for t in targets:
        cfg_t = track_cfg.get(t) or {}
        core_size = int(cfg_t.get("core_size") or cfg_t.get("target_min") or 25)
        extended_size = int(cfg_t.get("extended_size") or cfg_t.get("target_max") or cfg_t.get("target_min") or 40)
        if extended_size < core_size:
            extended_size = core_size
        sizes_by_track[t] = {"core_size": core_size, "extended_size": extended_size}

        works_snapshot_dir = paths.private_dir / "raw_snapshots" / "openalex"
        works_snapshot_path = works_snapshot_dir / f"works_track_{t}.jsonl"
        works_snapshot_dir.mkdir(parents=True, exist_ok=True)

        works: List[Dict[str, Any]] = []
        if offline:
            if not works_snapshot_path.exists():
                raise FileNotFoundError(f"Offline mode: missing {works_snapshot_path}")
            works = _load_openalex_snapshot(works_snapshot_path)
            logger.info("Loaded %d OpenAlex works from snapshot for track %s", len(works), t)
        else:
            # Truncate snapshot for deterministic reruns within the same export dir.
            works_snapshot_path.write_text("", encoding="utf-8")
            snap_log = SnapshotWriter(
                paths.private_dir / "raw_snapshots" / "openalex" / f"requests_track_{t}.jsonl",
                "openalex",
            )
            client = OpenAlexClient(openalex_cfg, snapshot=snap_log)
            filter_str, search_str = _build_openalex_filter(cfg_t)
            select = "id,title,publication_year,doi,ids,concepts,cited_by_count,referenced_works,abstract_inverted_index"
            for w in client.iter_works(filter_str=filter_str, search=search_str, select=select):
                works.append(w)
                with open(works_snapshot_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(w, ensure_ascii=False) + "\n")
            logger.info("Fetched %d OpenAlex works for track %s", len(works), t)

        candidates = [parse_openalex_work(w) for w in works if w.get("id")]
        if not candidates:
            logger.warning("No OpenAlex candidates for track %s", t)
            continue

        pool_size = max(extended_size, int(round(extended_size * pool_mult)))
        pool_size = max(1, min(pool_size, len(candidates)))

        oa_ref_year = None
        try:
            oa_ref_year = int(((cfg_t.get("openalex") or {}).get("year_to") or 0) or 0) or None
        except Exception:
            oa_ref_year = None

        selected_pool, selection_signals = select_works(
            candidates,
            target_min=pool_size,
            target_max=pool_size,
            topic_coverage_k=topic_k,
            centrality_weights=centrality_weights,
            manual_decisions=manual_decisions,
            ref_year=oa_ref_year,
            return_signals=True,
        )
        oa_to_pid = assign_local_ids(selected_pool, track_prefix=t)

        # Prepare S2 client for metadata enrichment (DOI/arXiv/openAccessPdf).
        s2_snap = SnapshotWriter(paths.private_dir / "raw_snapshots" / "s2" / f"requests_track_{t}.jsonl", "s2")
        s2 = S2Client(s2_cfg, snapshot=s2_snap)

        accepted_ext_rows: List[Dict[str, Any]] = []
        accepted_ext_records: Dict[str, PaperRecordInternalV2] = {}

        def process_batch(rows: List[Dict[str, Any]]) -> None:
            nonlocal accepted_ext_rows, accepted_ext_records
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

                try:
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
                except RecordBuildError as e:
                    selection_rows_by_tier["extended"].append(
                        {
                            "ts_unix": int(time.time()),
                            "track_id": t,
                            "tier": "extended",
                            "paper_id": paper_id,
                            "action": "exclude",
                            "reason_tag": "exclude_record_build_failed",
                            "evidence": {"code": e.code, "error": str(e)},
                        }
                    )
                    continue

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
                selection_rows_by_tier["extended"].append(
                    {
                        "ts_unix": int(time.time()),
                        "track_id": t,
                        "tier": "extended",
                        "paper_id": paper_id,
                        "action": "include",
                        "reason_tag": "include_strict_fulltext_and_record_ok",
                        "evidence": {
                            "pool_size": pool_size,
                            "selection_signals": row.get("selection_signals"),
                        },
                    }
                )

        pending: List[Dict[str, Any]] = []

        for c in selected_pool:
            if len(accepted_ext_rows) >= extended_size:
                break

            paper_id = oa_to_pid[c.openalex_id]

            deps = []
            for ref in c.referenced_works:
                if ref in oa_to_pid:
                    deps.append(oa_to_pid[ref])

            abstract = _openalex_inverted_abstract(c.raw)
            abstract_source = "openalex" if abstract else ""

            s2_meta: Optional[Dict[str, Any]] = None
            s2_meta_sha256: Optional[str] = None
            if not offline:
                key = c.doi or (c.arxiv_id or "")
                if key:
                    try:
                        s2_meta = s2.get_paper(key)
                    except Exception:
                        s2_meta = None
                if not s2_meta and c.title:
                    try:
                        s2_meta = (s2.search(c.title, limit=1) or {}).get("data", [None])[0]
                    except Exception:
                        s2_meta = None
                if s2_meta and isinstance(s2_meta, dict):
                    s2_meta_sha256 = _sha256_json(s2_meta)

            if s2_meta and not abstract:
                abstract = str(s2_meta.get("abstract") or "")
                abstract_source = "s2" if abstract else ""

            arxiv_id = c.arxiv_id
            doi = c.doi
            s2_id = None
            author_pdf_url = None
            landing = None
            s2_refs: List[str] = []
            if s2_meta and isinstance(s2_meta, dict):
                s2_id = s2_meta.get("paperId") or None
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
                "track_id": t,
                "openalex_id": c.openalex_id,
                "openalex_work_sha256": _sha256_json(c.raw),
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
                "openalex_work_sha256": row.get("openalex_work_sha256"),
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

        # Optional: enrich core with OpenCitations outgoing references (DOI->DOI).
        oc_cfg_raw = (sources_cfg.get("opencitations") or {}) if isinstance(sources_cfg, dict) else {}
        oc_enable = bool(oc_cfg_raw.get("enable", False))
        oc_tiers_raw = oc_cfg_raw.get("tiers") or ["core"]
        if not isinstance(oc_tiers_raw, list):
            oc_tiers_raw = [oc_tiers_raw]
        oc_tiers = [str(x) for x in oc_tiers_raw if x]

        if oc_enable and (not offline) and ("core" in oc_tiers):
            oc_snap = SnapshotWriter(
                paths.private_dir / "raw_snapshots" / "opencitations" / f"requests_track_{t}.jsonl",
                "opencitations",
            )
            oc_client = OpenCitationsClient(
                OpenCitationsConfig(
                    base_url=str(oc_cfg_raw.get("base_url", "https://api.opencitations.net/index/v1")),
                    rate_limit_qps=float(oc_cfg_raw.get("rate_limit_qps", 2.0)),
                ),
                snapshot=oc_snap,
            )

            doi_to_pid_core: Dict[str, str] = {}
            for row in core_rows:
                doi_norm = _normalize_doi(row.get("doi"))
                pid = str(row.get("paper_id") or "")
                if doi_norm and pid:
                    doi_to_pid_core[doi_norm] = pid

            for row in core_rows:
                doi_norm = _normalize_doi(row.get("doi"))
                if not doi_norm:
                    continue

                data = oc_client.references(doi_norm)
                ref_dois: List[str] = []
                if isinstance(data, list):
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        cited = item.get("cited") or item.get("cited_doi") or ""
                        cited_norm = _normalize_doi(str(cited))
                        if cited_norm:
                            ref_dois.append(cited_norm)

                seen: set[str] = set()
                uniq: List[str] = []
                for d in ref_dois:
                    if d not in seen:
                        seen.add(d)
                        uniq.append(d)

                row["oc_reference_dois"] = uniq
                row["oc_reference_paper_ids"] = [doi_to_pid_core[d] for d in uniq if d in doi_to_pid_core]

        _write_jsonl(paths.private_mapping_path(t, "core"), core_rows)

        # Core selection log (include + exclude-from-core for auditability).
        for pid in core_pids:
            selection_rows_by_tier["core"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "core",
                    "paper_id": pid,
                    "action": "include",
                    "reason_tag": "core_subset_from_extended",
                    "evidence": {"source_tier": "extended", "core_size": core_size},
                }
            )
        for pid in sorted(accepted_pids - core_set):
            selection_rows_by_tier["core"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "core",
                    "paper_id": pid,
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
