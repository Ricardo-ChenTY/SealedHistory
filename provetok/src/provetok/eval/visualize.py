"""Visualization utilities for eval results.

Generates Pareto front plots and rubric radar charts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def plot_pareto(report_path: Path, output_path: Path) -> None:
    """Plot Leakage-Utility Pareto front from an eval report JSON."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    pareto = report.get("pareto", [])
    if not pareto:
        print("No pareto data in report")
        return

    configs = [p["config"] for p in pareto]
    leakages = [p["leakage"] for p in pareto]
    utilities = [p["utility"] for p in pareto]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(leakages, utilities, s=100, zorder=5)
    for i, cfg in enumerate(configs):
        ax.annotate(cfg, (leakages[i], utilities[i]),
                     textcoords="offset points", xytext=(8, 8))

    # Draw Pareto front line
    front = sorted(zip(leakages, utilities), key=lambda x: x[0])
    best_u = -1
    front_pts = []
    for l, u in front:
        if u > best_u:
            front_pts.append((l, u))
            best_u = u
    if len(front_pts) > 1:
        ax.plot([p[0] for p in front_pts], [p[1] for p in front_pts],
                "r--", alpha=0.6, label="Pareto front")

    ax.set_xlabel("Leakage (attack success rate)")
    ax.set_ylabel("Utility (rubric score)")
    ax.set_title("Leakage-Utility Pareto Curve")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Pareto plot to {output_path}")


def plot_rubric_radar(report_path: Path, output_path: Path) -> None:
    """Plot rubric dimension radar chart."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib/numpy not installed; skipping plot")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    dims = report.get("rubric", {}).get("per_dimension_avg", {})
    if not dims:
        print("No rubric dimension data")
        return

    labels = list(dims.keys())
    values = list(dims.values())
    n = len(labels)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, alpha=0.25)
    ax.plot(angles, values, "o-", linewidth=2)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 1)
    ax.set_title("Rubric Dimension Scores")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved rubric radar to {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m provetok.eval.visualize <report.json>")
        sys.exit(1)
    rp = Path(sys.argv[1])
    plot_pareto(rp, rp.parent / "pareto.png")
    plot_rubric_radar(rp, rp.parent / "rubric_radar.png")
