"""Experiment helper: offline online-pipeline run with manual decisions.

This script creates a tiny S2 snapshot and a manual_decisions file under a
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
    parser.add_argument(
        "--disable_manual_decisions",
        action="store_true",
        help="Run the same offline export without manual_decisions_file configured.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    export_root = run_dir / "exports"
    cfg_path = run_dir / "cfg.yaml"
    manual_path = run_dir / "manual_decisions.jsonl"

    if not args.disable_manual_decisions:
        _write_jsonl(
            manual_path,
            [
                {
                    "paper_key": "s2:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "action": "exclude",
                    "reason_tag": "manual_exclude_exp",
                    "reviewer_id": "r1",
                    "evidence": "excluded by experiment",
                },
                {
                    "paper_key": "s2:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "action": "include",
                    "reason_tag": "manual_include_exp",
                    "reviewer_id": "r1",
                    "evidence": "included by experiment",
                },
                {
                    "paper_key": "s2:cccccccccccccccccccccccccccccccccccccccc",
                    "action": "exclude",
                    "reason_tag": "manual_exclude_exp",
                    "reviewer_id": "r1",
                    "evidence": "excluded by experiment",
                },
                {
                    "paper_key": "s2:dddddddddddddddddddddddddddddddddddddddd",
                    "action": "include",
                    "reason_tag": "manual_include_exp",
                    "reviewer_id": "r1",
                    "evidence": "included by experiment",
                },
            ],
        )

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    manual_cfg = f'"{manual_path.as_posix()}"' if not args.disable_manual_decisions else '""'
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
                "    s2:",
                "      keywords: []",
                "      year_from: 2009",
                "      year_to: 2025",
                "  B:",
                '    name: "test"',
                "    core_size: 1",
                "    extended_size: 1",
                "    s2:",
                "      keywords: []",
                "      year_from: 2009",
                "      year_to: 2025",
                "selection:",
                "  topic_coverage_k: 1",
                "  backfill_pool_multiplier: 1.0",
                "  backfill_batch_size: 1",
                f"  manual_decisions_file: {manual_cfg}",
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

    snapshot_dir = export_root / args.dataset_version / "private" / "raw_snapshots" / "s2"
    _write_jsonl(
        snapshot_dir / "works_track_A.jsonl",
        [
            {
                "paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Paper One",
                "year": 2020,
                "citationCount": 10,
                "references": [],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "one two",
            },
            {
                "paperId": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "title": "Paper Two",
                "year": 2021,
                "citationCount": 20,
                "references": [{"paperId": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}],
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
                "paperId": "cccccccccccccccccccccccccccccccccccccccc",
                "title": "Paper Three",
                "year": 2019,
                "citationCount": 7,
                "references": [],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "three paper",
            },
            {
                "paperId": "dddddddddddddddddddddddddddddddddddddddd",
                "title": "Paper Four",
                "year": 2022,
                "citationCount": 9,
                "references": [{"paperId": "cccccccccccccccccccccccccccccccccccccccc"}],
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {},
                "abstract": "four paper",
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
