"""Tests for SDG (Sealed Domain Generator)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, ExperimentResult, load_records
from provetok.sdg.codebook import Codebook
from provetok.sdg.sealer import SDGPipeline, LexicalSealer, StructuralSealer, NumericSealer


def _make_sample_record() -> PaperRecord:
    return PaperRecord(
        paper_id="A_001",
        title="Deep Residual Learning",
        phase="mid",
        background="Very deep networks suffer from degradation.",
        mechanism="Shortcut connections: learn residual F(x) = H(x) - x. Stack 152 layers.",
        experiment="1000-class benchmark. Metric: top-5 error.",
        results=ExperimentResult(metric_main=0.964, delta_vs_prev=0.031),
        dependencies=["A_000"],
        keywords=["residual learning", "skip connection", "deep network"],
        year=2015,
        venue="CVPR",
        authors=["K. He"],
    )


def test_codebook_deterministic():
    cb1 = Codebook(seed=42)
    cb2 = Codebook(seed=42)
    t1 = cb1.seal_term("residual learning", "keyword")
    t2 = cb2.seal_term("residual learning", "keyword")
    assert t1 == t2, "Same seed should produce same pseudotoken"


def test_codebook_bijective():
    cb = Codebook(seed=42)
    pseudo = cb.seal_term("convolution", "keyword")
    assert cb.reverse_lookup(pseudo) == "convolution"


def test_l1_sealing():
    rec = _make_sample_record()
    cb = Codebook(seed=42)
    l1 = LexicalSealer(cb)
    sealed = l1.seal(rec)

    # Title should be replaced
    assert sealed.title != rec.title
    # Keywords should be replaced
    assert sealed.keywords != rec.keywords
    assert len(sealed.keywords) == len(rec.keywords)
    # Year should be removed
    assert sealed.year is None
    # paper_id preserved
    assert sealed.paper_id == rec.paper_id
    # dependencies preserved
    assert sealed.dependencies == rec.dependencies


def test_l2_sealing():
    rec = _make_sample_record()
    l2 = StructuralSealer(seed=42)
    sealed = l2.seal(rec)

    # "skip connection" should be rewritten
    assert "skip connection" not in sealed.mechanism.lower() or "bypass" in sealed.mechanism.lower()
    # paper_id unchanged
    assert sealed.paper_id == rec.paper_id


def test_l3_sealing():
    rec = _make_sample_record()
    l3 = NumericSealer(n_bins=10, seed=42)
    sealed = l3.seal(rec)

    # Results should be perturbed but close
    assert sealed.results.metric_main != rec.results.metric_main
    assert abs(sealed.results.metric_main - rec.results.metric_main) < 0.15


def test_full_pipeline():
    rec = _make_sample_record()
    pipeline = SDGPipeline(seed=42, enable_l1=True, enable_l2=True, enable_l3=True)
    sealed = pipeline.seal_record(rec)

    # Basic sanity
    assert sealed.paper_id == rec.paper_id
    assert sealed.title != rec.title
    assert sealed.year is None
    assert sealed.keywords != rec.keywords


def test_pipeline_with_real_data():
    data_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "micro_history_a.jsonl"
    if not data_path.exists():
        return  # skip if data not available

    records = load_records(data_path)
    assert len(records) == 20

    pipeline = SDGPipeline(seed=42)
    sealed = pipeline.seal_records(records)
    assert len(sealed) == 20

    # No real keywords should survive in sealed records
    for s, r in zip(sealed, records):
        for kw in r.keywords:
            assert kw not in s.mechanism, f"Keyword '{kw}' leaked into sealed mechanism"


if __name__ == "__main__":
    test_codebook_deterministic()
    print("PASS: test_codebook_deterministic")
    test_codebook_bijective()
    print("PASS: test_codebook_bijective")
    test_l1_sealing()
    print("PASS: test_l1_sealing")
    test_l2_sealing()
    print("PASS: test_l2_sealing")
    test_l3_sealing()
    print("PASS: test_l3_sealing")
    test_full_pipeline()
    print("PASS: test_full_pipeline")
    test_pipeline_with_real_data()
    print("PASS: test_pipeline_with_real_data")
    print("\nAll tests passed!")
