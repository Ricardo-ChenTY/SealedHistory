from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_cli_run_random_agent_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    sealed = repo_root / "provetok" / "data" / "sealed" / "micro_history_a.sealed.jsonl"
    raw = repo_root / "provetok" / "data" / "raw" / "micro_history_a.jsonl"
    assert sealed.exists()
    assert raw.exists()

    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "project: provetok",
                "seed: 42",
                "env:",
                "  budget: 3",
                "  fast_mode: true",
                "  multi_agent: false",
                "  n_agents: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "eval_report.json"
    cmd = [
        sys.executable,
        "-m",
        "provetok.cli",
        "run",
        "--agent",
        "random",
        "--config",
        str(cfg_path),
        "--sealed",
        str(sealed),
        "--raw",
        str(raw),
        "--output",
        str(out_path),
    ]

    subprocess.run(
        cmd,
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert out_path.exists()
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(report.keys()) >= {"rubric", "audit", "pareto"}
    assert "total" in (report.get("rubric") or {})

