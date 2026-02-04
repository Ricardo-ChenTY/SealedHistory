"""OpenCitations client (best-effort DOI citation checks)."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional

from provetok.sources.http import RateLimiter, SnapshotWriter, http_get, safe_headers


@dataclass(frozen=True)
class OpenCitationsConfig:
    base_url: str = "https://api.opencitations.net/index/v1"
    rate_limit_qps: float = 2.0


class OpenCitationsClient:
    def __init__(self, cfg: OpenCitationsConfig, snapshot: Optional[SnapshotWriter] = None):
        self.cfg = cfg
        self.snapshot = snapshot
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def citations(self, doi: str) -> Any:
        doi_q = urllib.parse.quote(doi)
        url = f"{self.cfg.base_url.rstrip('/')}/citations/{doi_q}"
        headers = {"User-Agent": "ProveTok/0.1"}
        try:
            resp = http_get(url, headers=headers, timeout=60, limiter=self._limiter)
            data = resp.json()
            if self.snapshot is not None:
                self.snapshot.write(
                    url=url,
                    request={"doi": doi, "endpoint": "citations"},
                    response_status=resp.status,
                    response_headers=safe_headers(resp.headers),
                    response_sha256=resp.sha256,
                    response_len=len(resp.body),
                    response_preview=resp.text[:500],
                    response_json={"n_results": len(data) if isinstance(data, list) else None},
                )
            return data
        except Exception as e:
            if self.snapshot is not None:
                self.snapshot.write(
                    url=url,
                    request={"doi": doi, "endpoint": "citations"},
                    response_status=0,
                    response_headers={},
                    response_sha256="",
                    response_len=0,
                    error=str(e),
                )
            return []

    def references(self, doi: str) -> Any:
        """Return outgoing references for a DOI (DOI -> DOI edges)."""
        doi_q = urllib.parse.quote(doi)
        url = f"{self.cfg.base_url.rstrip('/')}/references/{doi_q}"
        headers = {"User-Agent": "ProveTok/0.1"}
        try:
            resp = http_get(url, headers=headers, timeout=60, limiter=self._limiter)
            data = resp.json()
            if self.snapshot is not None:
                self.snapshot.write(
                    url=url,
                    request={"doi": doi, "endpoint": "references"},
                    response_status=resp.status,
                    response_headers=safe_headers(resp.headers),
                    response_sha256=resp.sha256,
                    response_len=len(resp.body),
                    response_preview=resp.text[:500],
                    response_json={"n_results": len(data) if isinstance(data, list) else None},
                )
            return data
        except Exception as e:
            if self.snapshot is not None:
                self.snapshot.write(
                    url=url,
                    request={"doi": doi, "endpoint": "references"},
                    response_status=0,
                    response_headers={},
                    response_sha256="",
                    response_len=0,
                    error=str(e),
                )
            return []
