"""Online dataset pipeline (OpenAlex/S2/OC/arXiv).

This pipeline is best-effort: it aims to produce all plan.md artifacts, while
remaining runnable without network (via `--offline` and cached snapshots).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import PaperRecordInternalV2, save_records_internal_v2, save_records_v2
from provetok.dataset.fulltext import cache_fulltext_for_mapping_rows, write_fulltext_index_for_mapping_rows
from provetok.dataset.legacy import default_taxonomy
from provetok.dataset.paths import DatasetPaths
from provetok.dataset.record_builder import build_record_v2_from_abstract
from provetok.dataset.selection import (
    assign_local_ids,
    derive_dependency_closed_core_paper_ids,
    load_manual_decisions,
    parse_openalex_work,
    select_works,
)
from provetok.sources.http import SnapshotWriter
from provetok.sources.openalex_client import OpenAlexClient, OpenAlexConfig
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

    # Always write a public taxonomy scaffold.
    _write_json(paths.public_dir / "taxonomy.json", default_taxonomy())

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

    extended_rows_all: List[Dict[str, Any]] = []

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

        # Select the extended pool first, then derive a smaller dependency-closed core.
        selected_ext = select_works(
            candidates,
            target_min=extended_size,
            target_max=extended_size,
            topic_coverage_k=topic_k,
            centrality_weights=centrality_weights,
            manual_decisions=manual_decisions,
        )
        oa_to_pid = assign_local_ids(selected_ext, track_prefix=t)

        # Prepare S2 client for metadata enrichment (DOI/arXiv/openAccessPdf).
        s2_snap = SnapshotWriter(paths.private_dir / "raw_snapshots" / "s2" / f"requests_track_{t}.jsonl", "s2")
        s2 = S2Client(s2_cfg, snapshot=s2_snap)

        for c in selected_ext:
            paper_id = oa_to_pid[c.openalex_id]

            # Dependencies: OpenAlex referenced works restricted to selected set.
            deps = []
            for ref in c.referenced_works:
                if ref in oa_to_pid:
                    deps.append(oa_to_pid[ref])

            abstract = _openalex_inverted_abstract(c.raw)
            s2_meta: Optional[Dict[str, Any]] = None
            if not offline:
                # Best-effort: prefer DOI/arXiv id if available, else search by title.
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

            if s2_meta and not abstract:
                abstract = str(s2_meta.get("abstract") or "")

            arxiv_id = c.arxiv_id
            doi = c.doi
            s2_id = None
            author_pdf_url = None
            landing = None
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

            row = {
                "tier": "extended",
                "paper_id": paper_id,
                "track_id": t,
                "openalex_id": c.openalex_id,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "s2_id": s2_id,
                "landing_page_url": landing,
                "author_pdf_url": author_pdf_url,
                "title": c.title,
                "year": c.publication_year,
                "cited_by_count": c.cited_by_count,
                "dependencies": deps,
                "concept_ids": list(c.concept_ids),
                "abstract": abstract,
            }
            extended_rows_all.append(row)

            selection_rows_by_tier["extended"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "extended",
                    "paper_id": paper_id,
                    "action": "include",
                    "reason_tag": "openalex_selection_extended",
                    "evidence": {"policy": "openalex_selection_extended"},
                }
            )
            for dep_pid in deps:
                dep_edges_by_tier["extended"].append(f"{dep_pid} {paper_id}")

    # Fulltext cache (private) updates mapping rows with pdf_sha256/source_paths/retrieved_at_unix.
    extended_rows_all = cache_fulltext_for_mapping_rows(
        raw_cfg,
        paths=paths,
        mapping_rows=extended_rows_all,
        offline=offline,
        tier="extended",
    )

    # Add deterministic confidence score signals used for core subset selection.
    for row in extended_rows_all:
        row["confidence_score"] = _confidence_score(row)

    # Group extended rows by track.
    ext_by_track: Dict[str, List[Dict[str, Any]]] = {t: [] for t in targets}
    for row in extended_rows_all:
        t = str(row.get("track_id") or "")
        if t in ext_by_track:
            ext_by_track[t].append(row)

    # Derive core rows per track (dependency-closed prefix), then persist mapping rows.
    core_by_track: Dict[str, List[Dict[str, Any]]] = {t: [] for t in targets}
    for t in targets:
        ext_rows = ext_by_track.get(t) or []
        if not ext_rows:
            continue

        core_size = int((sizes_by_track.get(t) or {}).get("core_size", 0) or 0)
        core_pids = derive_dependency_closed_core_paper_ids(ext_rows, core_size=core_size)
        core_set = set(core_pids)
        ext_by_pid = {str(r.get("paper_id")): r for r in ext_rows if r.get("paper_id")}

        core_rows: List[Dict[str, Any]] = []
        for pid in core_pids:
            r = ext_by_pid.get(pid)
            if not r:
                continue
            rr = dict(r)
            rr["tier"] = "core"
            rr["dependencies"] = [d for d in (rr.get("dependencies") or []) if d in core_set]
            core_rows.append(rr)

            selection_rows_by_tier["core"].append(
                {
                    "ts_unix": int(time.time()),
                    "track_id": t,
                    "tier": "core",
                    "paper_id": pid,
                    "action": "include",
                    "reason_tag": "core_subset_from_extended",
                    "evidence": {"source_tier": "extended"},
                }
            )
            for dep_pid in rr["dependencies"]:
                dep_edges_by_tier["core"].append(f"{dep_pid} {pid}")

        core_by_track[t] = core_rows

        _write_jsonl(paths.private_mapping_path(t, "extended"), ext_rows)
        _write_jsonl(paths.private_mapping_path(t, "core"), core_rows)

    # Core is a subset of extended: write a tier-specific index without re-downloading.
    core_rows_all: List[Dict[str, Any]] = []
    for t in targets:
        core_rows_all.extend(core_by_track.get(t) or [])
    write_fulltext_index_for_mapping_rows(paths=paths, mapping_rows=core_rows_all, tier="core")

    # Build v2 records for each tier.
    rb = raw_cfg.get("record_build") or {}
    llm_mode = str(rb.get("mode", "llm"))
    llm: Optional[LLMClient] = None
    if llm_mode == "llm":
        api_key_env = str(rb.get("llm_api_key_env", "LLM_API_KEY"))
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            logger.info("LLM disabled: %s is empty; using deterministic fallbacks", api_key_env)
        else:
            llm = LLMClient(
                LLMConfig(
                    model=str(rb.get("llm_model", "deepseek-chat")),
                    api_base=str(rb.get("llm_api_base", "https://api.deepseek.com/v1")),
                    api_key=api_key,
                    temperature=0.0,
                )
            )

    def build_tier_records(tier: str, rows: List[Dict[str, Any]], track_id: str) -> None:
        if not rows:
            return

        internal: List[PaperRecordInternalV2] = []
        public = []

        ranked = sorted(rows, key=lambda r: (-int(r.get("cited_by_count", 0) or 0), str(r.get("paper_id"))))
        rank_map = {str(r["paper_id"]): i + 1 for i, r in enumerate(ranked) if r.get("paper_id")}

        for row in rows:
            paper_id = str(row.get("paper_id", ""))
            deps = list(row.get("dependencies") or [])
            title = str(row.get("title") or paper_id)
            abstract = str(row.get("abstract") or "")

            rec = build_record_v2_from_abstract(
                paper_id=paper_id,
                track_id=track_id,
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
            )
            rec.public.results.primary_metric_rank = int(rank_map.get(paper_id, 0))
            rec.public.provenance["tier"] = tier
            rec.public.provenance["pipeline"] = "online_v1"
            # Carry through fulltext metadata (private)
            rec.pdf_sha256 = row.get("pdf_sha256")
            rec.source_paths = list(row.get("source_paths") or [])
            rec.retrieved_at_unix = row.get("retrieved_at_unix")
            rec.year = row.get("year")
            internal.append(rec)
            public.append(rec.public)

        save_records_internal_v2(internal, paths.private_records_path(track_id, tier))
        save_records_v2(public, paths.public_records_path(track_id, tier))

    for t in targets:
        build_tier_records("extended", ext_by_track.get(t) or [], t)
        build_tier_records("core", core_by_track.get(t) or [], t)

    _write_jsonl(paths.public_selection_log_path("extended"), selection_rows_by_tier["extended"])
    _write_jsonl(paths.public_selection_log_path("core"), selection_rows_by_tier["core"])

    for tier in ("extended", "core"):
        p = paths.public_dependency_graph_path(tier)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for e in dep_edges_by_tier[tier]:
                f.write(e + "\n")
