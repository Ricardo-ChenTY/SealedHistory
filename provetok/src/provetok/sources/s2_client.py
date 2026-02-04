"""Semantic Scholar (S2) client with snapshot logging."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional

from provetok.sources.http import RateLimiter, SnapshotWriter, http_get, safe_headers


DEFAULT_FIELDS = (
    "paperId,title,abstract,year,venue,authors,citationCount,references,fieldsOfStudy,externalIds,url,openAccessPdf"
)


@dataclass(frozen=True)
class S2Config:
    base_url: str = "https://api.semanticscholar.org/graph/v1"
    api_key: str = ""
    rate_limit_qps: float = 1.0


class S2Client:
    def __init__(self, cfg: S2Config, snapshot: Optional[SnapshotWriter] = None):
        self.cfg = cfg
        self.snapshot = snapshot
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def get_paper(self, paper_key: str, fields: str = DEFAULT_FIELDS) -> Optional[Dict[str, Any]]:
        url = f"{self.cfg.base_url.rstrip('/')}/paper/{urllib.parse.quote(paper_key)}?fields={urllib.parse.quote(fields)}"
        headers = {"User-Agent": "ProveTok/0.1"}
        if self.cfg.api_key:
            headers["x-api-key"] = self.cfg.api_key
        resp = http_get(url, headers=headers, timeout=60, limiter=self._limiter)
        data = resp.json()
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={"paper_key": paper_key, "fields": fields},
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={"paperId": data.get("paperId"), "title": data.get("title"), "year": data.get("year")},
            )
        return data

    def search(self, query: str, *, limit: int = 1, fields: str = DEFAULT_FIELDS) -> Optional[Dict[str, Any]]:
        q = urllib.parse.quote(query)
        url = (
            f"{self.cfg.base_url.rstrip('/')}/paper/search?query={q}"
            f"&limit={limit}&fields={urllib.parse.quote(fields)}"
        )
        headers = {"User-Agent": "ProveTok/0.1"}
        if self.cfg.api_key:
            headers["x-api-key"] = self.cfg.api_key
        resp = http_get(url, headers=headers, timeout=60, limiter=self._limiter)
        data = resp.json()
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={"query": query, "limit": limit, "fields": fields},
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={"n_results": len(data.get("data") or [])},
            )
        return data

