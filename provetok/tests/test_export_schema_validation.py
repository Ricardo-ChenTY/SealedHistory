"""Validate selection logs and mapping rows against JSON schemas."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jsonschema import Draft202012Validator

from provetok.dataset.build import build_dataset


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_export_rows_match_schemas(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schema_dir = repo_root / "docs" / "schemas"

    selection_schema = json.loads((schema_dir / "selection_log_row.schema.json").read_text(encoding="utf-8"))
    mapping_schema = json.loads((schema_dir / "paper_id_map_row.schema.json").read_text(encoding="utf-8"))
    v_sel = Draft202012Validator(selection_schema)
    v_map = Draft202012Validator(mapping_schema)

    out_root = tmp_path / "exports"
    version = "test-schema-validation"

    manual_path = tmp_path / "manual_decisions.jsonl"
    _write_jsonl(
        manual_path,
        [
            {
                "paper_key": "s2:1111111111111111111111111111111111111111",
                "action": "exclude",
                "reason_tag": "manual_exclude_test",
                "reviewer_id": "r1",
                "evidence": "excluded by test",
            },
            {
                "paper_key": "s2:2222222222222222222222222222222222222222",
                "action": "include",
                "reason_tag": "manual_include_test",
                "reviewer_id": "r1",
                "evidence": "included by test",
            },
            {
                "paper_key": "s2:3333333333333333333333333333333333333333",
                "action": "exclude",
                "reason_tag": "manual_exclude_test",
                "reviewer_id": "r1",
                "evidence": "excluded by test",
            },
            {
                "paper_key": "s2:4444444444444444444444444444444444444444",
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
                "    s2:",
                "      keywords: []",
                '      fields_of_study: ["Computer Science"]',
                "      year_from: 2009",
                "      year_to: 2025",
                "  B:",
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

    snapshot_dir = out_root / version / "private" / "raw_snapshots" / "s2"
    _write_jsonl(
        snapshot_dir / "works_track_A.jsonl",
        [
            {
                "paperId": "1111111111111111111111111111111111111111",
                "title": "Paper One",
                "year": 2020,
                "citationCount": 10,
                "references": [],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "one two",
            },
            {
                "paperId": "2222222222222222222222222222222222222222",
                "title": "Paper Two",
                "year": 2021,
                "citationCount": 20,
                "references": [{"paperId": "1111111111111111111111111111111111111111"}],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "alpha beta",
            },
        ],
    )
    _write_jsonl(
        snapshot_dir / "works_track_B.jsonl",
        [
            {
                "paperId": "3333333333333333333333333333333333333333",
                "title": "Paper Three",
                "year": 2019,
                "citationCount": 7,
                "references": [],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "three paper",
            },
            {
                "paperId": "4444444444444444444444444444444444444444",
                "title": "Paper Four",
                "year": 2022,
                "citationCount": 9,
                "references": [{"paperId": "3333333333333333333333333333333333333333"}],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "four paper",
            },
        ],
    )

    build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="both")

    for tier in ("extended", "core"):
        p = out_root / version / "public" / f"selection_log_{tier}.jsonl"
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                v_sel.validate(json.loads(line))

    for t in ("A", "B"):
        for tier in ("extended", "core"):
            p = out_root / version / "private" / "mapping_key" / f"paper_id_map_track_{t}_{tier}.jsonl"
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    v_map.validate(json.loads(line))
