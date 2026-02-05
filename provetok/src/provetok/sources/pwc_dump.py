"""Papers With Code (PWC) dump ingestion (best-effort).

The plan.md pipeline uses PWC dumps as an *auxiliary* cross-check signal. This
module intentionally supports a very flexible input schema: JSONL/JSON and
their gzipped variants. The caller is expected to provide a local dump path.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


def normalize_doi(doi: str) -> str:
    s = str(doi or "").strip()
    if not s:
        return ""
    low = s.lower()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if low.startswith(prefix):
            s = s[len(prefix) :]
            break
    if s.lower().startswith("doi:"):
        s = s[4:]
    return s.strip().lower()


def _open_text(path: Path):
    if path.suffix.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with _open_text(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            if isinstance(v, dict):
                yield v


def _iter_json(path: Path) -> Iterator[Dict[str, Any]]:
    with _open_text(path) as f:
        v = json.load(f)
    if isinstance(v, list):
        for item in v:
            if isinstance(item, dict):
                yield item
    elif isinstance(v, dict):
        # Common pattern: {"data": [...]} or {"papers": [...]}
        for key in ("data", "papers", "items"):
            items = v.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        yield item
                return


def _extract_doi(obj: Dict[str, Any]) -> str:
    for k in ("doi", "DOI", "paper_doi", "paperDOI"):
        if obj.get(k):
            return normalize_doi(str(obj.get(k)))

    # Try to parse DOI from URLs
    for k in ("paper_url", "url", "paperUrl"):
        u = str(obj.get(k) or "")
        m = re.search(r"doi\\.org/([^\\s?#]+)", u, flags=re.IGNORECASE)
        if m:
            return normalize_doi(m.group(1))

    return ""


def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        return [v] if v.strip() else []
    return []


def _merge_sets(dst: Dict[str, set], *, key: str, values: Iterable[str]) -> None:
    if key not in dst:
        dst[key] = set()
    for x in values:
        s = str(x).strip()
        if s:
            dst[key].add(s)


def load_pwc_dump(path: Path, *, limit: Optional[int] = None) -> Dict[str, Dict[str, set]]:
    """Load a (local) PWC dump file and return hints keyed by normalized DOI.

    Output mapping:
      doi -> {"tasks": set[str], "datasets": set[str], "metrics": set[str]}
    """
    if not path.exists():
        raise FileNotFoundError(path)

    it: Iterator[Dict[str, Any]]
    suf = path.name.lower()
    if suf.endswith(".jsonl") or suf.endswith(".jsonl.gz"):
        it = _iter_jsonl(path)
    else:
        it = _iter_json(path)

    out: Dict[str, Dict[str, set]] = {}
    n = 0
    for obj in it:
        doi = _extract_doi(obj)
        if not doi:
            continue

        hints = out.setdefault(doi, {})

        _merge_sets(hints, key="tasks", values=_as_list(obj.get("tasks") or obj.get("task")))
        _merge_sets(hints, key="datasets", values=_as_list(obj.get("datasets") or obj.get("dataset")))
        _merge_sets(hints, key="metrics", values=_as_list(obj.get("metrics") or obj.get("metric")))

        n += 1
        if limit is not None and n >= int(limit):
            break

    return out

