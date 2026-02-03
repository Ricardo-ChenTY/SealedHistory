"""Leakage Audit Suite – attack-based tests.

Four tests (Proposal §5.3):
  1. Term Recovery Attack – can the LLM recover real terms from sealed text?
  2. Phase Prediction Attack – can it guess early/mid/late phase?
  3. Next Milestone Attack – can it predict the next breakthrough without evidence?
  4. Canonical Order Likelihood Test – does it show bias toward real ordering?
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from provetok.data.schema import PaperRecord
from provetok.utils.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class AttackResult:
    """Result of a single audit attack."""
    attack_name: str
    success_rate: float                 # 0-1
    n_trials: int
    details: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "attack_name": self.attack_name,
            "success_rate": self.success_rate,
            "n_trials": self.n_trials,
            "details": self.details,
            "metadata": self.metadata,
        }


# ======================================================================
# 1. Term Recovery Attack
# ======================================================================

class TermRecoveryAttack:
    """Ask LLM to guess the original term behind a pseudotoken."""

    PROMPT_TEMPLATE = (
        "You are given a sealed (anonymised) research paper snippet. "
        "The following pseudotoken appears in the text: '{pseudo_term}'.\n\n"
        "Context:\n{context}\n\n"
        "Try to guess the original real-world term that '{pseudo_term}' "
        "refers to. Provide your top-3 guesses as a JSON list of strings.\n"
        "Output ONLY the JSON list, e.g. [\"guess1\", \"guess2\", \"guess3\"]."
    )

    def __init__(self, llm: LLMClient, top_k: int = 3):
        self.llm = llm
        self.top_k = top_k

    def run(
        self,
        sealed_records: List[PaperRecord],
        codebook_reverse: Dict[str, str],
        n_samples: int = 10,
        seed: int = 42,
    ) -> AttackResult:
        rng = random.Random(seed)

        # Collect (pseudo_term, real_term, context) triples
        candidates = []
        for rec in sealed_records:
            for kw in rec.keywords:
                real = codebook_reverse.get(kw)
                if real:
                    candidates.append((kw, real, rec.mechanism[:300]))

        if not candidates:
            return AttackResult("term_recovery", 0.0, 0)

        rng.shuffle(candidates)
        trials = candidates[:n_samples]

        successes = 0
        details = []
        for pseudo, real, ctx in trials:
            prompt = self.PROMPT_TEMPLATE.format(
                pseudo_term=pseudo, context=ctx
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
            guesses = self._parse_guesses(resp.content)
            hit = any(g.lower().strip() == real.lower().strip() for g in guesses)
            if hit:
                successes += 1
            details.append({
                "pseudo": pseudo,
                "real": real,
                "guesses": guesses,
                "hit": hit,
            })

        return AttackResult(
            attack_name="term_recovery",
            success_rate=successes / len(trials) if trials else 0.0,
            n_trials=len(trials),
            details=details,
        )

    @staticmethod
    def _parse_guesses(text: str) -> List[str]:
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return [str(g) for g in parsed[:5]]
        except json.JSONDecodeError:
            pass
        return [text.strip()]


# ======================================================================
# 2. Phase Prediction Attack
# ======================================================================

class PhasePredictionAttack:
    """Ask LLM to guess whether a sealed paper is from early/mid/late phase."""

    PROMPT_TEMPLATE = (
        "You are given an anonymised research paper record from a sealed domain.\n\n"
        "Title: {title}\n"
        "Background: {background}\n"
        "Mechanism: {mechanism}\n\n"
        "Based on the content, guess the paper's phase in the research timeline.\n"
        "Answer exactly one of: early, mid, late"
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        sealed_records: List[PaperRecord],
        real_records: List[PaperRecord],
        n_samples: int = 10,
        seed: int = 42,
    ) -> AttackResult:
        rng = random.Random(seed)
        pairs = list(zip(sealed_records, real_records))
        rng.shuffle(pairs)
        trials = pairs[:n_samples]

        successes = 0
        details = []
        # Random baseline: 1/3
        for sealed, real in trials:
            prompt = self.PROMPT_TEMPLATE.format(
                title=sealed.title,
                background=sealed.background,
                mechanism=sealed.mechanism[:300],
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
            pred = resp.content.strip().lower()
            hit = pred == real.phase.lower()
            if hit:
                successes += 1
            details.append({
                "paper_id": real.paper_id,
                "real_phase": real.phase,
                "predicted": pred,
                "hit": hit,
            })

        return AttackResult(
            attack_name="phase_prediction",
            success_rate=successes / len(trials) if trials else 0.0,
            n_trials=len(trials),
            details=details,
            metadata={"random_baseline": 1 / 3},
        )


# ======================================================================
# 3. Next Milestone Attack
# ======================================================================

class NextMilestoneAttack:
    """Given sealed papers up to step t, can LLM predict step t+1 without evidence?"""

    PROMPT_TEMPLATE = (
        "You are given a sequence of anonymised research papers in a sealed domain.\n"
        "The papers represent a progression of ideas. Here are the papers so far:\n\n"
        "{history}\n\n"
        "Predict what the NEXT paper in this sequence would be about. "
        "Describe the key mechanism in 2-3 sentences."
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        sealed_records: List[PaperRecord],
        real_records: List[PaperRecord],
        n_samples: int = 5,
        seed: int = 42,
    ) -> AttackResult:
        rng = random.Random(seed)
        # Try prediction at different cutoff points
        n = len(sealed_records)
        if n < 3:
            return AttackResult("next_milestone", 0.0, 0)

        cutoffs = sorted(rng.sample(range(2, n), min(n_samples, n - 2)))
        details = []

        for cutoff in cutoffs:
            history_text = "\n".join(
                f"- [{r.title}]: {r.mechanism[:150]}"
                for r in sealed_records[:cutoff]
            )
            prompt = self.PROMPT_TEMPLATE.format(history=history_text)

            resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
            prediction = resp.content.strip()

            # Compare with real next paper's mechanism (semantic similarity would be ideal,
            # for now use keyword overlap as proxy)
            real_next = real_records[cutoff]
            overlap = self._keyword_overlap(prediction, real_next.mechanism)

            details.append({
                "cutoff": cutoff,
                "real_next_id": real_next.paper_id,
                "prediction_preview": prediction[:200],
                "keyword_overlap": overlap,
            })

        avg_overlap = sum(d["keyword_overlap"] for d in details) / len(details) if details else 0
        return AttackResult(
            attack_name="next_milestone",
            success_rate=avg_overlap,
            n_trials=len(details),
            details=details,
            metadata={"metric": "keyword_overlap_ratio"},
        )

    @staticmethod
    def _keyword_overlap(text_a: str, text_b: str) -> float:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_b)


# ======================================================================
# 4. Canonical Order Likelihood Test
# ======================================================================

class OrderBiasTest:
    """Test whether LLM shows preference for canonical ordering vs shuffled.

    Measure: perplexity / log-likelihood difference between canonical and shuffled
    presentation of paper sequences.
    """

    PROMPT_TEMPLATE = (
        "Below is a sequence of anonymised research papers. "
        "Rate how logical and coherent this sequence is on a scale of 1-10.\n"
        "Only output a single integer.\n\n"
        "{sequence}"
    )

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        sealed_records: List[PaperRecord],
        n_shuffles: int = 5,
        seed: int = 42,
    ) -> AttackResult:
        rng = random.Random(seed)

        def _format_seq(records: List[PaperRecord]) -> str:
            return "\n".join(
                f"{i+1}. [{r.title}] {r.background[:100]}"
                for i, r in enumerate(records)
            )

        # Score canonical order
        canonical_text = _format_seq(sealed_records)
        canonical_score = self._get_score(canonical_text)

        # Score shuffled orders
        shuffle_scores = []
        for _ in range(n_shuffles):
            shuffled = list(sealed_records)
            rng.shuffle(shuffled)
            shuffle_text = _format_seq(shuffled)
            shuffle_scores.append(self._get_score(shuffle_text))

        avg_shuffle = sum(shuffle_scores) / len(shuffle_scores) if shuffle_scores else 0
        bias = canonical_score - avg_shuffle  # positive = model prefers canonical

        return AttackResult(
            attack_name="order_bias",
            success_rate=max(0, bias / 10),  # normalise to 0-1
            n_trials=1 + n_shuffles,
            details=[{
                "canonical_score": canonical_score,
                "shuffle_scores": shuffle_scores,
                "bias": bias,
            }],
            metadata={"interpretation": "bias > 0 means model prefers canonical order"},
        )

    def _get_score(self, sequence_text: str) -> float:
        prompt = self.PROMPT_TEMPLATE.format(sequence=sequence_text)
        resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.0)
        try:
            return float(resp.content.strip())
        except ValueError:
            # try to extract first number
            import re
            nums = re.findall(r"\d+", resp.content)
            return float(nums[0]) if nums else 5.0


# ======================================================================
# Audit Runner
# ======================================================================

class AuditRunner:
    """Run all audit attacks and produce a summary report."""

    def __init__(self, llm: LLMClient, seed: int = 42):
        self.llm = llm
        self.seed = seed

    def run_all(
        self,
        sealed_records: List[PaperRecord],
        real_records: List[PaperRecord],
        codebook_reverse: Dict[str, str],
        config: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, AttackResult]:
        cfg = config or {}
        results: Dict[str, AttackResult] = {}

        if cfg.get("run_term_recovery", True):
            logger.info("Running term recovery attack...")
            atk = TermRecoveryAttack(self.llm)
            results["term_recovery"] = atk.run(
                sealed_records, codebook_reverse, seed=self.seed
            )

        if cfg.get("run_phase_pred", True):
            logger.info("Running phase prediction attack...")
            atk = PhasePredictionAttack(self.llm)
            results["phase_prediction"] = atk.run(
                sealed_records, real_records, seed=self.seed
            )

        if cfg.get("run_next_milestone", True):
            logger.info("Running next milestone attack...")
            atk = NextMilestoneAttack(self.llm)
            results["next_milestone"] = atk.run(
                sealed_records, real_records, seed=self.seed
            )

        if cfg.get("run_order_bias", True):
            logger.info("Running order bias test...")
            atk = OrderBiasTest(self.llm)
            results["order_bias"] = atk.run(sealed_records, seed=self.seed)

        return results

    @staticmethod
    def summary(results: Dict[str, AttackResult]) -> Dict[str, Any]:
        """Produce a summary dict suitable for JSON output / reporting."""
        summary = {}
        for name, res in results.items():
            summary[name] = {
                "success_rate": round(res.success_rate, 4),
                "n_trials": res.n_trials,
                "metadata": res.metadata,
            }

        # Overall pass/fail
        all_rates = [r.success_rate for r in results.values()]
        avg_leakage = sum(all_rates) / len(all_rates) if all_rates else 0
        summary["_overall"] = {
            "avg_leakage": round(avg_leakage, 4),
            "pass": avg_leakage < 0.4,  # threshold: better than random + margin
        }
        return summary
