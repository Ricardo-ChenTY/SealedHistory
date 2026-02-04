"""Tests for provenance snapshot references in (offline) online pipeline."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset
from provetok.dataset.config import load_dataset_config


def test_offline_online_build_adds_snapshot_refs():
    import yaml

    with tempfile.TemporaryDirectory() as td:
        out_root = Path(td)

        cfg = {
            "dataset_version": "offline-online-test",
            "export_root": str(out_root),
            "tracks": {
                "A": {"core_size": 2, "extended_size": 2, "openalex": {"concepts": [], "keywords": [], "venues": []}},
            },
            "sources": {
                "openalex": {"base_url": "https://api.openalex.org", "mailto": "", "per_page": 1, "max_pages": 1, "rate_limit_qps": 1},
                "s2": {"base_url": "https://api.semanticscholar.org/graph/v1", "api_key_env": "S2_API_KEY", "rate_limit_qps": 1},
                "opencitations": {"enable": False},
            },
            "selection": {
                "topic_coverage_k": 1,
                "centrality_weights": {"pagerank": 1.0, "indegree": 0.0},
                "backfill_pool_multiplier": 1.0,
                "backfill_batch_size": 8,
                "manual_decisions_file": "",
            },
            "fulltext": {
                "require_success": False,
                "policy": "none",
                "core": {"policy": "none", "require_success": False},
                "extended": {"policy": "none", "require_success": False},
            },
            "record_build": {
                "mode": "llm",
                "require_llm": False,
                "strict_paraphrase": False,
                "max_retries": 0,
                "prompt_version": "test",
            },
            "sdg": {"enable_l1": True, "enable_l2": True, "enable_l3": True},
            "qa": {"schema_pass_rate_required": 1.0, "consistency_pass_rate_required": 0.0, "edge_coverage_threshold": 0.0},
            "seeds": {"public_seeds": [1], "private_seeds": []},
        }

        cfg_path = out_root / "cfg.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

        dataset_version = load_dataset_config(cfg_path).dataset_version
        works_path = (
            out_root
            / dataset_version
            / "private"
            / "raw_snapshots"
            / "openalex"
            / "works_track_A.jsonl"
        )
        works_path.parent.mkdir(parents=True, exist_ok=True)

        works = [
            {
                "id": "https://openalex.org/W1",
                "title": "Paper One",
                "publication_year": 2020,
                "doi": None,
                "ids": {},
                "concepts": [{"id": "https://openalex.org/C1"}],
                "cited_by_count": 10,
                "referenced_works": [],
                "abstract_inverted_index": {"We": [0], "study": [1], "models": [2]},
            },
            {
                "id": "https://openalex.org/W2",
                "title": "Paper Two",
                "publication_year": 2021,
                "doi": None,
                "ids": {},
                "concepts": [{"id": "https://openalex.org/C2"}],
                "cited_by_count": 5,
                "referenced_works": ["https://openalex.org/W1"],
                "abstract_inverted_index": {"We": [0], "extend": [1], "methods": [2]},
            },
        ]
        works_path.write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in works) + "\n", encoding="utf-8")

        build_dataset(config_path=cfg_path, offline=True, out_root=out_root, track="A")

        pub = out_root / dataset_version / "public" / "track_A_extended_records.jsonl"
        line = pub.read_text(encoding="utf-8").splitlines()[0]
        rec = json.loads(line)

        snap = (rec.get("provenance") or {}).get("snapshot_refs") or {}
        openalex_sha = snap.get("openalex_work_sha256") or ""
        assert isinstance(openalex_sha, str) and len(openalex_sha) == 64

