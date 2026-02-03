"""Script: run leakage audit on sealed dataset.

Usage:
    python scripts/run_audit.py \
        --sealed data/sealed/micro_history_a.sealed.jsonl \
        --raw data/raw/micro_history_a.jsonl \
        --codebook data/sealed/micro_history_a.sealed.codebook.json \
        --output output/audit_report.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import load_records
from provetok.audit.attacks import AuditRunner
from provetok.sdg.codebook import Codebook
from provetok.utils.llm_client import LLMClient, LLMConfig


def main():
    parser = argparse.ArgumentParser(description="Run leakage audit")
    parser.add_argument("--sealed", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--codebook", default=None)
    parser.add_argument("--output", default="output/audit_report.json")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--api_base", default="https://api.deepseek.com/v1")
    args = parser.parse_args()

    sealed = load_records(Path(args.sealed))
    raw = load_records(Path(args.raw))

    reverse_map = {}
    if args.codebook and Path(args.codebook).exists():
        cb = Codebook.load(Path(args.codebook))
        reverse_map = cb._reverse

    llm = LLMClient(LLMConfig(
        model=args.model,
        api_base=args.api_base,
        temperature=0.0,
    ))

    runner = AuditRunner(llm, seed=42)
    results = runner.run_all(sealed, raw, reverse_map)
    summary = AuditRunner.summary(results)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nAudit summary saved to {out}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
