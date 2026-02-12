"""Cross-source citation edge agreement metrics (plan.md Phase 2 / QA §8).

This module computes overlap/coverage between:
  - OpenAlex-derived internal dependency edges (paper.dependencies)
  - Semantic Scholar references (s2_reference_ids)
  - OpenCitations DOI references (oc_reference_*)

The metrics are computed strictly *within a tier* (core/extended) by mapping
external IDs back to the selected PaperIDs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from provetok.dataset.paths import DatasetPaths

Edge = Tuple[str, str]  # (src_pid, dst_pid)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    # Read by physical file lines only. `str.splitlines()` is too aggressive:
    # it also splits on Unicode separators (e.g. U+2028) that may appear inside
    # JSON string fields from upstream metadata.
    for line in path.open("r", encoding="utf-8"):
        line = line.rstrip("\r\n").strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


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


def _edges_openalex(rows: List[Dict[str, Any]]) -> Set[Edge]:
    edges: Set[Edge] = set()
    for row in rows:
        dst = str(row.get("paper_id") or "")
        if not dst:
            continue
        for dep in row.get("dependencies") or []:
            src = str(dep or "")
            if src:
                edges.add((src, dst))
    return edges


def _edges_s2(rows: List[Dict[str, Any]]) -> Set[Edge]:
    s2_to_pid: Dict[str, str] = {}
    for row in rows:
        pid = str(row.get("paper_id") or "")
        s2_id = row.get("s2_id") or None
        if pid and s2_id:
            s2_to_pid[str(s2_id)] = pid

    edges: Set[Edge] = set()
    for row in rows:
        dst = str(row.get("paper_id") or "")
        if not dst:
            continue
        refs = row.get("s2_reference_ids") or []
        if not isinstance(refs, list):
            continue
        for ref in refs:
            ref_pid = s2_to_pid.get(str(ref))
            if ref_pid:
                edges.add((ref_pid, dst))
    return edges


def _edges_opencitations(rows: List[Dict[str, Any]]) -> Set[Edge]:
    doi_to_pid: Dict[str, str] = {}
    for row in rows:
        pid = str(row.get("paper_id") or "")
        doi_norm = _normalize_doi(row.get("doi"))
        if pid and doi_norm:
            doi_to_pid[doi_norm] = pid

    edges: Set[Edge] = set()
    for row in rows:
        dst = str(row.get("paper_id") or "")
        if not dst:
            continue

        # Prefer already-mapped PaperIDs (if present)
        ref_pids = row.get("oc_reference_paper_ids") or []
        if isinstance(ref_pids, list) and ref_pids:
            for src in ref_pids:
                src_pid = str(src or "")
                if src_pid:
                    edges.add((src_pid, dst))
            continue

        ref_dois = row.get("oc_reference_dois") or []
        if not isinstance(ref_dois, list):
            continue
        for d in ref_dois:
            src_pid = doi_to_pid.get(_normalize_doi(str(d)))
            if src_pid:
                edges.add((src_pid, dst))
    return edges


def _jaccard(a: Set[Edge], b: Set[Edge]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _coverage(numer: int, denom: int) -> float:
    return (numer / denom) if denom else 0.0


def _summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    pids = {str(r.get("paper_id") or "") for r in rows if r.get("paper_id")}
    n_papers = len(pids)

    has_doi = sum(1 for r in rows if _normalize_doi(r.get("doi")))
    has_s2 = sum(1 for r in rows if r.get("s2_id"))
    has_oc = sum(1 for r in rows if ("oc_reference_dois" in r) or ("oc_reference_paper_ids" in r))

    e_oa = _edges_openalex(rows)
    e_s2 = _edges_s2(rows)
    e_oc = _edges_opencitations(rows)

    oa_s2 = e_oa & e_s2
    oa_oc = e_oa & e_oc
    s2_oc = e_s2 & e_oc
    all3 = e_oa & e_s2 & e_oc

    union_other = e_s2 | e_oc

    return {
        "n_papers": n_papers,
        "id_coverage": {
            "doi_rate": _coverage(has_doi, len(rows)),
            "s2_enriched_rate": _coverage(has_s2, len(rows)),
            "opencitations_rate": _coverage(has_oc, len(rows)),
        },
        "n_edges": {
            "openalex": len(e_oa),
            "s2": len(e_s2),
            "opencitations": len(e_oc),
        },
        "overlap": {
            "openalex_s2": len(oa_s2),
            "openalex_opencitations": len(oa_oc),
            "s2_opencitations": len(s2_oc),
            "all3": len(all3),
        },
        "coverage": {
            "openalex_by_s2": _coverage(len(oa_s2), len(e_oa)),
            "openalex_by_opencitations": _coverage(len(oa_oc), len(e_oa)),
            "openalex_by_union": _coverage(len(e_oa & union_other), len(e_oa)),
        },
        "jaccard": {
            "openalex_s2": _jaccard(e_oa, e_s2),
            "openalex_opencitations": _jaccard(e_oa, e_oc),
            "s2_opencitations": _jaccard(e_s2, e_oc),
        },
    }


def compute_edge_agreement(
    *,
    paths: DatasetPaths,
    tier: str = "core",
    track: str = "both",
) -> Dict[str, Any]:
    targets = ["A", "B"] if track == "both" else [track]
    by_track: Dict[str, Any] = {}
    all_rows: List[Dict[str, Any]] = []

    for t in targets:
        p = paths.private_mapping_path(t, tier)
        if not p.exists():
            continue
        rows = _load_jsonl(p)
        by_track[t] = _summarize(rows)
        all_rows.extend(rows)

    overall = _summarize(all_rows) if all_rows else _summarize([])
    return {"tier": tier, "overall": overall, "by_track": by_track}
