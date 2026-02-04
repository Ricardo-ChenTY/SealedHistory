"""Small HTTP helpers (urllib-based) with rate limiting and snapshot support."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class RateLimiter:
    """Best-effort QPS limiter (thread-unsafe)."""

    def __init__(self, qps: float):
        self._min_interval = 1.0 / max(qps, 1e-6)
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        dt = now - self._last
        if dt < self._min_interval:
            time.sleep(self._min_interval - dt)
        self._last = time.time()


@dataclass
class HttpResponse:
    url: str
    status: int
    headers: Dict[str, str]
    body: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class SnapshotWriter:
    """Append-only JSONL snapshot writer."""

    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        url: str,
        request: Dict[str, Any],
        response_status: int,
        response_headers: Dict[str, str],
        response_sha256: str,
        response_len: int,
        response_preview: Optional[str] = None,
        response_json: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        row = {
            "ts_unix": int(time.time()),
            "source": self.source,
            "url": url,
            "request": request,
            "response_status": response_status,
            "response_headers": response_headers,
            "response_sha256": response_sha256,
            "response_len": response_len,
        }
        if response_preview is not None:
            row["response_preview"] = response_preview
        if response_json is not None:
            row["response_json"] = response_json
        if error is not None:
            row["error"] = error

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def http_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
    limiter: Optional[RateLimiter] = None,
    retries: int = 3,
) -> HttpResponse:
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers)

    last_err: Optional[BaseException] = None
    for attempt in range(retries):
        if limiter is not None:
            limiter.wait()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return HttpResponse(
                    url=url,
                    status=int(getattr(resp, "status", 200)),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    body=body,
                )
        except urllib.error.HTTPError as e:
            last_err = e
            # Rate limited or transient server errors: retry with backoff
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:  # pragma: no cover
            last_err = e
            time.sleep(2 ** attempt)
            continue

    if last_err is not None:  # pragma: no cover
        raise last_err
    raise RuntimeError("http_get failed without exception")  # pragma: no cover


def safe_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return headers with secrets removed."""
    redacted = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in ("authorization", "x-api-key", "api-key"):
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted

