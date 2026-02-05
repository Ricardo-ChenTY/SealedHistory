"""Tests that manual decisions are logged into public selection logs."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_manual_decisions_are_logged(tmp_path: Path) -> None:
    out_root = tmp_path / "exports"
    version = "test-manual-decisions"

    manual_path = tmp_path / "manual_decisions.jsonl"
    _write_jsonl(
        manual_path,
        [
            {
                "paper_key": "https://openalex.org/W1",
                "action": "exclude",
                "reason_tag": "manual_exclude_test",
                "reviewer_id": "r1",
                "evidence": "excluded by test",
            },
            {
                "paper_key": "https://openalex.org/W2",
                "action": "include",
                "reason_tag": "manual_include_test",
                "reviewer_id": "r1",
                "evidence": "included by test",
            },
        ],
    )

    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                f'dataset_version: "{version}"',
                'export_root: "unused"',
                "tracks:",
                "  A:",
                '    name: "test"',
                "    core_size: 1",
                "    extended_size: 1",
                "    openalex:",
                "      concepts: []",
                "      keywords: []",
                "      venues: []",
                "      year_from: 2009",
                "      year_to: 2025",
                "sources:",
                "  openalex:",
                '    base_url: "https://api.openalex.org"',
                '    mailto: ""',
                "    per_page: 200",
                "    max_pages: 1",
                "    rate_limit_qps: 3",
                "  s2:",
                '    base_url: "https://api.semanticscholar.org/graph/v1"',
                '    api_key_env: "S2_API_KEY"',
                "    rate_limit_qps: 1",
                "selection:",
                "  topic_coverage_k: 1",
                "  backfill_pool_multiplier: 1.0",
                "  backfill_batch_size: 1",
                f'  manual_decisions_file: "{manual_path.as_posix()}"',
                "record_build:",
                '  mode: "llm"',
                "  require_llm: false",
                "  strict_paraphrase: false",
                "qa:",
                "  edge_coverage_threshold: 0.0",
                "  schema_pass_rate_required: 0.0",
                "  consistency_pass_rate_required: 0.0",
                "seeds:",
                "  public_seeds: [42]",
                "  private_seeds: []",
                "fulltext:",
                "  policy: \"none\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    works_path = out_root / version / "private" / "raw_snapshots" / "openalex" / "works_track_A.jsonl"
    _write_jsonl(
        works_path,
        [
            {
                "id": "https://openalex.org/W1",
                "title": "Paper One",
                "publication_year": 2020,
                "doi": None,
                "ids": {"arxiv_id": None},
                "concepts": [{"id": "C1"}],
                "cited_by_count": 10,
                "referenced_works": [],
                "abstract_inverted_index": {"one": [0], "two": [1]},
            },
            {
                "id": "https://openalex.org/W2",
                "title": "Paper Two",
                "publication_year": 2021,
                "doi": None,
                "ids": {"arxiv_id": None},
                "concepts": [{"id": "C1"}],
                "cited_by_count": 20,
                "referenced_works": ["https://openalex.org/W1"],
                "abstract_inverted_index": {"alpha": [0], "beta": [1]},
            },
        ],
    )

    build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="A")

    sel_path = out_root / version / "public" / "selection_log_extended.jsonl"
    assert sel_path.exists()
    rows = [json.loads(line) for line in sel_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    manual_rows = [r for r in rows if r.get("reviewer_id") == "r1"]
    assert manual_rows
    assert all(str(r.get("paper_key") or "").startswith("openalex:") for r in manual_rows)

    map_path = out_root / version / "private" / "mapping_key" / "paper_id_map_track_A_extended.jsonl"
    assert map_path.exists()
    first = json.loads(map_path.read_text(encoding="utf-8").splitlines()[0])
    assert "paper_key" in first

