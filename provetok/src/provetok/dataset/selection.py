"""Candidate selection protocol (plan.md Phase 1–3).

This module is used by the online pipeline; it is also unit-testable with
fixtures and does not require network access.
"""

from __future__ import annotations

import json
import heapq
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkCandidate:
    openalex_id: str
    title: str
    publication_year: Optional[int]
    doi: Optional[str]
    arxiv_id: Optional[str]
    cited_by_count: int
    referenced_works: Tuple[str, ...]
    concept_ids: Tuple[str, ...]
    raw: Dict[str, Any]


def parse_openalex_work(w: Dict[str, Any]) -> WorkCandidate:
    oa_id = str(w.get("id", ""))
    title = str(w.get("title", ""))
    year = w.get("publication_year")
    try:
        year_int = int(year) if year is not None else None
    except Exception:
        year_int = None

    doi = w.get("doi") or None
    cited_by = int(w.get("cited_by_count", 0) or 0)

    referenced = w.get("referenced_works") or []
    referenced_ids = tuple(str(x) for x in referenced if x)

    concepts = w.get("concepts") or []
    concept_ids = tuple(str(c.get("id")) for c in concepts if c.get("id"))

    # Best-effort arXiv id from OpenAlex primary_location / ids
    arxiv_id = None
    ids = w.get("ids") or {}
    if isinstance(ids, dict):
        arxiv_id = ids.get("arxiv_id") or None

    return WorkCandidate(
        openalex_id=oa_id,
        title=title,
        publication_year=year_int,
        doi=doi,
        arxiv_id=arxiv_id,
        cited_by_count=cited_by,
        referenced_works=referenced_ids,
        concept_ids=concept_ids,
        raw=w,
    )


def build_internal_edges(candidates: Sequence[WorkCandidate]) -> List[Tuple[str, str]]:
    """Edges are (src -> dst) where src is referenced work and dst cites it."""
    ids: Set[str] = {c.openalex_id for c in candidates}
    edges: List[Tuple[str, str]] = []
    for c in candidates:
        for ref in c.referenced_works:
            if ref in ids:
                edges.append((ref, c.openalex_id))
    return edges


def pagerank_scores(
    nodes: Sequence[str],
    edges: Sequence[Tuple[str, str]],
    *,
    damping: float = 0.85,
    max_iter: int = 50,
    tol: float = 1e-8,
) -> Dict[str, float]:
    """Simple PageRank implementation (power iteration)."""
    n = len(nodes)
    if n == 0:
        return {}

    out: Dict[str, List[str]] = {u: [] for u in nodes}
    indeg: Dict[str, int] = {u: 0 for u in nodes}
    for u, v in edges:
        if u in out and v in out:
            out[u].append(v)
            indeg[v] += 1

    pr = {u: 1.0 / n for u in nodes}
    base = (1.0 - damping) / n

    for _ in range(max_iter):
        new = {u: base for u in nodes}
        # Distribute rank along outgoing edges; handle sinks by uniform redistribution
        sink_mass = sum(pr[u] for u in nodes if not out[u])
        sink_add = damping * sink_mass / n
        for u in nodes:
            new[u] += sink_add
        for u in nodes:
            if not out[u]:
                continue
            share = damping * pr[u] / len(out[u])
            for v in out[u]:
                new[v] += share
        diff = sum(abs(new[u] - pr[u]) for u in nodes)
        pr = new
        if diff < tol:
            break
    return pr


def indegree_scores(nodes: Sequence[str], edges: Sequence[Tuple[str, str]]) -> Dict[str, float]:
    indeg = {u: 0 for u in nodes}
    for u, v in edges:
        if v in indeg:
            indeg[v] += 1
    # Normalize to [0,1] range if possible
    mx = max(indeg.values()) if indeg else 0
    if mx <= 0:
        return {u: 0.0 for u in nodes}
    return {u: indeg[u] / mx for u in nodes}


def load_manual_decisions(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """Load manual decisions keyed by paper_key (OpenAlex ID / DOI / etc.)."""
    if path is None or not str(path):
        return {}
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:  # pragma: no cover
            raise ImportError("pyyaml is required: pip install pyyaml") from e
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if isinstance(raw, dict):
            raw = raw.get("decisions") or []
    else:
        # JSONL
        raw = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                raw.append(json.loads(line))

    decisions: Dict[str, Dict[str, Any]] = {}
    for d in raw:
        key = str(d.get("paper_key") or d.get("openalex_id") or d.get("doi") or "")
        if not key:
            continue
        decisions[key] = dict(d)
    return decisions


def select_works(
    candidates: Sequence[WorkCandidate],
    *,
    target_min: int,
    target_max: int,
    topic_coverage_k: int,
    centrality_weights: Dict[str, float],
    manual_decisions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[WorkCandidate]:
    """Select a subset of candidates with a greedy coverage + score heuristic."""
    manual_decisions = manual_decisions or {}

    nodes = [c.openalex_id for c in candidates]
    edges = build_internal_edges(candidates)
    pr = pagerank_scores(nodes, edges)
    indeg = indegree_scores(nodes, edges)

    def score(c: WorkCandidate) -> float:
        w_pr = float(centrality_weights.get("pagerank", 1.0))
        w_in = float(centrality_weights.get("indegree", 0.0))
        return w_pr * float(pr.get(c.openalex_id, 0.0)) + w_in * float(indeg.get(c.openalex_id, 0.0))

    # Apply hard excludes
    filtered: List[WorkCandidate] = []
    for c in candidates:
        dec = manual_decisions.get(c.openalex_id) or manual_decisions.get(c.doi or "")
        if dec and str(dec.get("action")).lower() == "exclude":
            continue
        filtered.append(c)

    # Greedy: satisfy topic coverage first, then fill by score.
    scored = sorted(filtered, key=score, reverse=True)

    selected: List[WorkCandidate] = []
    seen_topics: Set[str] = set()

    def topics_of(c: WorkCandidate) -> List[str]:
        # Use top few concept ids; stable order as provided by OpenAlex.
        return [x for x in c.concept_ids[:5] if x]

    # First pass: add if introduces a new topic
    for c in scored:
        if len(selected) >= target_max:
            break
        new_topics = [t for t in topics_of(c) if t not in seen_topics]
        if new_topics:
            selected.append(c)
            seen_topics.update(new_topics)
        if len(seen_topics) >= topic_coverage_k and len(selected) >= min(target_min, topic_coverage_k):
            break

    # Second pass: fill to target_min, then up to target_max
    for c in scored:
        if len(selected) >= target_max:
            break
        if c in selected:
            continue
        selected.append(c)
        if len(selected) >= target_min:
            break

    # Force includes
    force_include_keys = [
        k for k, d in manual_decisions.items() if str(d.get("action")).lower() == "include"
    ]
    if force_include_keys:
        by_id = {c.openalex_id: c for c in filtered}
        by_doi = {c.doi: c for c in filtered if c.doi}
        for key in force_include_keys:
            c = by_id.get(key) or by_doi.get(key)
            if c and c not in selected:
                selected.append(c)
                if len(selected) >= target_max:
                    break

    # Deterministic ordering for ID assignment: year asc, then OpenAlex id
    selected_sorted = sorted(
        selected,
        key=lambda c: (
            c.publication_year if c.publication_year is not None else 10**9,
            c.openalex_id,
        ),
    )

    return selected_sorted


def assign_local_ids(selected: Sequence[WorkCandidate], track_prefix: str) -> Dict[str, str]:
    """Assign stable local PaperIDs like A_001, A_002, ..."""
    mapping: Dict[str, str] = {}
    for i, c in enumerate(selected, start=1):
        mapping[c.openalex_id] = f"{track_prefix}_{i:03d}"
    return mapping


def stable_topological_sort(
    nodes: Sequence[str],
    edges: Sequence[Tuple[str, str]],
    *,
    priority_key: Optional[Callable[[str], Tuple[Any, ...]]] = None,
) -> List[str]:
    """Return a deterministic topological order.

    - edges are (u -> v) pairs.
    - priority_key controls which ready node is emitted first (heap order).
    - If a cycle exists, remaining nodes are appended in priority order.
    """
    if priority_key is None:
        priority_key = lambda x: (x,)

    node_set = set(nodes)
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n: [] for n in nodes}

    for u, v in edges:
        if u in node_set and v in node_set:
            adj[u].append(v)
            indeg[v] += 1

    heap: List[Tuple[Tuple[Any, ...], str]] = []
    for n in nodes:
        if indeg[n] == 0:
            heapq.heappush(heap, (priority_key(n), n))

    out: List[str] = []
    while heap:
        _, u = heapq.heappop(heap)
        if u in node_set:
            node_set.remove(u)
        out.append(u)
        for v in adj.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                heapq.heappush(heap, (priority_key(v), v))

    if node_set:
        rest = sorted(node_set, key=lambda n: (priority_key(n), n))
        logger.warning("Cycle detected in dependency graph; appending %d nodes", len(rest))
        out.extend(rest)

    return out


def derive_dependency_closed_core_paper_ids(
    mapping_rows: Sequence[Dict[str, Any]],
    *,
    core_size: int,
) -> List[str]:
    """Derive a small, dependency-closed 'core' subset from an 'extended' pool.

    Strategy: compute a stable topological order on dep->paper edges, then take a
    prefix of length core_size. This guarantees dependency closure when the
    graph is acyclic.

    priority: prefer papers with cached fulltext, then higher confidence_score,
    then higher cited_by_count, then earlier year, then paper_id.
    """
    paper_ids = [str(r.get("paper_id") or "") for r in mapping_rows if r.get("paper_id")]
    paper_set = set(paper_ids)
    if not paper_ids:
        return []

    deps_by_pid: Dict[str, List[str]] = {}
    meta_by_pid: Dict[str, Dict[str, Any]] = {}
    for r in mapping_rows:
        pid = str(r.get("paper_id") or "")
        if not pid:
            continue
        deps = [str(d) for d in (r.get("dependencies") or []) if d]
        deps_by_pid[pid] = [d for d in deps if d in paper_set]
        meta_by_pid[pid] = r

    edges: List[Tuple[str, str]] = []
    for pid, deps in deps_by_pid.items():
        for dep in deps:
            edges.append((dep, pid))

    def priority(pid: str) -> Tuple[Any, ...]:
        row = meta_by_pid.get(pid) or {}
        conf = row.get("confidence_score")
        try:
            conf_f = float(conf) if conf is not None else 0.0
        except Exception:
            conf_f = 0.0
        cited = int(row.get("cited_by_count", 0) or 0)
        year = row.get("year")
        try:
            year_i = int(year) if year is not None else 10**9
        except Exception:
            year_i = 10**9
        has_ft = bool(row.get("pdf_sha256")) or bool(row.get("source_paths") or [])
        # heapq is min-first; smaller is earlier
        return (0 if has_ft else 1, -conf_f, -cited, year_i, pid)

    order = stable_topological_sort(paper_ids, edges, priority_key=priority)
    k = max(0, min(int(core_size), len(order)))
    return order[:k]
