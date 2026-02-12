"""Offline online-pipeline runs must not use network or LLM calls."""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset
from provetok.utils.llm_client import LLMClient


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_offline_build_uses_no_network(monkeypatch, tmp_path: Path) -> None:
    out_root = tmp_path / "exports"
    version = "test-offline-no-network"

    monkeypatch.setenv("LLM_API_KEY", "dummy")

    def blocked_chat(self, *args, **kwargs):
        raise AssertionError("LLM chat must not be called in offline mode")

    monkeypatch.setattr(LLMClient, "chat", blocked_chat)

    def blocked_urlopen(*args, **kwargs):
        raise AssertionError("Network access must not be used in offline mode")

    monkeypatch.setattr(urllib.request, "urlopen", blocked_urlopen)

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

    build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="A")

    sel_path = out_root / version / "public" / "selection_log_extended.jsonl"
    assert sel_path.exists()
