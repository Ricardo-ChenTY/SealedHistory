"""arXiv metadata + fulltext fetch helpers."""

from __future__ import annotations

import hashlib
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from provetok.sources.http import RateLimiter, SnapshotWriter, http_get, safe_headers


@dataclass(frozen=True)
class ArxivConfig:
    oai_base_url: str = "https://export.arxiv.org/oai2"
    use_oai_pmh: bool = True
    use_api_fallback: bool = True
    rate_limit_qps: float = 1.0
    timeout_sec: int = 60


class ArxivClient:
    def __init__(self, cfg: ArxivConfig, snapshot: Optional[SnapshotWriter] = None):
        self.cfg = cfg
        self.snapshot = snapshot
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def fetch_oai_record_xml(self, arxiv_id: str, metadata_prefix: str = "arXiv") -> str:
        ident = f"oai:arXiv.org:{arxiv_id}"
        params = {
            "verb": "GetRecord",
            "identifier": ident,
            "metadataPrefix": metadata_prefix,
        }
        url = f"{self.cfg.oai_base_url.rstrip('/')}?{urllib.parse.urlencode(params)}"
        headers = {"User-Agent": "ProveTok/0.1"}
        resp = http_get(url, headers=headers, timeout=self.cfg.timeout_sec, limiter=self._limiter)
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={"arxiv_id": arxiv_id, "metadataPrefix": metadata_prefix},
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
            )
        return resp.text

    def download_pdf(self, arxiv_id: str, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_id = arxiv_id.replace("/", "_")
        out = dest_dir / f"{safe_id}.pdf"
        if out.exists() and out.stat().st_size > 0:
            return out
        url = f"https://arxiv.org/pdf/{urllib.parse.quote(arxiv_id)}.pdf"
        headers = {"User-Agent": "ProveTok/0.1"}
        resp = http_get(url, headers=headers, timeout=self.cfg.timeout_sec, limiter=self._limiter)
        out.write_bytes(resp.body)
        return out

    def download_source(self, arxiv_id: str, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_id = arxiv_id.replace("/", "_")
        out = dest_dir / f"{safe_id}.source"
        if out.exists() and out.stat().st_size > 0:
            return out
        url = f"https://arxiv.org/e-print/{urllib.parse.quote(arxiv_id)}"
        headers = {"User-Agent": "ProveTok/0.1"}
        resp = http_get(url, headers=headers, timeout=self.cfg.timeout_sec, limiter=self._limiter)
        out.write_bytes(resp.body)
        return out
