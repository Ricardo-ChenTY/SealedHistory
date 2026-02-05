"""Candidate selection protocol (plan.md Phase 1–3).

This module is used by the online pipeline; it is also unit-testable with
fixtures and does not require network access.
"""

from __future__ import annotations

import hashlib
import json
import heapq
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import yaml

logger = logging.getLogger(__name__)


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$", re.IGNORECASE)
_ARXIV_OLD_RE = re.compile(r"^[a-z\-]+(?:\.[a-z\-]+)?/\d{7}(?:v\d+)?$", re.IGNORECASE)


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


def _parse_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    if _FLOAT_RE.fullmatch(s):
        return float(s)
    return default


def normalize_doi(doi: Any) -> str:
    s = str(doi or "").strip()
    if not s:
        return ""
    low = s.lower()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if low.startswith(prefix):
            s = s[len(prefix) :]
            break
    low = s.lower()
    if low.startswith("doi:"):
        s = s[4:]
    return str(s).strip().lower()


def looks_like_doi(doi: Any) -> bool:
    s = normalize_doi(doi)
    if not s:
        return False
    return bool(_DOI_RE.fullmatch(s))


def normalize_arxiv_id(arxiv_id: Any) -> str:
    s = str(arxiv_id or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low.startswith("arxiv:"):
        s = s[6:]
    s = str(s).strip().lower()
    return s


def looks_like_arxiv_id(arxiv_id: Any) -> bool:
    s = normalize_arxiv_id(arxiv_id)
    if not s:
        return False
    return bool(_ARXIV_NEW_RE.fullmatch(s) or _ARXIV_OLD_RE.fullmatch(s))


def normalize_openalex_id(openalex_id: Any) -> str:
    s = str(openalex_id or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low.startswith("http://openalex.org/"):
        s = "https://openalex.org/" + s.split("/")[-1]
    if low.startswith("https://openalex.org/"):
        return s
    if s.startswith("W"):
        return f"https://openalex.org/{s}"
    return s


def title_sha256_12(title: Any) -> str:
    s = str(title or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return h[:12]


def compute_paper_key(
    *,
    doi: Any,
    arxiv_id: Any,
    openalex_id: Any,
    title: Any,
) -> str:
    if looks_like_doi(doi):
        return f"doi:{normalize_doi(doi)}"

    if looks_like_arxiv_id(arxiv_id):
        return f"arxiv:{normalize_arxiv_id(arxiv_id)}"

    oa_norm = normalize_openalex_id(openalex_id)
    if not oa_norm:
        return "openalex:unknown|title_sha256_12:" + title_sha256_12(title)

    return f"openalex:{oa_norm}|title_sha256_12:{title_sha256_12(title)}"


def manual_lookup_keys(candidate: "WorkCandidate") -> List[str]:
    keys = [candidate.paper_key]

    doi_norm = normalize_doi(candidate.doi)
    if doi_norm:
        keys.append(f"doi:{doi_norm}")
        keys.append(doi_norm)
        keys.append(str(candidate.doi))

    arxiv_norm = normalize_arxiv_id(candidate.arxiv_id)
    if arxiv_norm:
        keys.append(f"arxiv:{arxiv_norm}")
        keys.append(arxiv_norm)
        keys.append(str(candidate.arxiv_id))

    oa_norm = normalize_openalex_id(candidate.openalex_id)
    if oa_norm:
        keys.append(f"openalex:{oa_norm}")
        keys.append(oa_norm)

    # Also accept the un-hashed prefix for openalex fallback keys.
    if candidate.paper_key.startswith("openalex:") and "|title_sha256_12:" in candidate.paper_key:
        keys.append(candidate.paper_key.split("|title_sha256_12:", 1)[0])

    return [str(k) for k in keys if str(k).strip()]


def match_manual_decision(
    candidate: "WorkCandidate",
    decisions: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    if not decisions:
        return None, None

    matches: List[str] = []
    for k in manual_lookup_keys(candidate):
        if k in decisions:
            matches.append(k)

    if not matches:
        return None, None

    actions: Set[str] = set()
    for k in matches:
        dec = decisions.get(k) or {}
        a = str(dec.get("action") or "").strip().lower()
        if a:
            actions.add(a)
    if len(actions) > 1:
        raise ValueError(f"Conflicting manual decisions for {candidate.paper_key}: keys={matches}")

    k0 = matches[0]
    return k0, decisions.get(k0)


@dataclass(frozen=True)
class WorkCandidate:
    paper_key: str
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
    year_int = _parse_int(year)

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
        paper_key=compute_paper_key(
            doi=doi,
            arxiv_id=arxiv_id,
            openalex_id=oa_id,
            title=title,
        ),
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


def citation_velocity_scores(
    candidates: Sequence[WorkCandidate],
    *,
    ref_year: Optional[int] = None,
) -> Dict[str, float]:
    """Approximate 'burst/growth' via citations-per-year, normalized to [0,1]."""
    years = [c.publication_year for c in candidates if isinstance(c.publication_year, int)]
    if ref_year is None:
        ref_year = max(years) if years else 2025

    raw: Dict[str, float] = {}
    for c in candidates:
        y = c.publication_year if isinstance(c.publication_year, int) else None
        age = max(1, int(ref_year) - int(y) + 1) if y else 10
        raw[c.openalex_id] = float(c.cited_by_count) / float(age)

    mx = max(raw.values()) if raw else 0.0
    if mx <= 0.0:
        return {c.openalex_id: 0.0 for c in candidates}
    return {k: float(v) / mx for k, v in raw.items()}


def bridge_scores(
    nodes: Sequence[str],
    edges: Sequence[Tuple[str, str]],
    *,
    community_by_node: Dict[str, str],
) -> Dict[str, float]:
    """Approximate 'bridge' via cross-community neighbor ratio in the internal graph."""
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    node_set = set(nodes)
    for u, v in edges:
        if u in node_set and v in node_set:
            adj[u].append(v)
            adj[v].append(u)

    out: Dict[str, float] = {}
    for n in nodes:
        neigh = adj.get(n, [])
        if not neigh:
            out[n] = 0.0
            continue
        c0 = community_by_node.get(n, "")
        cross = sum(1 for m in neigh if community_by_node.get(m, "") != c0)
        out[n] = float(cross) / float(len(neigh))

    # Normalize to [0,1] by max.
    mx = max(out.values()) if out else 0.0
    if mx <= 0.0:
        return {n: 0.0 for n in nodes}
    return {n: float(out[n]) / mx for n in nodes}


def compute_selection_signals(
    candidates: Sequence[WorkCandidate],
    *,
    ref_year: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Compute deterministic selection signals for auditability.

    Signals are publish-safe and do not depend on any LLM outputs.
    """
    nodes = [c.openalex_id for c in candidates]
    edges = build_internal_edges(candidates)
    pr = pagerank_scores(nodes, edges)
    indeg = indegree_scores(nodes, edges)
    vel = citation_velocity_scores(candidates, ref_year=ref_year)

    community_by: Dict[str, str] = {}
    for c in candidates:
        community_by[c.openalex_id] = str(c.concept_ids[0]) if c.concept_ids else ""
    bridge = bridge_scores(nodes, edges, community_by_node=community_by)

    signals: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        oid = c.openalex_id
        signals[oid] = {
            "pagerank": float(pr.get(oid, 0.0) or 0.0),
            "indegree": float(indeg.get(oid, 0.0) or 0.0),
            "citation_velocity": float(vel.get(oid, 0.0) or 0.0),
            "bridge": float(bridge.get(oid, 0.0) or 0.0),
            "community_id": community_by.get(oid, ""),
        }
    return signals


def load_manual_decisions(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """Load manual decisions keyed by paper_key (OpenAlex ID / DOI / etc.)."""
    if path is None or not str(path):
        return {}
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() in (".yaml", ".yml"):
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
    for idx, d in enumerate(raw):
        if not isinstance(d, dict):
            raise ValueError(f"manual decision row {idx} is not an object: {type(d).__name__}")

        dd = dict(d)
        action = str(dd.get("action") or "").strip().lower()
        if action not in ("include", "exclude"):
            raise ValueError(f"manual decision row {idx} has invalid action: {dd.get('action')}")

        reason_tag = str(dd.get("reason_tag") or "").strip()
        reviewer_id = str(dd.get("reviewer_id") or "").strip()
        if not reason_tag:
            raise ValueError(f"manual decision row {idx} missing reason_tag")
        if not reviewer_id:
            raise ValueError(f"manual decision row {idx} missing reviewer_id")

        raw_key = str(dd.get("paper_key") or "").strip()
        openalex_id = dd.get("openalex_id") or ""
        doi = dd.get("doi") or ""
        arxiv_id = dd.get("arxiv_id") or ""
        title = dd.get("title") or ""

        if not raw_key and not str(openalex_id).strip() and not str(doi).strip() and not str(arxiv_id).strip():
            raise ValueError(f"manual decision row {idx} missing paper_key/openalex_id/doi/arxiv_id")

        key = ""
        if raw_key:
            raw_key_stripped = raw_key.strip()
            if raw_key_stripped.startswith("doi:") or looks_like_doi(raw_key_stripped):
                key = "doi:" + normalize_doi(raw_key_stripped)
            elif raw_key_stripped.startswith("arxiv:") or looks_like_arxiv_id(raw_key_stripped):
                key = "arxiv:" + normalize_arxiv_id(raw_key_stripped)
            elif raw_key_stripped.startswith("openalex:"):
                key = raw_key_stripped
            else:
                oa_norm = normalize_openalex_id(raw_key_stripped)
                if oa_norm.startswith("https://openalex.org/"):
                    key = "openalex:" + oa_norm

        if not key:
            key = compute_paper_key(doi=doi, arxiv_id=arxiv_id, openalex_id=openalex_id, title=title)

        if not key:
            raise ValueError(f"manual decision row {idx} missing paper_key fields")

        dd["paper_key"] = key
        decisions[key] = dd
    return decisions


def select_works(
    candidates: Sequence[WorkCandidate],
    *,
    target_min: int,
    target_max: int,
    topic_coverage_k: int,
    centrality_weights: Dict[str, float],
    manual_decisions: Optional[Dict[str, Dict[str, Any]]] = None,
    ref_year: Optional[int] = None,
    return_signals: bool = False,
) -> List[WorkCandidate] | Tuple[List[WorkCandidate], Dict[str, Dict[str, Any]]]:
    """Select a subset of candidates with a greedy coverage + score heuristic."""
    manual_decisions = manual_decisions or {}

    signals_by_id = compute_selection_signals(candidates, ref_year=ref_year)

    def score(c: WorkCandidate) -> float:
        w_pr = float(centrality_weights.get("pagerank", 1.0))
        w_in = float(centrality_weights.get("indegree", 0.0))
        w_vel = float(centrality_weights.get("citation_velocity", 0.0))
        w_bridge = float(centrality_weights.get("bridge", 0.0))

        s = signals_by_id.get(c.openalex_id) or {}
        return (
            w_pr * float(s.get("pagerank", 0.0) or 0.0)
            + w_in * float(s.get("indegree", 0.0) or 0.0)
            + w_vel * float(s.get("citation_velocity", 0.0) or 0.0)
            + w_bridge * float(s.get("bridge", 0.0) or 0.0)
        )

    # Apply hard excludes
    filtered: List[WorkCandidate] = []
    for c in candidates:
        _, dec = match_manual_decision(c, manual_decisions)
        if dec and str(dec.get("action") or "").strip().lower() == "exclude":
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
        by_key: Dict[str, WorkCandidate] = {}
        for c in filtered:
            for k in manual_lookup_keys(c):
                by_key[k] = c
        for key in force_include_keys:
            c = by_key.get(key)
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

    return (selected_sorted, signals_by_id) if return_signals else selected_sorted


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
        conf_f = _parse_float(conf, default=0.0)
        cited = int(row.get("cited_by_count", 0) or 0)
        year = row.get("year")
        year_i = _parse_int(year) if year is not None else None
        year_i = year_i if year_i is not None else 10**9
        has_ft = bool(row.get("pdf_sha256")) or bool(row.get("source_paths") or [])
        # heapq is min-first; smaller is earlier
        return (0 if has_ft else 1, -conf_f, -cited, year_i, pid)

    order = stable_topological_sort(paper_ids, edges, priority_key=priority)
    k = max(0, min(int(core_size), len(order)))
    return order[:k]
