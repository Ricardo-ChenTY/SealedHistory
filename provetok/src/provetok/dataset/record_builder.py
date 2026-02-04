"""Record builder for PaperRecordV2 (LLM-assisted, best-effort).

The online pipeline uses this module to turn metadata/fulltext into plan.md
record objects. It is designed to be robust when no LLM key is configured.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from provetok.data.schema_v2 import FormulaGraph, PaperRecordInternalV2, PaperRecordV2, Protocol, Results
from provetok.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


EXTRACT_V2_PROMPT = """You are building a public benchmark dataset. Given a paper title and abstract,
produce a *sealed-friendly* structured record. Do NOT output real author names, venues, years, URLs, DOIs, or arXiv IDs.

Title: {title}
Abstract: {abstract}

Output a JSON object with exactly these keys:
{{
  "background": "...",                 // 1-3 sentences, paraphrase only
  "mechanism_tags": ["tag1", ...],     // 1-6 short generic tags; use "other" if unsure
  "keywords": ["kw1", "..."],          // 5-10 distinctive technical terms (model/dataset/techniques); used for lexical sealing
  "protocol": {{
    "task_family_id": "...",           // use unknown_task if unsure
    "dataset_id": "...",               // use unknown_dataset if unsure
    "metric_id": "...",                // use unknown_metric if unsure
    "compute_class": "...",            // small|medium|large|unknown_compute
    "train_regime_class": "..."        // small|medium|large|unknown_regime
  }},
  "results": {{
    "delta_over_baseline_bucket": <int> // in [-3,-2,-1,0,1,2,3]
  }}
}}

Return ONLY the JSON object. No markdown, no extra text.
"""

_FORBIDDEN_PUBLIC_TEXT_PATTERNS: List[tuple[str, str]] = [
    ("url", r"https?://\S+"),
    ("doi", r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b"),
    ("arxiv_word", r"\barxiv\b"),
    ("arxiv_id", r"\b\d{4}\.\d{4,5}(v\d+)?\b"),
    ("year", r"\b(19|20)\d{2}\b"),
]


def _redact_public_text(text: str, *, max_chars: int = 2000) -> str:
    """Redact high-retrieval fingerprints from public text fields.

    This is a best-effort safety layer to keep the pipeline runnable without
    manual review. It does NOT guarantee perfect anonymization.
    """
    out = str(text or "")
    for _, pat in _FORBIDDEN_PUBLIC_TEXT_PATTERNS:
        out = re.sub(pat, " ", out, flags=re.IGNORECASE)
    out = " ".join(out.split())
    return out[:max_chars]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by",
    "for", "from", "has", "have", "in", "into", "is", "it", "its",
    "of", "on", "or", "our", "s", "such", "that", "the", "their", "this",
    "to", "we", "with", "without",
}


def _heuristic_keywords(title: str, abstract: str, max_k: int = 10) -> List[str]:
    kws: List[str] = []

    def add(tok: str) -> None:
        tok = tok.strip().strip(".,;:()[]{}\"'")
        if not tok:
            return
        low = tok.lower()
        if low in _STOPWORDS:
            return
        if len(tok) < 4:
            return
        if tok not in kws:
            kws.append(tok)

    for tok in re.split(r"[\s/]+", title):
        add(tok)
        if len(kws) >= max_k:
            return kws

    # Capture capitalized tokens, hyphenated tokens, and tokens with digits.
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9-]{3,}\b|\b[A-Za-z]{3,}-[A-Za-z0-9-]{2,}\b|\b[A-Za-z]{2,}\d{1,}\b", abstract):
        add(m.group(0))
        if len(kws) >= max_k:
            break

    return kws[:max_k]


def build_record_v2_from_abstract(
    *,
    paper_id: str,
    track_id: str,
    title: str,
    abstract: str,
    dependencies: List[str],
    llm: Optional[LLMClient],
    ids: Optional[Dict[str, Optional[str]]] = None,
) -> PaperRecordInternalV2:
    """Build an internal v2 record (public + mapping metadata)."""
    ids = ids or {}
    prompt = EXTRACT_V2_PROMPT.format(title=title[:200], abstract=abstract[:4000])
    extracted: Dict[str, Any] = {}
    llm_parse_ok = False

    if llm is not None:
        resp = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=1200)
        try:
            extracted = json.loads(resp.content.strip())
            llm_parse_ok = isinstance(extracted, dict)
        except Exception:
            logger.warning("LLM extraction failed for %s; falling back to placeholders", paper_id)

    background_raw = str(extracted.get("background") or "").strip()
    if not background_raw:
        # Best-effort: take a short prefix from the abstract as a fallback.
        background_raw = str(abstract or "").strip()[:600]
    background = _redact_public_text(background_raw, max_chars=2000)
    if not background:
        background = "This work proposes a method and evaluates it on standard benchmarks."
    mech_tags = extracted.get("mechanism_tags") or ["other"]
    if not isinstance(mech_tags, list):
        mech_tags = ["other"]

    keywords = extracted.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k).strip() for k in keywords if str(k).strip()]
    if not keywords:
        keywords = _heuristic_keywords(title, abstract, max_k=10)

    proto_raw = extracted.get("protocol") or {}
    if not isinstance(proto_raw, dict):
        proto_raw = {}

    res_raw = extracted.get("results") or {}
    if not isinstance(res_raw, dict):
        res_raw = {}

    pub = PaperRecordV2(
        paper_id=paper_id,
        track_id=track_id,
        dependencies=list(dependencies or []),
        background=background,
        mechanism_tags=[str(t) for t in mech_tags[:6] if str(t).strip()] or ["other"],
        formula_graph=FormulaGraph(),
        protocol=Protocol(
            task_family_id=str(proto_raw.get("task_family_id") or "unknown_task"),
            dataset_id=str(proto_raw.get("dataset_id") or "unknown_dataset"),
            metric_id=str(proto_raw.get("metric_id") or "unknown_metric"),
            compute_class=str(proto_raw.get("compute_class") or "unknown_compute"),
            train_regime_class=str(proto_raw.get("train_regime_class") or "unknown_regime"),
        ),
        results=Results(
            primary_metric_rank=0,
            delta_over_baseline_bucket=int(res_raw.get("delta_over_baseline_bucket", 0) or 0),
            ablation_delta_buckets=[],
            significance_flag=None,
        ),
        provenance={
            "abstract_sha256": _sha256_text(abstract or ""),
            "builder": "llm_v1" if llm_parse_ok else ("heuristic_v0" if llm is None else "llm_failed_fallback_v0"),
        },
        qa={
            "llm_parse_ok": bool(llm_parse_ok),
        },
    )

    return PaperRecordInternalV2(
        public=pub,
        doi=ids.get("doi"),
        arxiv_id=ids.get("arxiv_id"),
        openalex_id=ids.get("openalex_id"),
        s2_id=ids.get("s2_id"),
        landing_page_url=ids.get("landing_page_url"),
        retrieved_at_unix=int(time.time()),
        title=title,
        keywords=keywords,
    )
