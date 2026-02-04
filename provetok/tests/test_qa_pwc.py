"""Tests for optional Papers-with-Code (PWC) QA cross-check."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema_v2 import PaperRecordInternalV2, PaperRecordV2, Protocol, Results, save_records_internal_v2, save_records_v2
from provetok.dataset.paths import DatasetPaths
from provetok.dataset.qa import run_qa


def test_run_qa_emits_pwc_hint_warnings():
    with tempfile.TemporaryDirectory() as td:
        out_root = Path(td)
        paths = DatasetPaths(export_root=out_root, dataset_version="pwc-test")
        paths.ensure_dirs()

        pub = PaperRecordV2(
            paper_id="A_001",
            track_id="A",
            dependencies=[],
            background="b",
            mechanism_tags=["other"],
            protocol=Protocol(task_family_id="unknown_task", dataset_id="unknown_dataset", metric_id="unknown_metric"),
            results=Results(primary_metric_rank=1, delta_over_baseline_bucket=0),
            provenance={},
            qa={},
        )
        save_records_v2([pub], paths.public_records_path("A", "extended"))

        internal = PaperRecordInternalV2(public=pub, doi="https://doi.org/10.1000/xyz")
        save_records_internal_v2([internal], paths.private_records_path("A", "extended"))

        pwc_path = out_root / "pwc.jsonl"
        pwc_path.write_text(
            json.dumps({"doi": "10.1000/xyz", "datasets": ["ImageNet"], "metrics": ["accuracy"], "tasks": ["image classification"]})
            + "\n",
            encoding="utf-8",
        )

        cfg = {"sources": {"pwc_dump": {"enable": True, "dump_path": str(pwc_path)}}}
        run_qa(paths=paths, track="A", tier="extended", cfg=cfg)

        qa_path = paths.public_qa_report_path("extended")
        row = json.loads(qa_path.read_text(encoding="utf-8").splitlines()[0])
        codes = {i["code"] for i in row.get("issues") or []}
        assert "pwc_task_hint_available" in codes
        assert "pwc_dataset_hint_available" in codes
        assert "pwc_metric_hint_available" in codes

