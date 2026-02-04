"""Export an audit/attack-suite stub into the dataset public directory."""

from __future__ import annotations

from pathlib import Path

from provetok.dataset.paths import DatasetPaths


def export_attack_suite(paths: DatasetPaths) -> None:
    out_dir = paths.public_dir / "attack_suite"
    out_dir.mkdir(parents=True, exist_ok=True)

    readme = out_dir / "README.md"
    root = paths.root.as_posix()
    readme.write_text(
        "\n".join(
            [
                "# Attack Suite (SealedHistory)",
                "",
                "This folder documents leakage-audit commands for sealed worlds.",
                "",
                "## Term Recovery (v2 records)",
                "",
                "Run (requires a real LLM endpoint and the *private* codebook mapping):",
                "",
                "```bash",
                "# Build dataset first (legacy or online)",
                "provetok dataset build --config provetok/configs/dataset.yaml",
                "",
                "# Then run v2 audit against a public sealed world, using the private codebook",
                "python3 provetok/scripts/run_audit_v2.py \\",
                f"  --sealed_jsonl {root}/public/sealed_worlds/42/extended/records.jsonl \\",
                f"  --codebook_json {root}/private/mapping_key/seed_42.codebook.json \\",
                f"  --output {root}/public/attack_suite/audit_report_seed42.json",
                "```",
                "",
                "## Notes",
                "- Public releases should NOT include the private codebook mapping.",
                "- The v2 audit script is best-effort and intended as a starting point.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
