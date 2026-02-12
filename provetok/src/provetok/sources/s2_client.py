"""Semantic Scholar (S2) client with snapshot logging."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from provetok.sources.http import RateLimiter, SnapshotWriter, http_get, http_post_json, safe_headers


DEFAULT_FIELDS = (
    "paperId,title,abstract,year,venue,authors,citationCount,references,fieldsOfStudy,externalIds,url,openAccessPdf"
)
DEFAULT_BATCH_CHUNK_SIZE = 500


@dataclass(frozen=True)
class S2Config:
    base_url: str = "https://ai4scholar.net/graph/v1"
    api_key: str = ""
    rate_limit_qps: float = 1.0


class S2Client:
    def __init__(self, cfg: S2Config, snapshot: Optional[SnapshotWriter] = None):
        self.cfg = cfg
        self.snapshot = snapshot
        self._limiter = RateLimiter(cfg.rate_limit_qps)

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "ProveTok/0.1"}
        if self.cfg.api_key:
            headers["x-api-key"] = self.cfg.api_key
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def _build_url(self, path: str, params: Sequence[str]) -> str:
        base = self.cfg.base_url.rstrip("/")
        if not params:
            return f"{base}{path}"
        return f"{base}{path}?" + "&".join(params)

    def get_paper(self, paper_key: str, fields: str = DEFAULT_FIELDS) -> Optional[Dict[str, Any]]:
        url = self._build_url(
            f"/paper/{urllib.parse.quote(paper_key)}",
            [f"fields={urllib.parse.quote(fields)}"],
        )
        resp = http_get(url, headers=self._headers(), timeout=60, limiter=self._limiter)
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

    def search_match(
        self,
        query: str,
        *,
        fields: str = DEFAULT_FIELDS,
        year: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        min_citation_count: Optional[int] = None,
        open_access_pdf: bool = False,
    ) -> Optional[Dict[str, Any]]:
        params = [f"query={urllib.parse.quote(query)}", f"fields={urllib.parse.quote(fields)}"]
        if year:
            params.append(f"year={urllib.parse.quote(str(year))}")
        if fields_of_study:
            params.append(f"fieldsOfStudy={urllib.parse.quote(str(fields_of_study))}")
        if min_citation_count is not None:
            params.append(f"minCitationCount={int(min_citation_count)}")
        if open_access_pdf:
            params.append("openAccessPdf")

        url = self._build_url("/paper/search/match", params)
        resp = http_get(url, headers=self._headers(), timeout=60, limiter=self._limiter)
        data = resp.json()
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={
                    "query": query,
                    "fields": fields,
                    "year": year or "",
                    "fieldsOfStudy": fields_of_study or "",
                    "minCitationCount": min_citation_count if min_citation_count is not None else "",
                    "openAccessPdf": bool(open_access_pdf),
                },
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={"paperId": data.get("paperId"), "title": data.get("title")},
            )
        return data

    def search(
        self,
        query: str,
        *,
        limit: int = 1,
        offset: int = 0,
        fields: str = DEFAULT_FIELDS,
        year: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        min_citation_count: Optional[int] = None,
        open_access_pdf: bool = False,
    ) -> Optional[Dict[str, Any]]:
        q = urllib.parse.quote(query)
        params = [f"query={q}", f"limit={int(limit)}", f"offset={int(offset)}", f"fields={urllib.parse.quote(fields)}"]
        if year:
            params.append(f"year={urllib.parse.quote(str(year))}")
        if fields_of_study:
            params.append(f"fieldsOfStudy={urllib.parse.quote(str(fields_of_study))}")
        if min_citation_count is not None:
            params.append(f"minCitationCount={int(min_citation_count)}")
        if open_access_pdf:
            params.append("openAccessPdf")

        url = self._build_url("/paper/search", params)
        resp = http_get(url, headers=self._headers(), timeout=60, limiter=self._limiter)
        data = resp.json()
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={
                    "query": query,
                    "limit": int(limit),
                    "offset": int(offset),
                    "fields": fields,
                    "year": year or "",
                    "fieldsOfStudy": fields_of_study or "",
                    "minCitationCount": min_citation_count if min_citation_count is not None else "",
                    "openAccessPdf": bool(open_access_pdf),
                },
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={"n_results": len(data.get("data") or [])},
            )
        return data

    def search_bulk(
        self,
        *,
        query: str,
        token: str = "",
        fields: str = DEFAULT_FIELDS,
        sort: str = "citationCount:desc",
        year: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        min_citation_count: Optional[int] = None,
        open_access_pdf: bool = False,
    ) -> Optional[Dict[str, Any]]:
        params = [f"query={urllib.parse.quote(query)}", f"fields={urllib.parse.quote(fields)}", f"sort={urllib.parse.quote(sort)}"]
        if token:
            params.append(f"token={urllib.parse.quote(token)}")
        if year:
            params.append(f"year={urllib.parse.quote(str(year))}")
        if fields_of_study:
            params.append(f"fieldsOfStudy={urllib.parse.quote(str(fields_of_study))}")
        if min_citation_count is not None:
            params.append(f"minCitationCount={int(min_citation_count)}")
        if open_access_pdf:
            params.append("openAccessPdf")

        url = self._build_url("/paper/search/bulk", params)
        resp = http_get(url, headers=self._headers(), timeout=60, limiter=self._limiter)
        data = resp.json()
        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={
                    "query": query,
                    "token": token,
                    "fields": fields,
                    "sort": sort,
                    "year": year or "",
                    "fieldsOfStudy": fields_of_study or "",
                    "minCitationCount": min_citation_count if min_citation_count is not None else "",
                    "openAccessPdf": bool(open_access_pdf),
                },
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={
                    "n_results": len(data.get("data") or []),
                    "has_token": bool(data.get("token")),
                    "total": data.get("total"),
                },
            )
        return data

    def iter_search_bulk(
        self,
        *,
        query: str,
        fields: str = DEFAULT_FIELDS,
        sort: str = "citationCount:desc",
        year: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        min_citation_count: Optional[int] = None,
        open_access_pdf: bool = False,
        max_results: int = 10000,
    ) -> Iterable[Dict[str, Any]]:
        token = ""
        emitted = 0
        while emitted < max_results:
            page = self.search_bulk(
                query=query,
                token=token,
                fields=fields,
                sort=sort,
                year=year,
                fields_of_study=fields_of_study,
                min_citation_count=min_citation_count,
                open_access_pdf=open_access_pdf,
            ) or {}
            data = page.get("data") or []
            if not isinstance(data, list) or not data:
                break
            for row in data:
                if not isinstance(row, dict):
                    continue
                yield row
                emitted += 1
                if emitted >= max_results:
                    return

            next_token = str(page.get("token") or "").strip()
            if not next_token or next_token == token:
                break
            token = next_token

    def paper_batch(self, ids: Sequence[str], *, fields: str = DEFAULT_FIELDS) -> List[Dict[str, Any]]:
        uniq_ids: List[str] = []
        seen = set()
        for raw_id in ids:
            paper_id = str(raw_id or "").strip()
            if not paper_id or paper_id in seen:
                continue
            seen.add(paper_id)
            uniq_ids.append(paper_id)

        if not uniq_ids:
            return []
        if len(uniq_ids) > DEFAULT_BATCH_CHUNK_SIZE:
            raise ValueError(f"paper_batch ids must be <= {DEFAULT_BATCH_CHUNK_SIZE}")

        url = self._build_url("/paper/batch", [f"fields={urllib.parse.quote(fields)}"])
        payload = {"ids": uniq_ids}
        resp = http_post_json(url, json_body=payload, headers=self._headers(), timeout=60, limiter=self._limiter)
        data = resp.json()
        rows = data if isinstance(data, list) else []

        if self.snapshot is not None:
            self.snapshot.write(
                url=url,
                request={"ids_n": len(uniq_ids), "fields": fields},
                response_status=resp.status,
                response_headers=safe_headers(resp.headers),
                response_sha256=resp.sha256,
                response_len=len(resp.body),
                response_preview=resp.text[:500],
                response_json={"n_results": len(rows)},
            )
        return [row for row in rows if isinstance(row, dict)]

    def iter_paper_batch(
        self,
        ids: Iterable[str],
        *,
        fields: str = DEFAULT_FIELDS,
        chunk_size: int = DEFAULT_BATCH_CHUNK_SIZE,
    ) -> Iterable[Dict[str, Any]]:
        if chunk_size <= 0 or chunk_size > DEFAULT_BATCH_CHUNK_SIZE:
            raise ValueError(f"chunk_size must be in [1, {DEFAULT_BATCH_CHUNK_SIZE}]")

        uniq_ids: List[str] = []
        seen = set()
        for raw_id in ids:
            paper_id = str(raw_id or "").strip()
            if not paper_id or paper_id in seen:
                continue
            seen.add(paper_id)
            uniq_ids.append(paper_id)

        for i in range(0, len(uniq_ids), chunk_size):
            chunk = uniq_ids[i : i + chunk_size]
            for row in self.paper_batch(chunk, fields=fields):
                yield row
