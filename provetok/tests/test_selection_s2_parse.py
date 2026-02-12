"""Tests for S2 candidate parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.selection import parse_s2_work


def test_parse_s2_work_maps_ids_refs_and_fos():
    raw = {
        "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
        "title": "Example Paper",
        "abstract": "This is an abstract.",
        "year": 2021,
        "citationCount": 123,
        "externalIds": {"DOI": "10.1234/ABC.DEF", "ArXiv": "2101.12345"},
        "references": [{"paperId": "1111111111111111111111111111111111111111"}],
        "fieldsOfStudy": ["Computer Science"],
    }
    c = parse_s2_work(raw)
    assert c.s2_id == "649def34f8be52c8b66281af98ae884c09aef38b"
    assert c.openalex_id == "S2:649def34f8be52c8b66281af98ae884c09aef38b"
    assert c.paper_key == "doi:10.1234/abc.def"
    assert c.referenced_works == ("S2:1111111111111111111111111111111111111111",)
    assert c.concept_ids == ("s2fos:computer_science",)
    assert c.raw.get("_source_kind") == "s2_search"

