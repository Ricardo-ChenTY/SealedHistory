"""PaperRecord v2 schema (plan.md-aligned).

This schema is used for dataset publishing (public) and internal bookkeeping
(private). It intentionally does not replace the original `PaperRecord` to keep
backwards compatibility with existing demos/tests.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FormulaGraph:
    """Lightweight formula / mechanism graph."""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    ops: List[str] = field(default_factory=list)


@dataclass
class Protocol:
    task_family_id: str = "unknown_task"
    dataset_id: str = "unknown_dataset"
    metric_id: str = "unknown_metric"
    compute_class: str = "unknown_compute"          # e.g. small/medium/large
    train_regime_class: str = "unknown_regime"      # e.g. small/medium/large


@dataclass
class Results:
    primary_metric_rank: int = 0
    delta_over_baseline_bucket: int = 0
    ablation_delta_buckets: List[int] = field(default_factory=list)
    significance_flag: Optional[bool] = None


@dataclass
class PaperRecordV2:
    """Public record (safe to publish)."""

    paper_id: str
    track_id: str
    dependencies: List[str] = field(default_factory=list)

    background: str = ""
    mechanism_tags: List[str] = field(default_factory=list)
    formula_graph: FormulaGraph = field(default_factory=FormulaGraph)
    protocol: Protocol = field(default_factory=Protocol)
    results: Results = field(default_factory=Results)

    provenance: Dict[str, Any] = field(default_factory=dict)
    qa: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PaperRecordV2":
        fg = d.get("formula_graph") or {}
        proto = d.get("protocol") or {}
        res = d.get("results") or {}
        return cls(
            paper_id=str(d.get("paper_id", "")),
            track_id=str(d.get("track_id", "")),
            dependencies=list(d.get("dependencies") or []),
            background=str(d.get("background", "")),
            mechanism_tags=list(d.get("mechanism_tags") or []),
            formula_graph=FormulaGraph(**{k: v for k, v in fg.items() if k in FormulaGraph.__dataclass_fields__}),
            protocol=Protocol(**{k: v for k, v in proto.items() if k in Protocol.__dataclass_fields__}),
            results=Results(**{k: v for k, v in res.items() if k in Results.__dataclass_fields__}),
            provenance=dict(d.get("provenance") or {}),
            qa=dict(d.get("qa") or {}),
        )

    @classmethod
    def from_json(cls, line: str) -> "PaperRecordV2":
        return cls.from_dict(json.loads(line))


@dataclass
class PaperRecordInternalV2:
    """Internal record (not for public release)."""

    public: PaperRecordV2

    # Identifiers / mapping keys
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    openalex_id: Optional[str] = None
    s2_id: Optional[str] = None

    # Discovery + storage
    landing_page_url: Optional[str] = None
    retrieved_at_unix: Optional[int] = None
    pdf_sha256: Optional[str] = None
    source_paths: List[str] = field(default_factory=list)

    # Legacy compatibility / debugging (kept internal)
    title: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Flatten `public` for readability in JSONL
        pub = d.pop("public")
        return {"public": pub, **d}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PaperRecordInternalV2":
        pub = PaperRecordV2.from_dict(d.get("public") or {})
        rest = {k: v for k, v in d.items() if k != "public" and k in cls.__dataclass_fields__}
        return cls(public=pub, **rest)

    @classmethod
    def from_json(cls, line: str) -> "PaperRecordInternalV2":
        return cls.from_dict(json.loads(line))


def load_records_v2(path: Path) -> List[PaperRecordV2]:
    records: List[PaperRecordV2] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PaperRecordV2.from_json(line))
    return records


def save_records_v2(records: List[PaperRecordV2], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.to_json() + "\n")


def load_records_internal_v2(path: Path) -> List[PaperRecordInternalV2]:
    records: List[PaperRecordInternalV2] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PaperRecordInternalV2.from_json(line))
    return records


def save_records_internal_v2(records: List[PaperRecordInternalV2], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.to_json() + "\n")

