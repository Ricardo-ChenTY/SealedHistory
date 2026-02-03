"""Script: run benchmark simulation with an agent.

Usage:
    python scripts/run_benchmark.py \
        --sealed data/sealed/micro_history_a.sealed.jsonl \
        --raw data/raw/micro_history_a.jsonl \
        --agent llm \
        --output output/eval_report.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import load_records
from provetok.env.environment import BenchmarkEnvironment
from provetok.agents.base import LLMResearchAgent, RandomAgent, run_agent_loop
from provetok.eval.rubric import (
    AutoRubricScorer, RubricWeights, ParetoPoint, save_eval_report,
)
from provetok.utils.llm_client import LLMClient, LLMConfig


def main():
    parser = argparse.ArgumentParser(description="Run benchmark")
    parser.add_argument("--sealed", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--agent", choices=["llm", "random"], default="llm")
    parser.add_argument("--budget", type=int, default=30)
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--api_base", default="https://api.deepseek.com/v1")
    parser.add_argument("--audit_report", default=None)
    parser.add_argument("--output", default="output/eval_report.json")
    args = parser.parse_args()

    sealed = load_records(Path(args.sealed))
    raw = load_records(Path(args.raw))

    env = BenchmarkEnvironment(
        sealed_records=sealed,
        real_records=raw,
        budget=args.budget,
        fast_mode=True,
    )

    if args.agent == "random":
        agent = RandomAgent(seed=42)
    else:
        llm = LLMClient(LLMConfig(model=args.model, api_base=args.api_base))
        agent = LLMResearchAgent(llm)

    print(f"Running benchmark: agent={args.agent}, budget={args.budget}")
    results = run_agent_loop(agent, env)

    scorer = AutoRubricScorer()
    rubric_result = scorer.score_run(results, raw)

    audit_summary = {}
    if args.audit_report and Path(args.audit_report).exists():
        with open(args.audit_report) as f:
            audit_summary = json.load(f)

    leakage = audit_summary.get("_overall", {}).get("avg_leakage", 0.0)
    pareto_points = [
        ParetoPoint(config_name=args.agent, leakage=leakage, utility=rubric_result["total"])
    ]

    out = Path(args.output)
    save_eval_report(rubric_result, audit_summary, pareto_points, out)

    print(f"\nResults: utility={rubric_result['total']:.4f}, "
          f"accepted={rubric_result.get('n_accepted', 0)}/{rubric_result.get('n_proposals', 0)}")
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
