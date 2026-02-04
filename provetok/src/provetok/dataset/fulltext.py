"""Fulltext caching for selected papers (private artifacts only).

Policy options:
  - none
  - arxiv_only
  - arxiv_and_author_pdf

This module is used by the online pipeline. It is safe to keep generated files
under `private/` (gitignored by default).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from provetok.dataset.paths import DatasetPaths
from provetok.sources.arxiv_client import ArxivClient, ArxivConfig
from provetok.sources.author_pdf_fetcher import AuthorPdfFetcher, AuthorPdfConfig

logger = logging.getLogger(__name__)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_fulltext_index_for_mapping_rows(
    *,
    paths: DatasetPaths,
    mapping_rows: List[Dict[str, Any]],
    tier: str,
    ts_unix: Optional[int] = None,
) -> None:
    """Write a deterministic fulltext index from mapping rows (no downloads).

    This is useful for derived tiers (e.g., core subset of an extended pool),
    where fulltext has already been cached in the mapping rows.
    """
    build_ts = int(ts_unix or time.time())
    index_path = paths.private_fulltext_index_path(tier)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        for row in mapping_rows:
            paper_id = str(row.get("paper_id") or "")
            arxiv_id = row.get("arxiv_id") or None
            author_url = row.get("author_pdf_url") or None
            sources = list(row.get("source_paths") or [])
            pdf_sha256 = row.get("pdf_sha256") or None
            status = str(row.get("fulltext_status") or "")
            if not status:
                status = "ok_cached" if (sources or pdf_sha256) else "missing"
            f.write(
                json.dumps(
                    {
                        "ts_unix": build_ts,
                        "tier": tier,
                        "paper_id": paper_id,
                        "status": status,
                        "arxiv_id": arxiv_id,
                        "author_pdf_url": author_url,
                        "pdf_sha256": pdf_sha256,
                        "source_paths": sources,
                        "retrieved_at_unix": row.get("retrieved_at_unix"),
                        "fulltext_source": row.get("fulltext_source"),
                        "fulltext_policy": row.get("fulltext_policy"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def load_author_pdf_overrides(path: Optional[Path]) -> Dict[str, str]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in (".yaml", ".yml"):
        raise ValueError("author_pdf_overrides_file must be YAML")
    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise ImportError("pyyaml is required: pip install pyyaml") from e

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(raw, dict):
        # expected: {paper_key: url, ...}
        return {str(k): str(v) for k, v in raw.items() if v}
    raise ValueError("author_pdf_overrides_file YAML must be a mapping")  # pragma: no cover


def cache_fulltext_for_mapping_rows(
    cfg: Dict[str, Any],
    *,
    paths: DatasetPaths,
    mapping_rows: List[Dict[str, Any]],
    offline: bool,
    tier: str = "extended",
    write_index: bool = True,
    arxiv_client: Optional[ArxivClient] = None,
    pdf_fetcher: Optional[AuthorPdfFetcher] = None,
    overrides: Optional[Dict[str, str]] = None,
    ts_unix: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Download/cache fulltext based on mapping rows.

    mapping_rows are dicts containing at least:
      - paper_id
      - arxiv_id (optional)
      - author_pdf_url (optional)
    """
    ft_cfg = cfg.get("fulltext") or {}
    tier_cfg = ft_cfg.get(tier) or {}
    if not isinstance(tier_cfg, dict):
        tier_cfg = {}
    policy = str(tier_cfg.get("policy") or ft_cfg.get("policy", "none"))
    if policy == "none":
        logger.info("Fulltext policy=none; skipping downloads")
        return [
            {**dict(r), "fulltext_status": "skipped_none", "fulltext_source": None, "fulltext_policy": policy}
            for r in mapping_rows
        ]

    if offline:
        logger.info("Offline mode enabled; skipping fulltext downloads")
        return [
            {**dict(r), "fulltext_status": "skipped_offline", "fulltext_source": None, "fulltext_policy": policy}
            for r in mapping_rows
        ]

    if overrides is None:
        overrides_path = ft_cfg.get("author_pdf_overrides_file") or ""
        overrides = load_author_pdf_overrides(Path(overrides_path)) if overrides_path else {}

    if arxiv_client is None:
        arxiv_cfg_raw = (cfg.get("sources") or {}).get("arxiv") or {}
        arxiv_client = ArxivClient(
            ArxivConfig(
                oai_base_url=str(arxiv_cfg_raw.get("oai_base_url", "https://export.arxiv.org/oai2")),
                use_oai_pmh=bool(arxiv_cfg_raw.get("use_oai_pmh", True)),
                use_api_fallback=bool(arxiv_cfg_raw.get("use_api_fallback", True)),
                rate_limit_qps=float(arxiv_cfg_raw.get("rate_limit_qps", 1.0)),
                timeout_sec=int(ft_cfg.get("timeout_sec", 60)),
            )
        )

    if pdf_fetcher is None:
        pdf_fetcher = AuthorPdfFetcher(
            AuthorPdfConfig(
                rate_limit_qps=float((cfg.get("sources") or {}).get("s2", {}).get("rate_limit_qps", 1.0)),
                timeout_sec=int(ft_cfg.get("timeout_sec", 60)),
                max_pdf_mb=int(ft_cfg.get("max_pdf_mb", 50)),
            )
        )

    arxiv_root = paths.private_dir / "fulltext_cache" / "arxiv"
    pdf_root = paths.private_dir / "fulltext_cache" / "pdfs"
    index_path = paths.private_fulltext_index_path(tier)

    build_ts = int(ts_unix or time.time())

    updated = []
    for row in mapping_rows:
        paper_id = str(row.get("paper_id", ""))
        arxiv_id = row.get("arxiv_id") or None

        author_url = row.get("author_pdf_url") or None
        if not author_url:
            # Allow override by openalex_id/doi/paper_id
            for k in (row.get("openalex_id"), row.get("doi"), paper_id):
                if k and str(k) in overrides:
                    author_url = overrides[str(k)]
                    break

        sources: List[str] = []
        pdf_sha256: Optional[str] = None
        status = "skipped"
        ft_source: Optional[str] = None
        ft_error: Optional[str] = None

        try:
            if arxiv_id and policy in ("arxiv_only", "arxiv_and_author_pdf"):
                out_dir = arxiv_root / arxiv_id.replace("/", "_")
                pdf_path = arxiv_client.download_pdf(arxiv_id, out_dir)
                sources.append(str(pdf_path))
                pdf_sha256 = _sha256_file(pdf_path)
                ft_source = "arxiv"
                status = "ok_arxiv_pdf"

                # Best-effort: also fetch arXiv source for formula parsing.
                try:
                    src_path = arxiv_client.download_source(arxiv_id, out_dir)
                    sources.append(str(src_path))
                    status = "ok_arxiv_pdf_source"
                except Exception as e:
                    logger.warning("arXiv source download failed for %s: %s", paper_id, e)
            elif author_url and policy == "arxiv_and_author_pdf":
                pdf_path, pdf_sha256 = pdf_fetcher.download(author_url, pdf_root)
                sources.append(str(pdf_path))
                ft_source = "author_pdf"
                status = "ok_author_pdf"
            else:
                status = "missing"
        except Exception as e:
            status = f"error:{type(e).__name__}"
            ft_error = str(e)

            # Fallback: if arXiv failed and policy allows, try author PDF.
            if arxiv_id and author_url and policy == "arxiv_and_author_pdf":
                try:
                    pdf_path, pdf_sha256 = pdf_fetcher.download(author_url, pdf_root)
                    sources.append(str(pdf_path))
                    ft_source = "author_pdf"
                    status = "ok_author_pdf"
                    ft_error = None
                except Exception as e2:
                    status = f"error:{type(e2).__name__}"
                    ft_error = str(e2)

            if write_index:
                _append_jsonl(
                    index_path,
                    {
                        "ts_unix": build_ts,
                        "tier": tier,
                        "paper_id": paper_id,
                        "status": status,
                        "error": ft_error,
                        "arxiv_id": arxiv_id,
                        "author_pdf_url": author_url,
                        "fulltext_source": ft_source,
                        "fulltext_policy": policy,
                    },
                )

            new_row = dict(row)
            new_row["fulltext_status"] = status
            new_row["fulltext_source"] = ft_source
            new_row["fulltext_policy"] = policy
            if ft_error:
                new_row["fulltext_error"] = ft_error
            updated.append(new_row)
            continue

        new_row = dict(row)
        new_row["fulltext_status"] = status
        new_row["fulltext_source"] = ft_source
        new_row["fulltext_policy"] = policy
        if sources:
            new_row.setdefault("source_paths", [])
            new_row["source_paths"] = list(new_row["source_paths"]) + sources
        if pdf_sha256:
            new_row["pdf_sha256"] = pdf_sha256
        new_row["retrieved_at_unix"] = build_ts

        if write_index:
            _append_jsonl(
                index_path,
                {
                    "ts_unix": build_ts,
                    "tier": tier,
                    "paper_id": paper_id,
                    "status": status,
                    "arxiv_id": arxiv_id,
                    "author_pdf_url": author_url,
                    "pdf_sha256": pdf_sha256,
                    "source_paths": sources,
                    "fulltext_source": ft_source,
                    "fulltext_policy": policy,
                },
            )
        updated.append(new_row)

    return updated
