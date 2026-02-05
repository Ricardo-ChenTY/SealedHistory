"""Research agent interface and LLM-backed implementation.

Agents interact with the BenchmarkEnvironment through a standard loop:
  observe -> think -> act -> observe feedback -> repeat
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from provetok.data.schema import PaperRecord
from provetok.env.environment import (
    BenchmarkEnvironment,
    ExperimentFeedback,
    Proposal,
    ReviewResult,
)
from provetok.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract research agent."""

    @abstractmethod
    def act(self, env: BenchmarkEnvironment) -> Dict[str, Any]:
        """Perform one action cycle and return a summary."""
        ...


class LLMResearchAgent(BaseAgent):
    """Single research agent backed by an LLM (DeepSeek / OpenAI-compatible).

    Follows a three-phase cycle:
      1. Read available papers to gather context
      2. Propose the next research step
      3. Run experiment and submit for review
    """

    SYSTEM_PROMPT = (
        "You are a research scientist working in a sealed domain. "
        "You can only reason based on the papers provided to you. "
        "You must NOT use any prior knowledge about real-world research. "
        "Your goal is to propose the next logical research breakthrough "
        "based on the evidence available."
    )

    PROPOSE_PROMPT = (
        "Based on the papers you have read, propose the next research paper.\n\n"
        "Papers you have read:\n{papers_context}\n\n"
        "Requirements:\n"
        "- Identify a clear limitation in existing work\n"
        "- Propose a novel mechanism to address it\n"
        "- Specify which papers your work depends on\n"
        "- Describe the experiment you would run\n\n"
        "Output your proposal as JSON with these fields:\n"
        "{{\"title\": \"...\", \"background\": \"...\", \"mechanism\": \"...\", "
        "\"experiment_plan\": \"...\", \"predicted_improvement\": 0.05, "
        "\"dependencies\": [\"paper_id_1\", ...], \"keywords\": [\"kw1\", ...]}}"
    )

    def __init__(self, llm: LLMClient, agent_id: str = "agent_0"):
        self.llm = llm
        self.agent_id = agent_id
        self._read_papers: Dict[str, PaperRecord] = {}
        self._conversation: List[Dict[str, str]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]

    def act(self, env: BenchmarkEnvironment) -> Dict[str, Any]:
        """Execute one full research cycle: read -> propose -> experiment -> review."""

        # Phase 1: Read available papers we haven't read yet
        available = env.available_papers()
        new_papers = [pid for pid in available if pid not in self._read_papers]

        for pid in new_papers:
            record = env.read(pid)
            if record:
                self._read_papers[pid] = record
            if env.done:
                break

        if env.done:
            return {"status": "budget_exhausted", "phase": "read"}

        # Phase 2: Propose
        proposal = self._generate_proposal(env)
        if proposal is None:
            return {"status": "proposal_failed"}

        if env.done:
            return {"status": "budget_exhausted", "phase": "propose"}

        # Phase 3: Experiment
        feedback = env.experiment(proposal)

        if env.done:
            return {"status": "budget_exhausted", "phase": "experiment"}

        # Phase 4: Review
        review = env.review(proposal, feedback)

        return {
            "status": "completed",
            "proposal": proposal.to_dict(),
            "feedback": feedback.to_dict(),
            "accepted": review.accepted,
            "scores": review.scores,
        }

    def _generate_proposal(self, env: BenchmarkEnvironment) -> Optional[Proposal]:
        """Use LLM to generate a research proposal based on read papers."""
        if not self._read_papers:
            return None

        papers_context = "\n\n".join(
            f"[{pid}] {rec.title}\n"
            f"  Background: {rec.background[:200]}\n"
            f"  Mechanism: {rec.mechanism[:200]}\n"
            f"  Dependencies: {rec.dependencies}"
            for pid, rec in self._read_papers.items()
        )

        prompt = self.PROPOSE_PROMPT.format(papers_context=papers_context)
        self._conversation.append({"role": "user", "content": prompt})

        resp = self.llm.chat(self._conversation, temperature=0.7)
        self._conversation.append({"role": "assistant", "content": resp.content})

        return self._parse_proposal(resp.content)

    @staticmethod
    def _parse_proposal(text: str) -> Optional[Proposal]:
        """Convert LLM output into a Proposal without structured parsing.

        This repository forbids in-code exception handling; if structured JSON
        parsing is desired, it must be enforced upstream by making the model
        output deterministically valid JSON.
        """
        raw = str(text or "").strip()

        # Handle markdown code blocks (best-effort, deterministic string ops only).
        if "```" in raw:
            first = raw.find("```")
            second = raw.find("```", first + 3)
            if second > first:
                block = raw[first + 3 : second]
                block_l = block.lstrip()
                if block_l.startswith("json"):
                    block = block_l[4:]
                raw = block.strip()

        if not raw:
            return None

        return Proposal(
            title="LLM Proposal",
            background="Auto-generated from unstructured LLM output",
            mechanism=raw[:300],
            experiment_plan="Standard evaluation on benchmark",
            predicted_improvement=0.01,
            dependencies=[],
        )


class RandomAgent(BaseAgent):
    """Baseline agent that makes random proposals (lower bound)."""

    def __init__(self, seed: int = 42):
        import random
        self._rng = random.Random(seed)

    def act(self, env: BenchmarkEnvironment) -> Dict[str, Any]:
        available = env.available_papers()
        if not available:
            return {"status": "no_papers"}

        # Read a random paper
        pid = self._rng.choice(available)
        record = env.read(pid)
        if env.done or record is None:
            return {"status": "budget_exhausted"}

        # Random proposal
        proposal = Proposal(
            title=f"Random proposal {env.state.step}",
            background="Randomly generated",
            mechanism="Apply random transformation to features",
            experiment_plan="Run on standard benchmark",
            predicted_improvement=self._rng.uniform(0.01, 0.1),
            dependencies=[pid],
        )

        feedback = env.experiment(proposal)
        if env.done:
            return {"status": "budget_exhausted"}

        review = env.review(proposal, feedback)
        return {
            "status": "completed",
            "accepted": review.accepted,
        }


# ======================================================================
# Runner
# ======================================================================

def run_agent_loop(
    agent: BaseAgent,
    env: BenchmarkEnvironment,
    max_cycles: int = 50,
) -> List[Dict[str, Any]]:
    """Run the agent in the environment until budget is exhausted."""
    env.reset()
    results = []
    cycle = 0

    while not env.done and cycle < max_cycles:
        result = agent.act(env)
        results.append(result)
        cycle += 1
        logger.info(
            "Cycle %d: status=%s, budget=%d/%d",
            cycle, result.get("status"),
            env.state.budget_used, env.state.budget_total,
        )

    return results
