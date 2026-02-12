#!/usr/bin/env python3
"""S2-based paper downloader (docs/S2 compliant).

Collection strategy:
- DOI list: use `POST /graph/v1/paper/batch` (up to 500 IDs per request).
- Title list: use `GET /graph/v1/paper/search/match` (one best match).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "provetok" / "src"))

from provetok.sources.s2_client import S2Client, S2Config


S2_FIELDS = (
    "paperId,title,authors,year,abstract,citationCount,venue,openAccessPdf,"
    "externalIds,publicationTypes,journal,url"
)
S2_BATCH_LIMIT = 500


def _normalize_doi(doi: str) -> str:
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


def _extract_doi(paper: dict) -> str:
    ext = paper.get("externalIds") or {}
    if not isinstance(ext, dict):
        return ""
    return _normalize_doi(str(ext.get("DOI") or ext.get("Doi") or ""))


def _s2_graph_base(base_url: str) -> str:
    raw = str(base_url or "").strip().rstrip("/")
    if not raw:
        raw = "https://ai4scholar.net"
    if raw.endswith("/graph/v1"):
        return raw
    return raw + "/graph/v1"


def _dedup_keep_order(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in values:
        s = str(item or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


class PaperDownloader:
    def __init__(self, api_key: str, base_url: str = "https://ai4scholar.net", rate_limit_qps: float = 1.0):
        self.client = S2Client(
            S2Config(
                base_url=_s2_graph_base(base_url),
                api_key=api_key.strip(),
                rate_limit_qps=max(float(rate_limit_qps), 0.1),
            )
        )

    def fetch_by_dois(self, dois: List[str]) -> Dict[str, dict]:
        normalized = [_normalize_doi(x) for x in dois]
        normalized = [x for x in normalized if x]
        normalized = _dedup_keep_order(normalized)
        if not normalized:
            return {}

        query_ids = [f"DOI:{doi}" for doi in normalized]
        found: Dict[str, dict] = {}
        for i in range(0, len(query_ids), S2_BATCH_LIMIT):
            chunk = query_ids[i : i + S2_BATCH_LIMIT]
            rows = self.client.paper_batch(chunk, fields=S2_FIELDS)
            for row in rows:
                doi_norm = _extract_doi(row)
                if doi_norm:
                    found[doi_norm] = row
        return found

    def fetch_by_title(self, title: str) -> Optional[dict]:
        query = str(title or "").strip()
        if not query:
            return None
        row = self.client.search_match(query, fields=S2_FIELDS)
        if not isinstance(row, dict):
            return None
        paper_id = str(row.get("paperId") or "").strip()
        if not paper_id:
            return None
        return row

    def convert_to_pdf_url(self, url: str) -> Optional[str]:
        raw = str(url or "").strip()
        if not raw:
            return None
        if raw.endswith(".pdf"):
            return raw

        if "pmc.ncbi.nlm.nih.gov" in raw or "ncbi.nlm.nih.gov/pmc" in raw:
            token = "PMC"
            pos = raw.upper().find(token)
            if pos >= 0:
                suffix = raw[pos + len(token) :]
                digits = "".join(ch for ch in suffix if ch.isdigit())
                if digits:
                    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{digits}/pdf/"

        if "arxiv.org" in raw:
            if "/abs/" in raw:
                return raw.replace("/abs/", "/pdf/") + ".pdf"
            if "/pdf/" in raw and not raw.endswith(".pdf"):
                return raw + ".pdf"

        if ("biorxiv.org" in raw or "medrxiv.org" in raw) and not raw.endswith(".pdf"):
            return raw + ".full.pdf"

        return raw

    def download_pdf(self, paper: dict, output_dir: str, quiet: bool = False) -> bool:
        pdf_info = paper.get("openAccessPdf") or {}
        if not isinstance(pdf_info, dict):
            pdf_info = {}
        raw_url = str(pdf_info.get("url") or "").strip()
        if not raw_url:
            if not quiet:
                print("No openAccessPdf.url")
            return False

        pdf_url = self.convert_to_pdf_url(raw_url)
        if not pdf_url:
            if not quiet:
                print(f"Invalid PDF URL: {raw_url}")
            return False

        paper_id = str(paper.get("paperId") or "unknown")
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{paper_id}.pdf"
        if out_path.exists():
            if not quiet:
                print(f"PDF exists: {out_path.name}")
            return True

        headers = {
            "User-Agent": "SealedHistory-S2-Downloader/1.0",
            "Accept": "application/pdf,application/octet-stream,*/*",
        }
        if "arxiv.org" in pdf_url:
            headers["Referer"] = "https://arxiv.org/"
        req = urllib.request.Request(pdf_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = int(getattr(resp, "status", 200))
            if status >= 400:
                if not quiet:
                    print(f"PDF download failed [{status}]: {pdf_url}")
                return False
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

        if out_path.stat().st_size <= 0:
            out_path.unlink(missing_ok=True)
            if not quiet:
                print(f"Downloaded empty PDF: {pdf_url}")
            return False

        if not quiet:
            mb = out_path.stat().st_size / 1024 / 1024
            print(f"PDF downloaded: {out_path.name} ({mb:.2f} MB)")
        return True

    def build_paper_meta(self, paper: dict, pdf_downloaded: bool) -> dict:
        paper_id = str(paper.get("paperId") or "unknown")
        title = str(paper.get("title") or "")
        year = paper.get("year")
        venue = str(paper.get("venue") or "")
        citation_count = int(paper.get("citationCount", 0) or 0)
        abstract = str(paper.get("abstract") or "")

        authors_raw = paper.get("authors") or []
        if not isinstance(authors_raw, list):
            authors_raw = []
        author_names = [str(a.get("name") or "") for a in authors_raw if isinstance(a, dict) and a.get("name")]
        authors_str = "; ".join(author_names)

        external_ids = paper.get("externalIds") or {}
        if not isinstance(external_ids, dict):
            external_ids = {}
        doi = str(external_ids.get("DOI") or external_ids.get("Doi") or "")
        arxiv_id = str(external_ids.get("ArXiv") or external_ids.get("arXiv") or "")
        pmid = str(external_ids.get("PubMed") or "")

        pdf_info = paper.get("openAccessPdf") or {}
        if not isinstance(pdf_info, dict):
            pdf_info = {}
        pdf_url = str(pdf_info.get("url") or "")
        pdf_status = str(pdf_info.get("status") or "")

        journal = paper.get("journal") or {}
        if not isinstance(journal, dict):
            journal = {}
        journal_name = str(journal.get("name") or venue)
        journal_volume = str(journal.get("volume") or "")
        journal_pages = str(journal.get("pages") or "")

        pub_types = paper.get("publicationTypes") or []
        if not isinstance(pub_types, list):
            pub_types = []
        pub_types = [str(x) for x in pub_types if str(x)]

        return {
            "paperId": paper_id,
            "title": title,
            "authors": author_names,
            "authorsString": authors_str,
            "year": year,
            "venue": venue,
            "journal": journal_name,
            "journalVolume": journal_volume,
            "journalPages": journal_pages,
            "citationCount": citation_count,
            "abstract": abstract,
            "doi": doi,
            "arxivId": arxiv_id,
            "pmid": pmid,
            "pdfUrl": pdf_url,
            "pdfStatus": pdf_status,
            "publicationTypes": pub_types,
            "publicationTypesString": ", ".join(pub_types),
            "pdfDownloaded": bool(pdf_downloaded),
            "pdfFilename": f"{paper_id}.pdf" if pdf_downloaded else None,
            "downloadTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def save_single_metadata(self, paper: dict, output_dir: str, pdf_downloaded: bool) -> dict:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = self.build_paper_meta(paper, pdf_downloaded)

        (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        row = {
            "paperId": meta["paperId"],
            "title": meta["title"],
            "authors": meta["authorsString"],
            "year": meta["year"],
            "venue": meta["journal"],
            "citationCount": meta["citationCount"],
            "doi": meta["doi"],
            "arxivId": meta["arxivId"],
            "pmid": meta["pmid"],
            "pdfUrl": meta["pdfUrl"],
            "pdfDownloaded": meta["pdfDownloaded"],
            "publicationTypes": meta["publicationTypesString"],
            "abstract": (meta["abstract"][:500] + "...") if len(meta["abstract"]) > 500 else meta["abstract"],
        }
        with open(out_dir / "papers.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            w.writeheader()
            w.writerow(row)
        return meta

    def save_batch_metadata(self, papers_meta: List[dict], output_dir: str, failed_items: List[dict]) -> None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "meta.json").write_text(json.dumps(papers_meta, ensure_ascii=False, indent=2), encoding="utf-8")

        if papers_meta:
            fieldnames = [
                "paperId",
                "title",
                "authors",
                "year",
                "venue",
                "citationCount",
                "doi",
                "arxivId",
                "pmid",
                "pdfUrl",
                "pdfDownloaded",
                "publicationTypes",
                "abstract",
            ]
            with open(out_dir / "papers.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for meta in papers_meta:
                    w.writerow(
                        {
                            "paperId": meta["paperId"],
                            "title": meta["title"],
                            "authors": meta["authorsString"],
                            "year": meta["year"],
                            "venue": meta["journal"],
                            "citationCount": meta["citationCount"],
                            "doi": meta["doi"],
                            "arxivId": meta["arxivId"],
                            "pmid": meta["pmid"],
                            "pdfUrl": meta["pdfUrl"],
                            "pdfDownloaded": meta["pdfDownloaded"],
                            "publicationTypes": meta["publicationTypesString"],
                            "abstract": (meta["abstract"][:500] + "...") if len(meta["abstract"]) > 500 else meta["abstract"],
                        }
                    )

        if failed_items:
            (out_dir / "failed.json").write_text(json.dumps(failed_items, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv_items(csv_path: str, column: Optional[str] = None) -> List[dict]:
    items: List[dict] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return []

        target_col = None
        item_type = None
        if column:
            for fn in fieldnames:
                if fn == column or fn.lower() == column.lower():
                    target_col = fn
                    break
            if not target_col:
                print(f"Column not found: {column}")
                return []
            item_type = "doi" if "doi" in target_col.lower() else "title"
        else:
            for fn in fieldnames:
                if "doi" in fn.lower():
                    target_col = fn
                    item_type = "doi"
                    break
            if not target_col:
                for fn in fieldnames:
                    low = fn.lower()
                    if "title" in low or low in ("题目", "标题", "paper", "name"):
                        target_col = fn
                        item_type = "title"
                        break
            if not target_col:
                print(f"Cannot infer csv column. Available: {', '.join(fieldnames)}")
                return []

        print(f"Using CSV column: {target_col} ({item_type})")
        for idx, row in enumerate(reader, start=1):
            value = str(row.get(target_col) or "").strip()
            if not value:
                continue
            items.append({"index": idx, "type": item_type, "value": value})
    return items


def _print_paper_summary(paper: dict) -> None:
    print("Paper:")
    print(f"  title: {paper.get('title', '')}")
    print(f"  year: {paper.get('year', '')}")
    print(f"  venue: {paper.get('venue', '')}")
    print(f"  citations: {paper.get('citationCount', 0)}")
    print(f"  paperId: {paper.get('paperId', '')}")
    ext = paper.get("externalIds") or {}
    if isinstance(ext, dict):
        if ext.get("DOI") or ext.get("Doi"):
            print(f"  doi: {ext.get('DOI') or ext.get('Doi')}")
        if ext.get("ArXiv") or ext.get("arXiv"):
            print(f"  arxiv: {ext.get('ArXiv') or ext.get('arXiv')}")
    oa = paper.get("openAccessPdf") or {}
    has_pdf = isinstance(oa, dict) and bool(oa.get("url"))
    print(f"  open_access_pdf: {'yes' if has_pdf else 'no'}")


def download_single(args: argparse.Namespace) -> None:
    downloader = PaperDownloader(args.api_key, args.base_url, rate_limit_qps=args.rate_limit_qps)
    paper: Optional[dict] = None

    if args.doi:
        doi_map = downloader.fetch_by_dois([args.doi])
        paper = doi_map.get(_normalize_doi(args.doi))
    elif args.title:
        paper = downloader.fetch_by_title(args.title)

    if not paper:
        print("No paper found.")
        raise SystemExit(1)

    _print_paper_summary(paper)
    pdf_downloaded = False if args.no_pdf else downloader.download_pdf(paper, args.output, quiet=False)
    downloader.save_single_metadata(paper, args.output, pdf_downloaded)
    print(f"Done. Output: {Path(args.output).resolve()}")


def download_batch(args: argparse.Namespace) -> None:
    downloader = PaperDownloader(args.api_key, args.base_url, rate_limit_qps=args.rate_limit_qps)
    items = read_csv_items(args.csv, args.column)
    if not items:
        print("No valid rows in CSV.")
        raise SystemExit(1)

    doi_values = _dedup_keep_order([_normalize_doi(it["value"]) for it in items if it["type"] == "doi"])
    doi_values = [x for x in doi_values if x]
    title_values = _dedup_keep_order([str(it["value"]).strip() for it in items if it["type"] == "title"])

    doi_map = downloader.fetch_by_dois(doi_values) if doi_values else {}

    title_map: Dict[str, dict] = {}
    for idx, title in enumerate(title_values, start=1):
        row = downloader.fetch_by_title(title)
        if row:
            title_map[title] = row
        if idx < len(title_values):
            time.sleep(max(float(args.sleep), 0.0))

    total = len(items)
    success = 0
    pdf_ok = 0
    failed: List[dict] = []
    papers_meta: List[dict] = []

    for i, item in enumerate(items, start=1):
        print(f"[{i}/{total}] {item['type']}: {item['value']}")
        paper = None
        if item["type"] == "doi":
            paper = doi_map.get(_normalize_doi(item["value"]))
        else:
            paper = title_map.get(str(item["value"]).strip())

        if not paper:
            failed.append({"index": i, "input": item["value"], "reason": "paper_not_found"})
            continue

        success += 1
        downloaded = False if args.no_pdf else downloader.download_pdf(paper, args.output, quiet=True)
        if downloaded:
            pdf_ok += 1
        meta = downloader.build_paper_meta(paper, downloaded)
        meta["inputQuery"] = item["value"]
        meta["inputType"] = item["type"]
        papers_meta.append(meta)

    downloader.save_batch_metadata(papers_meta, args.output, failed)
    print("Summary:")
    print(f"  total: {total}")
    print(f"  found: {success}")
    print(f"  pdf_downloaded: {pdf_ok}")
    print(f"  failed: {len(failed)}")
    print(f"  output: {Path(args.output).resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="S2 paper downloader (batch DOI + title match).")
    parser.add_argument("--api-key", required=True, help="ai4scholar.net API key")
    parser.add_argument("--base-url", default="https://ai4scholar.net", help="Base URL")
    parser.add_argument("--rate-limit-qps", type=float, default=1.0, help="Client-side QPS limiter")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay (sec) between title lookups")
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    parser.add_argument("--column", default=None, help="CSV column name (optional)")
    parser.add_argument("--no-pdf", action="store_true", help="Collect metadata only (skip PDF download)")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doi", help="Single DOI")
    group.add_argument("--title", help="Single title")
    group.add_argument("--csv", help="CSV path for batch mode")

    args = parser.parse_args()

    if args.csv:
        download_batch(args)
        return
    download_single(args)


if __name__ == "__main__":
    main()
