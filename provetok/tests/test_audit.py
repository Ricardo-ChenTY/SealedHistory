"""Tests for Leakage Audit Suite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import load_records
from provetok.sdg.sealer import SDGPipeline
from provetok.audit.attacks import (
    AuditRunner, TermRecoveryAttack, PhasePredictionAttack,
    NextMilestoneAttack, OrderBiasTest,
)
from provetok.utils.llm_client import LLMClient, LLMConfig


def _get_test_data():
    data_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "micro_history_a.jsonl"
    records = load_records(data_path)
    pipeline = SDGPipeline(seed=42)
    sealed = pipeline.seal_records(records)
    return records, sealed, pipeline.codebook


def test_audit_runner_dummy():
    """Test audit runner with dummy LLM (no API key)."""
    raw, sealed, codebook = _get_test_data()

    llm = LLMClient(LLMConfig())  # dummy mode
    runner = AuditRunner(llm, seed=42)
    results = runner.run_all(sealed, raw, codebook._reverse)

    assert "term_recovery" in results
    assert "phase_prediction" in results
    assert "next_milestone" in results
    assert "order_bias" in results

    summary = AuditRunner.summary(results)
    assert "_overall" in summary
    assert "avg_leakage" in summary["_overall"]
    print("Audit summary:", summary)


if __name__ == "__main__":
    test_audit_runner_dummy()
    print("PASS: test_audit_runner_dummy")
    print("\nAll audit tests passed!")
