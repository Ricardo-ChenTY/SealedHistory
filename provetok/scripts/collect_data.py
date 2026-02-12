"""S2-first data collection entrypoint (legacy wrapper).

This script replaces the historical milestone collector and now delegates to
the unified dataset pipeline (`provetok dataset build` / `build_dataset`).

Examples:
  python scripts/collect_data.py --track both --out runs/exports_real
  python scripts/collect_data.py --track a --offline --out runs/exports_offline
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.build import build_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("collect_data")


def _normalize_track(track: str) -> str:
    t = str(track).strip().lower()
    if t in ("a", "track_a"):
        return "A"
    if t in ("b", "track_b"):
        return "B"
    return "both"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run S2-first dataset collection/build pipeline.")
    parser.add_argument("--config", default="provetok/configs/dataset.yaml", help="Dataset YAML config path")
    parser.add_argument("--track", choices=["a", "b", "both", "A", "B"], default="both", help="Track scope")
    parser.add_argument("--out", "--output", dest="out", default=None, help="Export root directory")
    parser.add_argument("--offline", action="store_true", help="Use cached snapshots only")
    args = parser.parse_args()

    track = _normalize_track(args.track)
    out_root = Path(args.out) if args.out else None

    logger.info("collect_data now delegates to dataset build (S2-first).")
    logger.info("config=%s track=%s offline=%s out=%s", args.config, track, bool(args.offline), str(out_root or "default"))

    build_dataset(
        config_path=Path(args.config) if args.config else None,
        offline=bool(args.offline),
        out_root=out_root,
        track=track,
    )

    logger.info("Done.")


if __name__ == "__main__":
    main()

