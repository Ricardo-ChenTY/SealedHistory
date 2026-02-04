"""Dataset pipeline configuration loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DatasetConfig:
    raw: Dict[str, Any]
    path: Path

    @property
    def dataset_version(self) -> str:
        return str(self.raw.get("dataset_version", "0.0.0"))

    @property
    def export_root(self) -> Path:
        return Path(self.raw.get("export_root", "provetok/data/exports"))


def load_dataset_config(path: Optional[Path]) -> DatasetConfig:
    if path is None:
        path = Path("provetok/configs/dataset.yaml")

    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise ImportError("pyyaml is required: pip install pyyaml") from e

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return DatasetConfig(raw=raw, path=path)

