"""Benchmark environment for sealed-domain research simulation.

Implements the minimal read -> propose -> experiment -> review loop described
in `ProveTok_SealedHistory_Proposal.md` and used by `provetok.cli run`.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from provetok.data.schema import PaperRecord
from provetok.eval.rubric import AutoRubricScorer, RubricWeights

logger = logging.getLogger(__name__)


@dataclass
class Proposal:
    title: str
    background: str
    mechanism: str
    experiment_plan: str
    predicted_improvement: float = 0.0
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "background": self.background,
            "mechanism": self.mechanism,
            "experiment_plan": self.experiment_plan,
            "predicted_improvement": self.predicted_improvement,
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Proposal":
        return cls(
            title=str(d.get("title") or ""),
            background=str(d.get("background") or ""),
            mechanism=str(d.get("mechanism") or ""),
            experiment_plan=str(d.get("experiment_plan") or d.get("experiment") or ""),
            predicted_improvement=float(d.get("predicted_improvement") or 0.0),
            dependencies=[str(x) for x in (d.get("dependencies") or []) if str(x).strip()],
        )


@dataclass
class ExperimentFeedback:
    success: bool
    delta_vs_baseline: float = 0.0
    ablation_results: Dict[str, float] = field(default_factory=dict)
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": bool(self.success),
            "delta_vs_baseline": float(self.delta_vs_baseline),
            "ablation_results": dict(self.ablation_results),
            "notes": dict(self.notes),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperimentFeedback":
        return cls(
            success=bool(d.get("success", False)),
            delta_vs_baseline=float(d.get("delta_vs_baseline") or 0.0),
            ablation_results={str(k): float(v) for k, v in (d.get("ablation_results") or {}).items()},
            notes=dict(d.get("notes") or {}),
        )


@dataclass
class ReviewResult:
    accepted: bool
    scores: Dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    threshold: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": bool(self.accepted),
            "scores": {k: float(v) for k, v in (self.scores or {}).items()},
            "total": float(self.total),
            "threshold": float(self.threshold),
        }


@dataclass
class EnvState:
    budget_total: int
    budget_used: int = 0
    step: int = 0
    n_accepted: int = 0
    n_rejected: int = 0


class BenchmarkEnvironment:
    """Fast-mode benchmark environment.

    - `sealed_records` are what the agent can observe.
    - `real_records` are used to generate deterministic experiment feedback and
      to score proposals during review.
    """

    def __init__(
        self,
        *,
        sealed_records: List[PaperRecord],
        real_records: List[PaperRecord],
        budget: int = 30,
        fast_mode: bool = True,
        accept_threshold: float = 0.50,
        seed: int = 42,  # reserved for future stochastic env behaviors
        rubric_weights: Optional[RubricWeights] = None,
    ):
        self.sealed_records = list(sealed_records)
        self.real_records = list(real_records)
        self.fast_mode = bool(fast_mode)
        self.accept_threshold = float(accept_threshold)
        self.seed = int(seed)

        self._sealed_by_id = {r.paper_id: r for r in self.sealed_records}
        self._scorer = AutoRubricScorer(weights=rubric_weights or RubricWeights())

        self.state = EnvState(budget_total=int(budget), budget_used=0, step=0)
        # Allow the final review even when budget hits the limit.
        self._pending_review: bool = False

    @property
    def done(self) -> bool:
        if self.state.step >= len(self.real_records):
            return True
        if self.state.step >= len(self.sealed_records):
            return True
        if self.state.budget_used >= self.state.budget_total and not self._pending_review:
            return True
        return False

    def reset(self) -> None:
        self.state.budget_used = 0
        self.state.step = 0
        self.state.n_accepted = 0
        self.state.n_rejected = 0
        self._pending_review = False

    def available_papers(self) -> List[str]:
        """Return the list of sealed papers currently accessible."""
        if self.done:
            return []
        idx = min(len(self.sealed_records), self.state.step + 1)
        return [r.paper_id for r in self.sealed_records[:idx] if r.paper_id]

    def read(self, paper_id: str) -> Optional[PaperRecord]:
        """Read one sealed record (if accessible)."""
        if self.done:
            return None
        pid = str(paper_id or "")
        if not pid:
            return None
        if pid not in set(self.available_papers()):
            return None
        rec = self._sealed_by_id.get(pid)
        return copy.deepcopy(rec) if rec is not None else None

    def experiment(self, proposal: Proposal) -> ExperimentFeedback:
        """Run an experiment (fast-mode: deterministic feedback from the next real milestone)."""
        if self.done:
            return ExperimentFeedback(success=False, notes={"reason": "done"})

        if self.state.budget_used >= self.state.budget_total:
            # No experiments left.
            return ExperimentFeedback(success=False, notes={"reason": "budget_exhausted"})

        self.state.budget_used += 1
        self._pending_review = True

        target = self._target_record()
        if target is None:
            return ExperimentFeedback(success=False, notes={"reason": "no_target"})

        # Deterministic feedback: use the next real record's delta and extras.
        delta = float(getattr(target.results, "delta_vs_prev", 0.0) or 0.0)
        delta = max(-1.0, min(1.0, delta))

        extra = getattr(target.results, "extra", {}) or {}
        ablations: Dict[str, float] = {}
        if isinstance(extra, dict):
            for k, v in extra.items():
                try:
                    ablations[str(k)] = float(v)
                except Exception:
                    continue

        return ExperimentFeedback(
            success=True,
            delta_vs_baseline=delta,
            ablation_results=ablations,
            notes={
                "target_paper_id": target.paper_id,
                "target_phase": target.phase,
                "target_metric_main": float(getattr(target.results, "metric_main", 0.0) or 0.0),
                "fast_mode": bool(self.fast_mode),
            },
        )

    def review(self, proposal: Proposal, feedback: ExperimentFeedback) -> ReviewResult:
        """Review a proposal against the next real milestone using the rubric scorer."""
        target = self._target_record()

        if target is None:
            self._pending_review = False
            return ReviewResult(
                accepted=False,
                scores={},
                total=0.0,
                threshold=self.accept_threshold,
            )

        rub = self._scorer.score_proposal(
            proposal.to_dict() if proposal is not None else {},
            feedback.to_dict() if feedback is not None else {},
            target=target,
        )
        total = float(rub.weighted_total(self._scorer.weights))
        accepted = bool(total >= self.accept_threshold)

        if accepted:
            self.state.step += 1
            self.state.n_accepted += 1
        else:
            self.state.n_rejected += 1

        self._pending_review = False

        scores = rub.to_dict()
        scores["total"] = round(total, 4)
        return ReviewResult(
            accepted=accepted,
            scores=scores,
            total=round(total, 4),
            threshold=float(self.accept_threshold),
        )

    def get_state_dict(self) -> Dict[str, Any]:
        return {
            "step": int(self.state.step),
            "budget_used": int(self.state.budget_used),
            "budget_total": int(self.state.budget_total),
            "n_accepted": int(self.state.n_accepted),
            "n_rejected": int(self.state.n_rejected),
            "done": bool(self.done),
            "pending_review": bool(self._pending_review),
        }

    def _target_record(self) -> Optional[PaperRecord]:
        if self.state.step < 0 or self.state.step >= len(self.real_records):
            return None
        return self.real_records[self.state.step]

