"""Standard output paths for dataset exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetPaths:
    export_root: Path
    dataset_version: str

    @property
    def root(self) -> Path:
        return self.export_root / self.dataset_version

    @property
    def public_dir(self) -> Path:
        return self.root / "public"

    @property
    def private_dir(self) -> Path:
        return self.root / "private"

    def ensure_dirs(self) -> None:
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.private_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Tiered artifact helpers
    def public_records_path(self, track_id: str, tier: str) -> Path:
        return self.public_dir / f"track_{track_id}_{tier}_records.jsonl"

    def private_records_path(self, track_id: str, tier: str) -> Path:
        return self.private_dir / f"track_{track_id}_{tier}_records.internal.jsonl"

    def public_selection_log_path(self, tier: str) -> Path:
        return self.public_dir / f"selection_log_{tier}.jsonl"

    def public_dependency_graph_path(self, tier: str) -> Path:
        return self.public_dir / f"dependency_graph_{tier}.edgelist"

    def public_qa_report_path(self, tier: str) -> Path:
        return self.public_dir / f"qa_report_{tier}.jsonl"

    def private_fulltext_index_path(self, tier: str) -> Path:
        return self.private_dir / f"fulltext_index_{tier}.jsonl"

    def private_mapping_path(self, track_id: str, tier: str) -> Path:
        return self.private_dir / "mapping_key" / f"paper_id_map_track_{track_id}_{tier}.jsonl"

    def private_track_papers_path(self, track_id: str) -> Path:
        """Private per-track paper list (pre-record generation)."""
        return self.private_dir / f"track_{track_id}_papers.jsonl"
