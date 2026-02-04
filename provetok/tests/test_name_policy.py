"""Tests for optional name/identity fingerprint policy in public text."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.record_builder import RecordBuildError, build_record_v2_from_abstract


class _Resp:
    def __init__(self, content: str):
        self.content = content


class _StubLLM:
    def __init__(self, payload):
        self._payload = payload

    def chat(self, messages, temperature=0.0, max_tokens=1200, **kwargs):  # noqa: ARG002
        return _Resp(json.dumps(self._payload))


def _payload(background: str):
    return {
        "background": background,
        "mechanism_tags": ["other"],
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


def test_strict_background_allows_names_by_default():
    llm = _StubLLM(
        _payload(
            "As shown by Smith et al., this work improves optimization stability without leaking identifiers."
        )
    )
    rec = build_record_v2_from_abstract(
        paper_id="A_001",
        track_id="A",
        title="Example",
        abstract="We propose a method and evaluate it on benchmarks.",
        dependencies=[],
        llm=llm,
        strict_paraphrase=True,
        max_retries=0,
        forbid_names=False,
    )
    assert rec.public.background


def test_strict_background_can_forbid_name_fingerprints():
    llm = _StubLLM(
        _payload(
            "As shown by Smith et al., this work improves optimization stability without leaking identifiers."
        )
    )
    with pytest.raises(RecordBuildError) as ei:
        build_record_v2_from_abstract(
            paper_id="A_001",
            track_id="A",
            title="Example",
            abstract="We propose a method and evaluate it on benchmarks.",
            dependencies=[],
            llm=llm,
            strict_paraphrase=True,
            max_retries=0,
            forbid_names=True,
        )
    assert ei.value.code == "background_policy_fail"


def test_name_allowlist_can_suppress_false_positives():
    llm = _StubLLM(
        _payload(
            "As shown by Smith et al., this work improves optimization stability without leaking identifiers."
        )
    )
    rec = build_record_v2_from_abstract(
        paper_id="A_001",
        track_id="A",
        title="Example",
        abstract="We propose a method and evaluate it on benchmarks.",
        dependencies=[],
        llm=llm,
        strict_paraphrase=True,
        max_retries=0,
        forbid_names=True,
        name_allowlist=["smith"],
    )
    assert rec.public.background

