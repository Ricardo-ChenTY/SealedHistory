"""Script: build sealed dataset from raw micro-history.

Usage:
    python scripts/build_sealed_dataset.py \
        --in_jsonl data/raw/micro_history_a.jsonl \
        --out_jsonl data/sealed/micro_history_a.sealed.jsonl \
        --seed 42
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import load_records, save_records
from provetok.sdg.sealer import SDGPipeline


def main():
    parser = argparse.ArgumentParser(description="Build sealed dataset")
    parser.add_argument("--in_jsonl", required=True)
    parser.add_argument("--out_jsonl", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--l1", action="store_true", default=True)
    parser.add_argument("--no-l2", action="store_true")
    parser.add_argument("--no-l3", action="store_true")
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()

    records = load_records(Path(args.in_jsonl))
    print(f"Loaded {len(records)} records")

    pipeline = SDGPipeline(
        seed=args.seed,
        enable_l1=args.l1,
        enable_l2=not args.no_l2,
        enable_l3=not args.no_l3,
        numeric_bins=args.bins,
    )

    sealed = pipeline.seal_records(records)
    out = Path(args.out_jsonl)
    save_records(sealed, out)
    print(f"Saved {len(sealed)} sealed records to {out}")

    # Save codebook
    cb_path = out.parent / (out.stem + ".codebook.json")
    pipeline.codebook.save(cb_path)
    print(f"Codebook saved to {cb_path}")

    # Preview first record
    print("\n--- Preview (first sealed record) ---")
    print(sealed[0].to_json()[:500])


if __name__ == "__main__":
    main()
