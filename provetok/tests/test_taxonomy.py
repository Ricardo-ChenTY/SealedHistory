"""Tests for taxonomy + tag normalization (v2 records)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.legacy import default_taxonomy
from provetok.dataset.record_builder import build_record_v2_from_abstract


class _Resp:
    def __init__(self, content: str):
        self.content = content


class _StubLLM:
    def __init__(self, payload):
        self._payload = payload

    def chat(self, messages, temperature=0.0, max_tokens=1200, **kwargs):  # noqa: ARG002
        return _Resp(json.dumps(self._payload))


def test_default_taxonomy_nontrivial():
    tax = default_taxonomy()
    mech = tax.get("mechanism_tags") or {}
    assert isinstance(mech, dict)
    assert "other" in mech
    assert len(mech) >= 8
    assert any(isinstance(v, dict) and v.get("aliases") for v in mech.values())


def test_record_builder_normalizes_tags_to_taxonomy():
    tax = default_taxonomy()

    llm = _StubLLM(
        {
            "background": "This work proposes a new mechanism and evaluates it.",
            "mechanism_tags": ["Attention", "cnn", "WeirdTag"],
            "keywords": ["token"],
            "protocol": {
                "task_family_id": "unknown_task",
                "dataset_id": "unknown_dataset",
                "metric_id": "unknown_metric",
                "compute_class": "unknown_compute",
                "train_regime_class": "unknown_regime",
            },
            "results": {"delta_over_baseline_bucket": 1},
        }
    )

    rec = build_record_v2_from_abstract(
        paper_id="A_001",
        track_id="A",
        title="Example Paper",
        abstract="We study a model with attention. CNN baselines are strong.",
        dependencies=[],
        llm=llm,
        strict_paraphrase=False,
        taxonomy=tax,
    )

    allowed = set((tax.get("mechanism_tags") or {}).keys())
    assert set(rec.public.mechanism_tags).issubset(allowed)
    assert "attention" in rec.public.mechanism_tags
    assert "convolution" in rec.public.mechanism_tags
    assert "other" in rec.public.mechanism_tags

