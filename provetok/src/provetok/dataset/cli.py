"""CLI wiring for the dataset pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path


def register_dataset_commands(subparsers: argparse._SubParsersAction) -> None:
    p_dataset = subparsers.add_parser("dataset", help="Dataset build pipeline (plan.md)")
    sub = p_dataset.add_subparsers(dest="dataset_cmd", required=True)

    p_build = sub.add_parser("build", help="Run full dataset build pipeline")
    p_build.add_argument("--config", default=None, help="Dataset YAML config path")
    p_build.add_argument("--offline", action="store_true", help="Use only cached snapshots")
    p_build.add_argument("--out", default=None, help="Override export root directory")
    p_build.add_argument("--track", choices=["A", "B", "both"], default="both")

    p_export_legacy = sub.add_parser(
        "export-legacy",
        help="Export legacy micro_history_*.jsonl into v2 public/private layout",
    )
    p_export_legacy.add_argument("--config", default=None)
    p_export_legacy.add_argument("--out", default=None)
    p_export_legacy.add_argument("--track", choices=["A", "B", "both"], default="A")


def handle_dataset_command(args: argparse.Namespace) -> None:
    from provetok.dataset.build import build_dataset, export_legacy_dataset

    if args.dataset_cmd == "build":
        build_dataset(
            config_path=Path(args.config) if args.config else None,
            offline=bool(args.offline),
            out_root=Path(args.out) if args.out else None,
            track=args.track,
        )
        return
    if args.dataset_cmd == "export-legacy":
        export_legacy_dataset(
            config_path=Path(args.config) if args.config else None,
            out_root=Path(args.out) if args.out else None,
            track=args.track,
        )
        return

    raise SystemExit(f"Unknown dataset_cmd: {args.dataset_cmd}")

