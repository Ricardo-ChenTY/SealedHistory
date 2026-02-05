"""Tests for v2 time-index / canonical-order attack."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema_v2 import PaperRecordV2
from provetok.dataset.audit_v2 import TimeIndexPairwiseAttackV2


class _Resp:
    def __init__(self, content: str):
        self.content = content


class _OracleLLM:
    """Picks the correct earlier record by parsing the prompt."""

    def chat(self, messages, temperature=0.0, max_tokens=20, **kwargs):  # noqa: ARG002
        prompt = messages[-1]["content"]
        m_a = re.search(r"A:\s*\[([^\]]+)\]", prompt)
        m_b = re.search(r"B:\s*\[([^\]]+)\]", prompt)
        ida = m_a.group(1) if m_a else ""
        idb = m_b.group(1) if m_b else ""

        def idx(pid: str) -> int:
            parts = str(pid or "").split("_", 1)
            if len(parts) != 2:
                return 0
            s = parts[1]
            return int(s) if s.isdigit() else 0

        choice = "A" if idx(ida) <= idx(idb) else "B"
        return _Resp(choice)


def test_time_index_pairwise_attack_oracle():
    records = [
        PaperRecordV2(paper_id="A_001", track_id="A", background="r1"),
        PaperRecordV2(paper_id="A_002", track_id="A", background="r2"),
        PaperRecordV2(paper_id="A_010", track_id="A", background="r3"),
    ]
    attack = TimeIndexPairwiseAttackV2(_OracleLLM())
    res = attack.run(records, n_samples=25, seed=123)
    assert res.n_trials == 25
    assert res.success_rate == 1.0
