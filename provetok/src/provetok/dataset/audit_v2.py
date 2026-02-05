"""Leakage audit for v2 records (sealed worlds).

This is intentionally lightweight: it supports:
  - term recovery (requires private codebook mapping for evaluation)
  - order-bias proxy via coherence rating
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from provetok.data.schema_v2 import PaperRecordV2
from provetok.utils.llm_client import LLMClient


@dataclass
class AttackResult:
    attack_name: str
    success_rate: float
    n_trials: int
    details: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_name": self.attack_name,
            "success_rate": self.success_rate,
            "n_trials": self.n_trials,
            "details": self.details,
            "metadata": self.metadata,
        }


class TermRecoveryAttackV2:
    PROMPT_TEMPLATE = (
        "You are given an anonymised research snippet. The pseudotoken '{pseudo}' appears.\n\n"
        "Context:\n{context}\n\n"
        "Guess the original term behind '{pseudo}'. Return top-3 guesses as a JSON list of strings.\n"
        "Output ONLY the JSON list."
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        sealed_records: List[PaperRecordV2],
        codebook_reverse: Dict[str, str],
        *,
        n_samples: int = 20,
        seed: int = 42,
    ) -> AttackResult:
        rng = random.Random(seed)
        pseudos = list(codebook_reverse.keys())
        if not pseudos:
            return AttackResult("term_recovery_v2", 0.0, 0)

        candidates: List[Dict[str, str]] = []
        for r in sealed_records:
            ctx = r.background[:400]
            for pseudo in pseudos:
                if pseudo and pseudo in ctx:
                    candidates.append({"pseudo": pseudo, "real": codebook_reverse[pseudo], "context": ctx})

        if not candidates:
            return AttackResult("term_recovery_v2", 0.0, 0)

        rng.shuffle(candidates)
        trials = candidates[:n_samples]
        hits = 0
        details: List[Dict[str, Any]] = []

        for c in trials:
            prompt = self.PROMPT_TEMPLATE.format(pseudo=c["pseudo"], context=c["context"])
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=300)
            guesses = _parse_json_list(resp.content)
            real = str(c["real"]).lower().strip()
            hit = any(str(g).lower().strip() == real for g in guesses)
            hits += 1 if hit else 0
            details.append({"pseudo": c["pseudo"], "real": c["real"], "guesses": guesses, "hit": hit})

        return AttackResult(
            attack_name="term_recovery_v2",
            success_rate=hits / len(trials) if trials else 0.0,
            n_trials=len(trials),
            details=details,
        )


class OrderBiasTestV2:
    PROMPT_TEMPLATE = (
        "Below is a sequence of anonymised research records. Rate how coherent and logical it is on a scale of 1-10.\n"
        "Only output a single integer.\n\n{sequence}"
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, sealed_records: List[PaperRecordV2], *, n_shuffles: int = 5, seed: int = 42) -> AttackResult:
        rng = random.Random(seed)

        def fmt(rs: List[PaperRecordV2]) -> str:
            return "\n".join(f"{i+1}. [{r.paper_id}] {r.background[:120]}" for i, r in enumerate(rs))

        canonical = sorted(sealed_records, key=lambda r: r.paper_id)
        canonical_score = _get_score(self.llm, self.PROMPT_TEMPLATE.format(sequence=fmt(canonical)))

        shuffle_scores = []
        for _ in range(n_shuffles):
            rs = list(canonical)
            rng.shuffle(rs)
            shuffle_scores.append(_get_score(self.llm, self.PROMPT_TEMPLATE.format(sequence=fmt(rs))))

        avg_shuffle = sum(shuffle_scores) / len(shuffle_scores) if shuffle_scores else 0.0
        bias = canonical_score - avg_shuffle
        return AttackResult(
            attack_name="order_bias_v2",
            success_rate=max(0.0, bias / 10.0),
            n_trials=1 + n_shuffles,
            details=[{"canonical_score": canonical_score, "shuffle_scores": shuffle_scores, "bias": bias}],
            metadata={"interpretation": "bias > 0 means model prefers canonical order"},
        )


class TimeIndexPairwiseAttackV2:
    """Ask LLM to predict which record comes earlier (pairwise time-index)."""

    PROMPT_TEMPLATE = (
        "You are given two anonymised research records from a sealed domain.\n"
        "Which one likely appears EARLIER in the research timeline?\n"
        "Answer exactly one character: A or B.\n\n"
        "A: [{id_a}] {bg_a}\n\n"
        "B: [{id_b}] {bg_b}\n"
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    @staticmethod
    def _paper_index(paper_id: str) -> int:
        s = str(paper_id or "")
        parts = s.split("_", 1)
        if len(parts) != 2:
            return 0
        tail = parts[1]
        return int(tail) if tail.isdigit() else 0

    @staticmethod
    def _parse_choice(text: str) -> str:
        t = str(text or "").strip().upper()
        if t.startswith("A"):
            return "A"
        if t.startswith("B"):
            return "B"
        # Fallback: search for isolated A/B
        if re.search(r"\\bA\\b", t):
            return "A"
        if re.search(r"\\bB\\b", t):
            return "B"
        return "A"

    def run(self, sealed_records: List[PaperRecordV2], *, n_samples: int = 30, seed: int = 42) -> AttackResult:
        rng = random.Random(seed)
        if len(sealed_records) < 2:
            return AttackResult("time_index_pairwise_v2", 0.0, 0)

        trials = 0
        hits = 0
        details: List[Dict[str, Any]] = []

        records = list(sealed_records)
        for _ in range(n_samples):
            a, b = rng.sample(records, 2)
            prompt = self.PROMPT_TEMPLATE.format(
                id_a=a.paper_id,
                id_b=b.paper_id,
                bg_a=(a.background or "")[:220],
                bg_b=(b.background or "")[:220],
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=20)
            choice = self._parse_choice(resp.content)

            # Ground truth: smaller local paper_id index is earlier.
            idx_a = self._paper_index(a.paper_id)
            idx_b = self._paper_index(b.paper_id)
            gold = "A" if idx_a <= idx_b else "B"
            hit = choice == gold
            hits += 1 if hit else 0
            trials += 1
            details.append(
                {
                    "a": a.paper_id,
                    "b": b.paper_id,
                    "gold": gold,
                    "pred": choice,
                    "hit": hit,
                }
            )

        return AttackResult(
            attack_name="time_index_pairwise_v2",
            success_rate=hits / trials if trials else 0.0,
            n_trials=trials,
            details=details,
            metadata={"random_baseline": 0.5, "gold_rule": "min(paper_id_index) is earlier"},
        )


def summary(results: Dict[str, AttackResult]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    rates = []
    for k, v in results.items():
        out[k] = {"success_rate": round(v.success_rate, 4), "n_trials": v.n_trials, "metadata": v.metadata}
        rates.append(v.success_rate)
    avg = sum(rates) / len(rates) if rates else 0.0
    out["_overall"] = {"avg_leakage": round(avg, 4)}
    return out


def _parse_json_list(text: str) -> List[str]:
    return [str(text or "").strip()]


def _get_score(llm: LLMClient, prompt: str) -> float:
    resp = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=50)
    m = re.search(r"-?\d+(?:\.\d+)?", str(resp.content or ""))
    if not m:
        return 5.0
    return float(m.group(0))
