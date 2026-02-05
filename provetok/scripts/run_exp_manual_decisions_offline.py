"""Experiment helper: offline online-pipeline run with manual decisions.

This script creates a tiny OpenAlex snapshot and a manual_decisions file under a
`runs/` directory, then runs the dataset build in offline mode. It is used by
`docs/experiment.md` to prove selection-log auditability and paper_key plumbing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", default="runs/EXP-006", help="Directory to write experiment artifacts")
    parser.add_argument("--dataset_version", default="exp-006-manual-decisions")
    parser.add_argument("--track", choices=["A", "B", "both"], default="A")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    export_root = run_dir / "exports"
    cfg_path = run_dir / "cfg.yaml"
    manual_path = run_dir / "manual_decisions.jsonl"

    _write_jsonl(
        manual_path,
        [
            {
                "paper_key": "https://openalex.org/W1",
                "action": "exclude",
                "reason_tag": "manual_exclude_exp",
                "reviewer_id": "r1",
                "evidence": "excluded by experiment",
            },
            {
                "paper_key": "https://openalex.org/W2",
                "action": "include",
                "reason_tag": "manual_include_exp",
                "reviewer_id": "r1",
                "evidence": "included by experiment",
            },
            {
                "paper_key": "https://openalex.org/W3",
                "action": "exclude",
                "reason_tag": "manual_exclude_exp",
                "reviewer_id": "r1",
                "evidence": "excluded by experiment",
            },
            {
                "paper_key": "https://openalex.org/W4",
                "action": "include",
                "reason_tag": "manual_include_exp",
                "reviewer_id": "r1",
                "evidence": "included by experiment",
            },
        ],
    )

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        "\n".join(
            [
                f'dataset_version: "{args.dataset_version}"',
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
                "  B:",
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

    snapshot_dir = export_root / args.dataset_version / "private" / "raw_snapshots" / "openalex"
    _write_jsonl(
        snapshot_dir / "works_track_A.jsonl",
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
    _write_jsonl(
        snapshot_dir / "works_track_B.jsonl",
        [
            {
                "id": "https://openalex.org/W3",
                "title": "Paper Three",
                "publication_year": 2019,
                "doi": None,
                "ids": {"arxiv_id": None},
                "concepts": [{"id": "C2"}],
                "cited_by_count": 7,
                "referenced_works": [],
                "abstract_inverted_index": {"three": [0], "paper": [1]},
            },
            {
                "id": "https://openalex.org/W4",
                "title": "Paper Four",
                "publication_year": 2022,
                "doi": None,
                "ids": {"arxiv_id": None},
                "concepts": [{"id": "C2"}],
                "cited_by_count": 9,
                "referenced_works": ["https://openalex.org/W3"],
                "abstract_inverted_index": {"four": [0], "paper": [1]},
            },
        ],
    )

    build_dataset(config_path=cfg_path, offline=True, out_root=export_root, track=args.track)

    sel = export_root / args.dataset_version / "public" / "selection_log_extended.jsonl"
    text = sel.read_text(encoding="utf-8")
    out = run_dir / "check_manual.log"
    out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
