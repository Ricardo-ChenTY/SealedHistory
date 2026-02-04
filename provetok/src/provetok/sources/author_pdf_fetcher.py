"""Author public PDF download helper."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from provetok.sources.http import RateLimiter, http_get


@dataclass(frozen=True)
class AuthorPdfConfig:
    rate_limit_qps: float = 1.0
    timeout_sec: int = 60
    max_pdf_mb: int = 50


class AuthorPdfFetcher:
    def __init__(self, cfg: AuthorPdfConfig):
        self.cfg = cfg
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def download(self, url: str, dest_dir: Path) -> Tuple[Path, str]:
        """Download PDF to dest_dir, named by sha256, returning (path, sha256)."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        resp = http_get(url, headers={"User-Agent": "ProveTok/0.1"}, timeout=self.cfg.timeout_sec, limiter=self._limiter)
        if len(resp.body) > self.cfg.max_pdf_mb * 1024 * 1024:
            raise ValueError(f"PDF too large: {len(resp.body)} bytes > {self.cfg.max_pdf_mb} MB")
        sha = hashlib.sha256(resp.body).hexdigest()
        out = dest_dir / f"{sha}.pdf"
        if not out.exists():
            out.write_bytes(resp.body)
        return out, sha

