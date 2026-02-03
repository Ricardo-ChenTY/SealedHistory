"""PaperRecord schema and data loading utilities.

Follows MLE-bench pattern: structured metadata + standardised I/O,
but adapted for micro-history research simulation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExperimentResult:
    """Quantitative results of a paper."""
    metric_main: float
    delta_vs_prev: float
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass
class PaperRecord:
    """Minimal structured representation of one milestone paper.

    Fields align with Proposal §5.1.
    """
    paper_id: str
    title: str
    phase: str                        # "early" | "mid" | "late" (or int bucket)
    background: str                   # problem & limitations
    mechanism: str                    # core mechanism (may include pseudo-formulas)
    experiment: str                   # experiment setup, metrics, ablations
    results: ExperimentResult
    dependencies: List[str]           # list of prerequisite paper_ids
    keywords: List[str]               # terms used for lexical sealing

    # --- optional enrichment fields ---
    year: Optional[int] = None
    venue: Optional[str] = None
    authors: Optional[List[str]] = None

    # ---- serialisation ----
    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "PaperRecord":
        res = d.get("results", {})
        if isinstance(res, dict):
            d["results"] = ExperimentResult(
                metric_main=res.get("metric_main", 0.0),
                delta_vs_prev=res.get("delta_vs_prev", 0.0),
                extra=res.get("extra", {}),
            )
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, line: str) -> "PaperRecord":
        return cls.from_dict(json.loads(line))


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_records(path: Path) -> List[PaperRecord]:
    """Load a JSONL file of PaperRecords."""
    records: List[PaperRecord] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PaperRecord.from_json(line))
    return records


def save_records(records: List[PaperRecord], path: Path) -> None:
    """Save PaperRecords to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.to_json() + "\n")


def build_dependency_graph(records: List[PaperRecord]) -> Dict[str, List[str]]:
    """Return adjacency list: paper_id -> list of papers that depend on it."""
    graph: Dict[str, List[str]] = {r.paper_id: [] for r in records}
    for r in records:
        for dep in r.dependencies:
            if dep in graph:
                graph[dep].append(r.paper_id)
    return graph
