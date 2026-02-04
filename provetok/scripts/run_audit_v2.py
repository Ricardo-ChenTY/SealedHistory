"""Script: run leakage audit on v2 sealed-world records.

Usage:
  python3 provetok/scripts/run_audit_v2.py \
    --sealed_jsonl provetok/data/exports/{dataset_version}/public/sealed_worlds/42/extended/records.jsonl \
    --codebook_json provetok/data/exports/{dataset_version}/private/mapping_key/seed_42.codebook.json \
    --output provetok/data/exports/{dataset_version}/public/attack_suite/audit_report_seed42.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema_v2 import load_records_v2
from provetok.dataset.audit_v2 import OrderBiasTestV2, TermRecoveryAttackV2, summary
from provetok.sdg.codebook import Codebook
from provetok.utils.llm_client import LLMClient, LLMConfig


def main() -> None:
    p = argparse.ArgumentParser(description="Run v2 leakage audit")
    p.add_argument("--sealed_jsonl", required=True)
    p.add_argument("--codebook_json", required=True, help="PRIVATE codebook mapping (do not publish)")
    p.add_argument("--output", required=True)
    p.add_argument("--model", default="deepseek-chat")
    p.add_argument("--api_base", default="https://api.deepseek.com/v1")
    p.add_argument("--n_samples", type=int, default=20)
    args = p.parse_args()

    records = load_records_v2(Path(args.sealed_jsonl))
    cb = Codebook.load(Path(args.codebook_json))
    reverse_map = cb._reverse

    llm = LLMClient(LLMConfig(model=args.model, api_base=args.api_base, temperature=0.0))

    results = {}
    results["term_recovery_v2"] = TermRecoveryAttackV2(llm).run(records, reverse_map, n_samples=args.n_samples)
    results["order_bias_v2"] = OrderBiasTestV2(llm).run(records)

    out = summary(results)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps(out, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
