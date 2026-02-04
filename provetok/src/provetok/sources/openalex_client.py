"""OpenAlex client (works fetch + snapshot logging)."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from provetok.sources.http import RateLimiter, SnapshotWriter, http_get, safe_headers


@dataclass(frozen=True)
class OpenAlexConfig:
    base_url: str = "https://api.openalex.org"
    mailto: str = ""
    per_page: int = 200
    max_pages: int = 50
    rate_limit_qps: float = 3.0


class OpenAlexClient:
    def __init__(self, cfg: OpenAlexConfig, snapshot: Optional[SnapshotWriter] = None):
        self.cfg = cfg
        self.snapshot = snapshot
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def iter_works(
        self,
        *,
        filter_str: Optional[str] = None,
        search: Optional[str] = None,
        select: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield raw OpenAlex work objects."""
        cursor = "*"
        for page_idx in range(self.cfg.max_pages):
            url = self._works_url(
                cursor=cursor,
                filter_str=filter_str,
                search=search,
                select=select,
            )
            headers = {"User-Agent": "ProveTok/0.1"}
            resp = http_get(url, headers=headers, timeout=60, limiter=self._limiter)
            data = resp.json()

            if self.snapshot is not None:
                self.snapshot.write(
                    url=url,
                    request={"cursor": cursor, "filter": filter_str, "search": search, "select": select},
                    response_status=resp.status,
                    response_headers=safe_headers(resp.headers),
                    response_sha256=resp.sha256,
                    response_len=len(resp.body),
                    response_preview=resp.text[:500],
                    response_json={"meta": data.get("meta", {}), "n_results": len(data.get("results") or [])},
                )

            results = data.get("results") or []
            for w in results:
                yield w

            meta = data.get("meta") or {}
            next_cursor = meta.get("next_cursor")
            if not next_cursor:
                break
            cursor = str(next_cursor)

    def _works_url(
        self,
        *,
        cursor: str,
        filter_str: Optional[str],
        search: Optional[str],
        select: Optional[str],
    ) -> str:
        params: Dict[str, str] = {
            "per-page": str(self.cfg.per_page),
            "cursor": cursor,
        }
        if self.cfg.mailto:
            params["mailto"] = self.cfg.mailto
        if filter_str:
            params["filter"] = filter_str
        if search:
            params["search"] = search
        if select:
            params["select"] = select
        return f"{self.cfg.base_url.rstrip('/')}/works?{urllib.parse.urlencode(params)}"

