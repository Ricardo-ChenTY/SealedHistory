"""Unified CLI entry point for ProveTok / SealedHistory.

Usage:
    python -m provetok.cli seal   --in_jsonl ... --out_jsonl ... [--seed 42]
    python -m provetok.cli audit  --sealed ... --raw ... [--config ...]
    python -m provetok.cli run    --sealed ... --raw ... [--config ...]
    python -m provetok.cli all    --in_jsonl ... [--config ...]   # seal -> audit -> run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("provetok.cli")


def cmd_seal(args: argparse.Namespace) -> None:
    """Generate sealed dataset from raw micro-history."""
    from provetok.data.schema import load_records, save_records
    from provetok.sdg.sealer import SDGPipeline
    from provetok.utils.config import load_config

    cfg = load_config(Path(args.config) if args.config else None)
    seed = args.seed or cfg.seed

    logger.info("Loading raw records from %s", args.in_jsonl)
    records = load_records(Path(args.in_jsonl))
    logger.info("Loaded %d records", len(records))

    pipeline = SDGPipeline(
        seed=seed,
        enable_l1=cfg.sdg.enable_l1,
        enable_l2=cfg.sdg.enable_l2,
        enable_l3=cfg.sdg.enable_l3,
        numeric_bins=cfg.sdg.numeric_bins,
    )

    sealed = pipeline.seal_records(records)
    out_path = Path(args.out_jsonl)
    save_records(sealed, out_path)
    logger.info("Saved %d sealed records to %s", len(sealed), out_path)

    # Save codebook alongside
    cb_path = out_path.parent / (out_path.stem + ".codebook.json")
    pipeline.codebook.save(cb_path)
    logger.info("Saved codebook to %s", cb_path)


def cmd_audit(args: argparse.Namespace) -> None:
    """Run leakage audit on sealed dataset."""
    from provetok.data.schema import load_records
    from provetok.audit.attacks import AuditRunner
    from provetok.sdg.codebook import Codebook
    from provetok.utils.config import load_config
    from provetok.utils.llm_client import LLMClient, LLMConfig

    cfg = load_config(Path(args.config) if args.config else None)

    sealed = load_records(Path(args.sealed))
    raw = load_records(Path(args.raw))

    # Load codebook for reverse lookup
    cb_path = Path(args.codebook) if args.codebook else None
    if cb_path and cb_path.exists():
        codebook = Codebook.load(cb_path)
        reverse_map = codebook._reverse
    else:
        reverse_map = {}
        logger.warning("No codebook provided; term recovery attack will be limited")

    # Create LLM client
    llm_cfg = LLMConfig(
        model=cfg.llm.model,
        api_base=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
        temperature=0.0,
    )
    llm = LLMClient(llm_cfg)

    runner = AuditRunner(llm, seed=cfg.seed)
    audit_cfg = {
        "run_term_recovery": cfg.audit.run_term_recovery,
        "run_phase_pred": cfg.audit.run_phase_pred,
        "run_next_milestone": cfg.audit.run_next_milestone,
        "run_order_bias": cfg.audit.run_order_bias,
    }
    results = runner.run_all(sealed, raw, reverse_map, config=audit_cfg)
    summary = AuditRunner.summary(results)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info("Audit results saved to %s", out_path)

    # Print summary
    for name, info in summary.items():
        if name.startswith("_"):
            continue
        logger.info("  %s: success_rate=%.4f  (n=%d)",
                     name, info["success_rate"], info["n_trials"])
    overall = summary.get("_overall", {})
    logger.info("  OVERALL: avg_leakage=%.4f  pass=%s",
                 overall.get("avg_leakage", 0), overall.get("pass", False))


def cmd_run(args: argparse.Namespace) -> None:
    """Run benchmark simulation."""
    from provetok.data.schema import load_records
    from provetok.env.environment import BenchmarkEnvironment
    from provetok.agents.base import LLMResearchAgent, RandomAgent, run_agent_loop
    from provetok.eval.rubric import AutoRubricScorer, RubricWeights, ParetoPoint, save_eval_report
    from provetok.utils.config import load_config
    from provetok.utils.llm_client import LLMClient, LLMConfig

    cfg = load_config(Path(args.config) if args.config else None)

    sealed = load_records(Path(args.sealed))
    raw = load_records(Path(args.raw))

    env = BenchmarkEnvironment(
        sealed_records=sealed,
        real_records=raw,
        budget=cfg.env.budget,
        fast_mode=cfg.env.fast_mode,
    )

    # Create agent
    if args.agent == "random":
        agent = RandomAgent(seed=cfg.seed)
    else:
        llm_cfg = LLMConfig(
            model=cfg.llm.model,
            api_base=cfg.llm.api_base,
            api_key=cfg.llm.api_key,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
        )
        llm = LLMClient(llm_cfg)
        agent = LLMResearchAgent(llm)

    logger.info("Running benchmark with agent=%s, budget=%d", args.agent, cfg.env.budget)
    results = run_agent_loop(agent, env)

    # Score
    weights = RubricWeights(**cfg.eval.rubric_weights)
    scorer = AutoRubricScorer(weights)
    rubric_result = scorer.score_run(results, raw)

    # Load audit results if available
    audit_summary = {}
    if args.audit_report and Path(args.audit_report).exists():
        with open(args.audit_report, "r") as f:
            audit_summary = json.load(f)

    leakage = audit_summary.get("_overall", {}).get("avg_leakage", 0.0)
    pareto_points = [
        ParetoPoint(
            config_name=args.agent,
            leakage=leakage,
            utility=rubric_result["total"],
        )
    ]

    out_path = Path(args.output)
    save_eval_report(rubric_result, audit_summary, pareto_points, out_path)

    logger.info("Benchmark complete: utility=%.4f, accepted=%d/%d",
                 rubric_result["total"],
                 rubric_result.get("n_accepted", 0),
                 rubric_result.get("n_proposals", 0))
    logger.info("Full report: %s", out_path)

    # Print env state
    logger.info("Env state: %s", json.dumps(env.get_state_dict(), indent=2))


def cmd_all(args: argparse.Namespace) -> None:
    """Run full pipeline: seal -> audit -> run."""
    import tempfile
    from pathlib import Path

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sealed_path = out_dir / "sealed.jsonl"
    cb_path = out_dir / "sealed.codebook.json"
    audit_path = out_dir / "audit_report.json"
    run_path = out_dir / "eval_report.json"

    # Step 1: Seal
    logger.info("=== Step 1: Seal ===")
    seal_args = argparse.Namespace(
        in_jsonl=args.in_jsonl,
        out_jsonl=str(sealed_path),
        seed=args.seed,
        config=args.config,
    )
    cmd_seal(seal_args)

    # Step 2: Audit
    logger.info("=== Step 2: Audit ===")
    audit_args = argparse.Namespace(
        sealed=str(sealed_path),
        raw=args.in_jsonl,
        codebook=str(cb_path),
        config=args.config,
        output=str(audit_path),
    )
    cmd_audit(audit_args)

    # Step 3: Run
    logger.info("=== Step 3: Run benchmark ===")
    run_args = argparse.Namespace(
        sealed=str(sealed_path),
        raw=args.in_jsonl,
        config=args.config,
        agent=args.agent or "llm",
        audit_report=str(audit_path),
        output=str(run_path),
    )
    cmd_run(run_args)

    logger.info("=== Pipeline complete. Outputs in %s ===", out_dir)


def main():
    parser = argparse.ArgumentParser(
        prog="provetok",
        description="ProveTok / SealedHistory: anti-hindsight benchmark for research agents",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- seal ---
    p_seal = sub.add_parser("seal", help="Generate sealed dataset")
    p_seal.add_argument("--in_jsonl", required=True, help="Input raw JSONL path")
    p_seal.add_argument("--out_jsonl", required=True, help="Output sealed JSONL path")
    p_seal.add_argument("--seed", type=int, default=None)
    p_seal.add_argument("--config", default=None, help="YAML config path")

    # --- audit ---
    p_audit = sub.add_parser("audit", help="Run leakage audit")
    p_audit.add_argument("--sealed", required=True, help="Sealed JSONL path")
    p_audit.add_argument("--raw", required=True, help="Raw JSONL path")
    p_audit.add_argument("--codebook", default=None, help="Codebook JSON path")
    p_audit.add_argument("--config", default=None)
    p_audit.add_argument("--output", default="audit_report.json")

    # --- run ---
    p_run = sub.add_parser("run", help="Run benchmark simulation")
    p_run.add_argument("--sealed", required=True)
    p_run.add_argument("--raw", required=True)
    p_run.add_argument("--config", default=None)
    p_run.add_argument("--agent", choices=["llm", "random"], default="llm")
    p_run.add_argument("--audit_report", default=None)
    p_run.add_argument("--output", default="eval_report.json")

    # --- all ---
    p_all = sub.add_parser("all", help="Run full pipeline: seal -> audit -> run")
    p_all.add_argument("--in_jsonl", required=True)
    p_all.add_argument("--out_dir", default="output")
    p_all.add_argument("--seed", type=int, default=42)
    p_all.add_argument("--config", default=None)
    p_all.add_argument("--agent", choices=["llm", "random"], default="llm")

    args = parser.parse_args()

    if args.command == "seal":
        cmd_seal(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "all":
        cmd_all(args)


if __name__ == "__main__":
    main()
