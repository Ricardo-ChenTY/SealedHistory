"""Plot budget attack curves into a slide/paper-ready PNG.

Checklist-5 support
-------------------
Budget curves are a key "failure-first" artifact. This script turns the JSON
curves into a 2-panel plot (black-box vs white-box).

No `try/except/finally` is used (forbidden under `provetok/`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _series(curve: List[Dict[str, Any]]) -> Tuple[List[float], List[float]]:
    xs = [float(p.get("budget") or 0) for p in curve]
    ys = [float(p.get("top1") or 0.0) for p in curve]
    return xs, ys


def main() -> None:
    p = argparse.ArgumentParser(description="Plot budget_curves.json to budget_curves.png")
    p.add_argument("--in_json", required=True)
    p.add_argument("--out_png", default="")
    p.add_argument("--title", default="")
    args = p.parse_args()

    in_path = Path(args.in_json)
    obj = json.loads(in_path.read_text(encoding="utf-8"))

    curves = obj.get("curves") or {}
    if not isinstance(curves, dict) or not curves:
        raise ValueError(f"No curves in JSON: {in_path}")

    out_png = Path(args.out_png) if str(args.out_png or "").strip() else in_path.with_suffix(".png")
    out_png.parent.mkdir(parents=True, exist_ok=True)

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=160)
    ax_bb, ax_wb = axes[0], axes[1]

    # Stable ordering for legend.
    keys = sorted(curves.keys())

    styles = {
        "A_sealed": {"color": "#1f77b4", "marker": "o"},
        "B_sealed": {"color": "#ff7f0e", "marker": "o"},
        "A_defended": {"color": "#2ca02c", "marker": "s"},
        "B_defended": {"color": "#d62728", "marker": "s"},
    }

    for k in keys:
        v = curves.get(k) or {}
        bb = v.get("black_box") or []
        wb = v.get("white_box") or []
        if not bb or not wb:
            continue
        xs_bb, ys_bb = _series(bb)
        xs_wb, ys_wb = _series(wb)
        st = styles.get(k, {"color": None, "marker": "o"})
        ax_bb.plot(xs_bb, ys_bb, label=k, color=st.get("color"), marker=st.get("marker"))
        ax_wb.plot(xs_wb, ys_wb, label=k, color=st.get("color"), marker=st.get("marker"))

    for ax, title in [(ax_bb, "Black-box"), (ax_wb, "White-box")]:
        ax.set_title(title)
        ax.set_xlabel("Budget")
        ax.set_ylabel("Top-1 success")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)

    # Budgets are powers of two; log scale makes shape clearer.
    ax_bb.set_xscale("log", base=2)
    ax_wb.set_xscale("log", base=2)

    # One shared legend (avoid duplicated legends per subplot).
    handles, labels = ax_bb.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)

    ttl = str(args.title or "").strip()
    if not ttl:
        ttl = f"Budget Attack Curves ({in_path.parent.name})"
    fig.suptitle(ttl, y=1.02)

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    print(f"Saved: {out_png}")


if __name__ == "__main__":
    main()

