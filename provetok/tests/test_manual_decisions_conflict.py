"""Manual decision conflicts must fail fast with a clear error."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset
from provetok.dataset.selection import title_sha256_12


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_conflicting_manual_decisions_raise(tmp_path: Path) -> None:
    out_root = tmp_path / "exports"
    version = "test-manual-conflict"

    canonical = (
        "openalex:https://openalex.org/W1|title_sha256_12:" + title_sha256_12("Paper One")
    )
    manual_path = tmp_path / "manual_decisions.jsonl"
    _write_jsonl(
        manual_path,
        [
            {
                "paper_key": canonical,
                "action": "include",
                "reason_tag": "manual_include_test",
                "reviewer_id": "r1",
                "evidence": "included by test",
            },
            {
                "paper_key": "https://openalex.org/W1",
                "action": "exclude",
                "reason_tag": "manual_exclude_test",
                "reviewer_id": "r1",
                "evidence": "excluded by test",
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
                "selection:",
                "  topic_coverage_k: 1",
                "  backfill_pool_multiplier: 1.0",
                "  backfill_batch_size: 1",
                f'  manual_decisions_file: \"{manual_path.as_posix()}\"',
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
            }
        ],
    )

    with pytest.raises(ValueError):
        build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="A")

