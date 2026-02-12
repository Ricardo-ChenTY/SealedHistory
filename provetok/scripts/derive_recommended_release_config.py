"""Derive a recommended defense configuration ("shipping decision") from a tradeoff curve.

Checklist-4
-----------
Top-conference papers need an explicit "what should I ship?" configuration. We
derive it deterministically from `runs/EXP-023/tradeoff_curve.json`.

Policy (simple + auditable, not overfit):
- Recommend the *lowest* defense `level` that achieves:
  - black-box leakage <= target_bb_leakage
  - utility retention >= min_utility_retention

Additionally report:
- the lowest `level` that achieves black-box leakage == 0 (if any).

No `try/except/finally` is used (forbidden under `provetok/`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _pick_recommended(
    levels: List[Dict[str, Any]],
    *,
    target_bb_leakage: float,
    min_utility_retention: float,
) -> Optional[Dict[str, Any]]:
    # Lowest level satisfying constraints.
    ok = []
    for lv in levels:
        o = lv.get("overall") or {}
        bb = float(o.get("black_box_leakage_avg") or 0.0)
        ur = float(o.get("utility_retention_vs_raw_avg") or 0.0)
        if bb <= float(target_bb_leakage) and ur >= float(min_utility_retention):
            ok.append(lv)
    ok.sort(key=lambda x: int(x.get("level") or 0))
    return ok[0] if ok else None


def _pick_zero_bb(levels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ok = []
    for lv in levels:
        o = lv.get("overall") or {}
        bb = float(o.get("black_box_leakage_avg") or 0.0)
        if bb <= 0.0:
            ok.append(lv)
    ok.sort(key=lambda x: int(x.get("level") or 0))
    return ok[0] if ok else None


def main() -> None:
    p = argparse.ArgumentParser(description="Derive recommended release defense level from EXP-023 tradeoff curve.")
    p.add_argument("--curve_json", default="runs/EXP-023/tradeoff_curve.json")
    p.add_argument("--out_dir", default="runs/EXP-033")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--target_bb_leakage", type=float, default=0.03)
    p.add_argument("--min_utility_retention", type=float, default=0.99)
    args = p.parse_args()

    curve_path = Path(args.curve_json)
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    levels = curve.get("levels") or []
    if not isinstance(levels, list) or not levels:
        raise ValueError(f"tradeoff curve has no levels: {curve_path}")

    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.overwrite:
        for name in ["recommended_config.json", "recommended_config.md", "run_meta.json", "run.log", "exit_code.txt"]:
            pth = out_dir / name
            if pth.exists():
                pth.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    rec = _pick_recommended(
        levels,
        target_bb_leakage=float(args.target_bb_leakage),
        min_utility_retention=float(args.min_utility_retention),
    )
    zero = _pick_zero_bb(levels)

    def _fmt_level(lv: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not lv:
            return None
        o = lv.get("overall") or {}
        return {
            "level": int(lv.get("level") or 0),
            "utility_retention_vs_raw_avg": float(o.get("utility_retention_vs_raw_avg") or 0.0),
            "black_box_leakage_avg": float(o.get("black_box_leakage_avg") or 0.0),
            "white_box_leakage_avg": float(o.get("white_box_leakage_avg") or 0.0),
        }

    elapsed = time.time() - t0
    meta = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "curve_json": str(curve_path),
        "curve_sha256": _sha256_file(curve_path),
        "policy": {
            "target_bb_leakage": float(args.target_bb_leakage),
            "min_utility_retention": float(args.min_utility_retention),
            "rule": "pick lowest level with bb_leakage<=target and utility_retention>=min",
        },
        "runtime": {"elapsed_sec": round(float(elapsed), 3), "python": sys.version.split()[0], "platform": platform.platform()},
        "git": {"commit": _git_head(), "dirty": bool(_git_dirty())},
    }

    out = {
        "meta": meta,
        "recommended": _fmt_level(rec),
        "black_box_zero_leakage": _fmt_level(zero),
    }

    (out_dir / "recommended_config.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "run.log").write_text("OK\n", encoding="utf-8")

    md = []
    md.append("# Recommended Release Config (from EXP-023 tradeoff curve)\n\n")
    md.append("Policy:\n")
    md.append(f"- target black-box leakage <= `{float(args.target_bb_leakage)}`\n")
    md.append(f"- min utility retention >= `{float(args.min_utility_retention)}`\n\n")
    md.append("Recommendation:\n")
    if out["recommended"]:
        r = out["recommended"]
        md.append(
            "- level={level} (utility_retention={ur:.4f}, black_box_leakage={bb:.4f}, white_box_leakage={wb:.4f})\n".format(
                level=r["level"], ur=r["utility_retention_vs_raw_avg"], bb=r["black_box_leakage_avg"], wb=r["white_box_leakage_avg"]
            )
        )
    else:
        md.append("- No level satisfies the policy thresholds.\n")
    if out["black_box_zero_leakage"]:
        z = out["black_box_zero_leakage"]
        md.append(
            "\nLowest level achieving black-box leakage=0:\n"
            "- level={level} (utility_retention={ur:.4f}, white_box_leakage={wb:.4f})\n".format(
                level=z["level"], ur=z["utility_retention_vs_raw_avg"], wb=z["white_box_leakage_avg"]
            )
        )
    md.append("\nArtifacts:\n- `runs/EXP-033/recommended_config.json`\n")
    (out_dir / "recommended_config.md").write_text("".join(md), encoding="utf-8")

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

