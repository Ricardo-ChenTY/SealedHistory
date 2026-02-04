"""Tests for selection signals (burst/bridge approximations)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.selection import WorkCandidate, compute_selection_signals, select_works


def _cand(oid: str, *, year: int, cited: int, refs=(), concepts=()):
    return WorkCandidate(
        openalex_id=oid,
        title=f"t-{oid}",
        publication_year=year,
        doi=None,
        arxiv_id=None,
        cited_by_count=cited,
        referenced_works=tuple(refs),
        concept_ids=tuple(concepts),
        raw={"id": oid, "title": f"t-{oid}"},
    )


def test_compute_selection_signals_keys_and_ranges():
    c1 = _cand("W1", year=2020, cited=10, refs=(), concepts=("C1",))
    c2 = _cand("W2", year=2021, cited=100, refs=("W1",), concepts=("C1",))
    c3 = _cand("W3", year=2022, cited=50, refs=("W1", "W2"), concepts=("C2",))

    sig = compute_selection_signals([c1, c2, c3], ref_year=2022)
    assert set(sig.keys()) == {"W1", "W2", "W3"}

    for v in sig.values():
        for k in ("pagerank", "indegree", "citation_velocity", "bridge"):
            assert 0.0 <= float(v[k]) <= 1.0
        assert "community_id" in v


def test_select_works_can_return_signals():
    c1 = _cand("W1", year=2020, cited=10, refs=(), concepts=("C1",))
    c2 = _cand("W2", year=2021, cited=100, refs=("W1",), concepts=("C1",))
    c3 = _cand("W3", year=2022, cited=50, refs=("W1", "W2"), concepts=("C2",))

    selected, sig = select_works(
        [c1, c2, c3],
        target_min=2,
        target_max=2,
        topic_coverage_k=1,
        centrality_weights={"pagerank": 1.0, "indegree": 0.5, "citation_velocity": 0.3, "bridge": 0.2},
        ref_year=2022,
        return_signals=True,
    )
    assert len(selected) == 2
    assert set(sig.keys()) == {"W1", "W2", "W3"}

