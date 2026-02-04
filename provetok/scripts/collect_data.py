"""Script: collect micro-history data from Semantic Scholar + LLM extraction.

Usage:
    # Collect Track A (vision)
    python scripts/collect_data.py --track a --output data/raw/micro_history_a.jsonl

    # Collect Track B (sequence modeling)
    python scripts/collect_data.py --track b --output data/raw/micro_history_b.jsonl

    # Collect both tracks
    python scripts/collect_data.py --track both --output data/raw/

    # Validate existing data
    python scripts/collect_data.py --validate data/raw/micro_history_a.jsonl

Environment variables:
    LLM_API_KEY    - API key for DeepSeek/OpenAI (required for LLM extraction)
    LLM_API_BASE   - API base URL (default: https://api.deepseek.com/v1)
    S2_API_KEY     - Semantic Scholar API key (optional, higher rate limits)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.collector import (
    TRACK_A_MILESTONES,
    TRACK_B_MILESTONES,
    collect_track,
    validate_records,
)
from provetok.data.schema import load_records
from provetok.utils.llm_client import LLMClient, LLMConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("collect_data")


def main():
    parser = argparse.ArgumentParser(description="Collect micro-history data")
    parser.add_argument("--track", choices=["a", "b", "both"], default="a",
                        help="Which track to collect")
    parser.add_argument("--output", required=True,
                        help="Output JSONL path (or directory if --track both)")
    parser.add_argument("--model", default="deepseek-chat",
                        help="LLM model for extraction")
    parser.add_argument("--api_base", default=None,
                        help="LLM API base URL")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between Semantic Scholar API calls (seconds)")
    parser.add_argument("--validate", default=None,
                        help="Validate an existing JSONL file instead of collecting")
    args = parser.parse_args()

    # Validate mode
    if args.validate:
        records = load_records(Path(args.validate))
        issues = validate_records(records)
        if issues:
            print(f"\n{len(issues)} issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\nAll {len(records)} records passed validation.")
        return

    # Collection mode
    llm_config = LLMConfig(model=args.model)
    if args.api_base:
        llm_config.api_base = args.api_base
    llm = LLMClient(llm_config)

    import os
    s2_key = os.environ.get("S2_API_KEY")

    if args.track in ("a", "both"):
        out_a = Path(args.output)
        if args.track == "both":
            out_a = Path(args.output) / "micro_history_a.jsonl"
        logger.info("=== Collecting Track A: Vision Representation (%d papers) ===",
                     len(TRACK_A_MILESTONES))
        records_a = collect_track(
            TRACK_A_MILESTONES, llm, out_a, s2_api_key=s2_key, delay=args.delay
        )
        issues_a = validate_records(records_a)
        if issues_a:
            logger.warning("Track A: %d validation issues", len(issues_a))

    if args.track in ("b", "both"):
        out_b = Path(args.output)
        if args.track == "both":
            out_b = Path(args.output) / "micro_history_b.jsonl"
        logger.info("=== Collecting Track B: Sequence Modeling (%d papers) ===",
                     len(TRACK_B_MILESTONES))
        records_b = collect_track(
            TRACK_B_MILESTONES, llm, out_b, s2_api_key=s2_key, delay=args.delay
        )
        issues_b = validate_records(records_b)
        if issues_b:
            logger.warning("Track B: %d validation issues", len(issues_b))

    logger.info("Done. Remember to review and manually fix [TODO] entries.")


if __name__ == "__main__":
    main()
