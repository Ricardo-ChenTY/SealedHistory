"""Tests for canonical paper_key generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.selection import (
    compute_paper_key,
    normalize_arxiv_id,
    normalize_doi,
    title_sha256_12,
)


def test_compute_paper_key_prefers_doi():
    key = compute_paper_key(
        doi="https://doi.org/10.1234/AbC.Def",
        arxiv_id="2101.12345v2",
        openalex_id="https://openalex.org/W1",
        title="Paper",
    )
    assert key == "doi:10.1234/abc.def"


def test_compute_paper_key_arxiv_when_no_doi():
    key = compute_paper_key(
        doi="",
        arxiv_id="arXiv:2101.12345V2",
        openalex_id="https://openalex.org/W1",
        title="Paper",
    )
    assert key == "arxiv:2101.12345v2"


def test_compute_paper_key_openalex_fallback_has_title_hash():
    key = compute_paper_key(
        doi="",
        arxiv_id="",
        openalex_id="https://openalex.org/W123",
        title="Hello   World",
    )
    assert key.startswith("openalex:https://openalex.org/W123|title_sha256_12:")
    assert key.endswith(title_sha256_12("hello world"))


def test_normalizers_are_stable():
    assert normalize_doi("DOI:10.1000/XYZ") == "10.1000/xyz"
    assert normalize_arxiv_id("arXiv:2101.12345v3") == "2101.12345v3"

