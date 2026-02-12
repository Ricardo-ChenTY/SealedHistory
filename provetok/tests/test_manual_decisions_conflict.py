"""Manual decision conflicts must fail fast with a clear error."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_conflicting_manual_decisions_raise(tmp_path: Path) -> None:
    out_root = tmp_path / "exports"
    version = "test-manual-conflict"

    s2_id = "1111111111111111111111111111111111111111"
    manual_path = tmp_path / "manual_decisions.jsonl"
    _write_jsonl(
        manual_path,
        [
            {
                "paper_key": f"s2:{s2_id}",
                "action": "include",
                "reason_tag": "manual_include_test",
                "reviewer_id": "r1",
                "evidence": "included by test",
            },
            {
                "paper_key": f"openalex:S2:{s2_id}",
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
                "    s2:",
                "      keywords: []",
                '      fields_of_study: ["Computer Science"]',
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

    works_path = out_root / version / "private" / "raw_snapshots" / "s2" / "works_track_A.jsonl"
    _write_jsonl(
        works_path,
        [
            {
                "paperId": s2_id,
                "title": "Paper One",
                "year": 2020,
                "citationCount": 10,
                "references": [],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "one two",
            }
        ],
    )

    with pytest.raises(ValueError):
        build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="A")
