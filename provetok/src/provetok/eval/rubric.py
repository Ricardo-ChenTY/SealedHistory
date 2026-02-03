"""Rubric-based evaluation and Pareto front analysis.

Proposal §7: six scoring dimensions + Leakage-Utility Pareto curve.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from provetok.data.schema import PaperRecord

logger = logging.getLogger(__name__)


# ======================================================================
# Rubric dimensions
# ======================================================================

@dataclass
class RubricWeights:
    problem_shift: float = 1.0
    mechanism_class: float = 1.0
    dependency: float = 1.0
    claim_validity: float = 2.0
    ablation: float = 1.0
    clarity: float = 0.5

    def total_weight(self) -> float:
        return (
            self.problem_shift + self.mechanism_class + self.dependency
            + self.claim_validity + self.ablation + self.clarity
        )


@dataclass
class RubricScore:
    """Per-proposal rubric breakdown."""
    problem_shift: float = 0.0       # 0-1: is the problem framing reasonable?
    mechanism_class: float = 0.0     # 0-1: does mechanism match expected class?
    dependency: float = 0.0          # 0-1: dependency precision/recall
    claim_validity: float = 0.0      # 0-1: claims consistent with experiment?
    ablation: float = 0.0            # 0-1: ablation included & interpreted?
    clarity: float = 0.0             # 0-1: structure & readability

    def weighted_total(self, weights: RubricWeights) -> float:
        raw = (
            self.problem_shift * weights.problem_shift
            + self.mechanism_class * weights.mechanism_class
            + self.dependency * weights.dependency
            + self.claim_validity * weights.claim_validity
            + self.ablation * weights.ablation
            + self.clarity * weights.clarity
        )
        return raw / weights.total_weight()

    def to_dict(self) -> dict:
        return {
            "problem_shift": round(self.problem_shift, 4),
            "mechanism_class": round(self.mechanism_class, 4),
            "dependency": round(self.dependency, 4),
            "claim_validity": round(self.claim_validity, 4),
            "ablation": round(self.ablation, 4),
            "clarity": round(self.clarity, 4),
        }


# ======================================================================
# Scorer (automatic, MVP)
# ======================================================================

class AutoRubricScorer:
    """Automated rubric scorer for MVP.

    Uses heuristic + optional LLM-judge for clarity.
    """

    def __init__(self, weights: Optional[RubricWeights] = None):
        self.weights = weights or RubricWeights()

    def score_proposal(
        self,
        proposal: Dict[str, Any],
        feedback: Dict[str, Any],
        target: Optional[PaperRecord] = None,
    ) -> RubricScore:
        """Score a single accepted proposal against the target milestone."""
        score = RubricScore()

        # 1. Problem shift: does background mention a limitation?
        bg = proposal.get("background", "")
        score.problem_shift = min(1.0, len(bg) / 100)  # basic length proxy

        # 2. Mechanism class: keyword overlap with target
        if target:
            prop_words = set(proposal.get("mechanism", "").lower().split())
            target_words = set(target.mechanism.lower().split())
            overlap = len(prop_words & target_words)
            score.mechanism_class = min(1.0, overlap / max(len(target_words), 1))
        else:
            score.mechanism_class = 0.5 if proposal.get("mechanism") else 0.0

        # 3. Dependency accuracy
        if target:
            prop_deps = set(proposal.get("dependencies", []))
            real_deps = set(target.dependencies)
            if real_deps:
                precision = len(prop_deps & real_deps) / max(len(prop_deps), 1)
                recall = len(prop_deps & real_deps) / len(real_deps)
                score.dependency = 2 * precision * recall / max(precision + recall, 1e-9)
            else:
                score.dependency = 1.0 if not prop_deps else 0.5
        else:
            score.dependency = 0.5

        # 4. Claim validity: do claims match experiment feedback?
        if feedback.get("success"):
            # Check if predicted improvement direction matches actual
            predicted = proposal.get("predicted_improvement", 0)
            actual = feedback.get("delta_vs_baseline", 0)
            if predicted > 0 and actual > 0:
                score.claim_validity = 1.0
            elif predicted <= 0 and actual <= 0:
                score.claim_validity = 0.8
            else:
                score.claim_validity = 0.2
        else:
            score.claim_validity = 0.0

        # 5. Ablation discipline
        ablation = feedback.get("ablation_results", {})
        score.ablation = min(1.0, len(ablation) / 2)  # at least 2 ablation entries

        # 6. Clarity (length + structure proxy)
        mech_len = len(proposal.get("mechanism", ""))
        has_plan = bool(proposal.get("experiment_plan"))
        score.clarity = min(1.0, (mech_len / 200 + (1.0 if has_plan else 0.0)) / 2)

        return score

    def score_run(
        self,
        run_results: List[Dict[str, Any]],
        real_records: List[PaperRecord],
    ) -> Dict[str, Any]:
        """Score an entire benchmark run."""
        scores = []
        milestone_idx = 0

        for result in run_results:
            if result.get("status") != "completed":
                continue

            proposal = result.get("proposal", {})
            feedback = result.get("feedback", {})
            target = real_records[milestone_idx] if milestone_idx < len(real_records) else None

            score = self.score_proposal(proposal, feedback, target)
            scores.append(score)

            if result.get("accepted"):
                milestone_idx += 1

        if not scores:
            return {"total": 0.0, "n_proposals": 0, "breakdown": []}

        avg_total = sum(
            s.weighted_total(self.weights) for s in scores
        ) / len(scores)

        return {
            "total": round(avg_total, 4),
            "n_proposals": len(scores),
            "n_accepted": milestone_idx,
            "breakdown": [s.to_dict() for s in scores],
            "per_dimension_avg": {
                "problem_shift": round(sum(s.problem_shift for s in scores) / len(scores), 4),
                "mechanism_class": round(sum(s.mechanism_class for s in scores) / len(scores), 4),
                "dependency": round(sum(s.dependency for s in scores) / len(scores), 4),
                "claim_validity": round(sum(s.claim_validity for s in scores) / len(scores), 4),
                "ablation": round(sum(s.ablation for s in scores) / len(scores), 4),
                "clarity": round(sum(s.clarity for s in scores) / len(scores), 4),
            },
        }


# ======================================================================
# Pareto front computation
# ======================================================================

@dataclass
class ParetoPoint:
    """One point on the Leakage-Utility Pareto curve."""
    config_name: str           # e.g. "unsealed", "L1", "L1+L2+L3"
    leakage: float             # avg attack success rate (0-1)
    utility: float             # rubric total score (0-1)
    details: Dict[str, Any] = field(default_factory=dict)


def compute_pareto_front(points: List[ParetoPoint]) -> List[ParetoPoint]:
    """Extract Pareto-optimal points (minimise leakage, maximise utility)."""
    # Sort by leakage ascending
    sorted_pts = sorted(points, key=lambda p: p.leakage)
    front = []
    best_utility = -1.0

    for pt in sorted_pts:
        if pt.utility > best_utility:
            front.append(pt)
            best_utility = pt.utility

    return front


def save_eval_report(
    rubric_result: Dict[str, Any],
    audit_summary: Dict[str, Any],
    pareto_points: List[ParetoPoint],
    output_path: Path,
) -> None:
    """Save full evaluation report as JSON."""
    report = {
        "rubric": rubric_result,
        "audit": audit_summary,
        "pareto": [
            {"config": p.config_name, "leakage": p.leakage, "utility": p.utility}
            for p in pareto_points
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("Saved eval report to %s", output_path)
