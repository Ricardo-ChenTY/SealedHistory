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
from typing import Any, Dict, List, Optional, Sequence

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
    ("venue", r"\b(NeurIPS|ICML|ICLR|CVPR|ICCV|ECCV|ACL|EMNLP|NAACL|COLING)\b"),
]

_NAME_FINGERPRINT_PATTERNS: List[tuple[str, str]] = [
    ("name_initial_surname", r"\b[A-Z]\.\s*[A-Z][a-z]{2,}\b"),
    ("name_surname_et_al", r"\b[A-Z][a-z]{2,}\s+et\s+al\.?\b"),
]


class RecordBuildError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _normalize_taxonomy_key(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _taxonomy_mechanism_tag_vocab(taxonomy: Optional[Dict[str, Any]]) -> tuple[set[str], Dict[str, str]]:
    """Return (allowed, alias_to_tag) for mechanism tags."""
    allowed: set[str] = {"other"}
    alias_to: Dict[str, str] = {}
    if not taxonomy or not isinstance(taxonomy, dict):
        return allowed, alias_to

    mech = taxonomy.get("mechanism_tags") or {}
    if not isinstance(mech, dict):
        return allowed, alias_to

    for tag, info in mech.items():
        tag_norm = _normalize_taxonomy_key(tag)
        if not tag_norm:
            continue
        allowed.add(tag_norm)
        if isinstance(info, dict):
            aliases = info.get("aliases") or []
            if isinstance(aliases, list):
                for a in aliases:
                    a_norm = _normalize_taxonomy_key(a)
                    if a_norm and a_norm not in alias_to:
                        alias_to[a_norm] = tag_norm
    return allowed, alias_to


def _normalize_mechanism_tags(
    tags: Any,
    *,
    taxonomy: Optional[Dict[str, Any]] = None,
    max_tags: int = 6,
) -> List[str]:
    allowed, alias_to = _taxonomy_mechanism_tag_vocab(taxonomy)

    if not isinstance(tags, list):
        tags = ["other"]

    out: List[str] = []
    seen: set[str] = set()
    for t in tags:
        t_norm = _normalize_taxonomy_key(t)
        if not t_norm:
            continue
        t_norm = alias_to.get(t_norm, t_norm)
        if t_norm not in allowed:
            t_norm = "other"
        if t_norm not in seen:
            seen.add(t_norm)
            out.append(t_norm)
        if len(out) >= max_tags:
            break

    return out or ["other"]


def _public_text_patterns(*, forbid_names: bool) -> List[tuple[str, str]]:
    pats = list(_FORBIDDEN_PUBLIC_TEXT_PATTERNS)
    if forbid_names:
        pats.extend(_NAME_FINGERPRINT_PATTERNS)
    return pats


def _redact_public_text(text: str, *, max_chars: int = 2000, forbid_names: bool = False) -> str:
    """Redact high-retrieval fingerprints from public text fields.

    This is a best-effort safety layer to keep the pipeline runnable without
    manual review. It does NOT guarantee perfect anonymization.
    """
    out = str(text or "")
    for _, pat in _public_text_patterns(forbid_names=forbid_names):
        out = re.sub(pat, " ", out, flags=re.IGNORECASE)
    out = " ".join(out.split())
    return out[:max_chars]


def _normalize_public_text(text: str, *, max_chars: int = 2000) -> str:
    out = " ".join(str(text or "").split())
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


def _forbidden_public_text_codes(
    text: str,
    *,
    forbid_names: bool = False,
    name_allowlist: Optional[Sequence[str]] = None,
) -> List[str]:
    hits: List[str] = []
    allow = [str(x).strip().lower() for x in (name_allowlist or []) if str(x).strip()]
    for code, pat in _public_text_patterns(forbid_names=forbid_names):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        if code.startswith("name_") and allow:
            span = str(m.group(0) or "").lower()
            if any(a in span for a in allow):
                continue
        hits.append(code)
    return hits


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^A-Za-z0-9]+", str(text or "").lower()) if t]


def _ngram_overlap_ratio(a: Sequence[str], b: Sequence[str], *, n: int) -> float:
    if n <= 0:
        return 0.0
    if len(a) < n or len(b) < n:
        return 0.0
    ng_a = {tuple(a[i : i + n]) for i in range(len(a) - n + 1)}
    ng_b = {tuple(b[i : i + n]) for i in range(len(b) - n + 1)}
    if not ng_a:
        return 0.0
    return len(ng_a & ng_b) / len(ng_a)


def _contains_verbatim_span(a: Sequence[str], b_text: str, *, span_words: int) -> bool:
    if span_words <= 0 or len(a) < span_words:
        return False
    hay = " ".join(str(b_text or "").lower().split())
    # Background is short; O(n) substring checks are OK.
    for i in range(len(a) - span_words + 1):
        needle = " ".join(a[i : i + span_words])
        if needle and needle in hay:
            return True
    return False


def _validate_strict_background(
    background: str,
    abstract: str,
    *,
    forbid_names: bool = False,
    name_allowlist: Optional[Sequence[str]] = None,
) -> List[str]:
    issues: List[str] = []

    bg = _normalize_public_text(background, max_chars=2000)
    if len(bg.strip()) < 40:
        issues.append("background_too_short")

    forbidden = _forbidden_public_text_codes(bg, forbid_names=forbid_names, name_allowlist=name_allowlist)
    for code in forbidden:
        issues.append(f"forbidden_{code}")

    # Heuristic paraphrase enforcement: avoid long verbatim spans and high n-gram overlap.
    bg_toks = _tokenize(bg)
    abs_toks = _tokenize(abstract)
    if _contains_verbatim_span(bg_toks, abstract, span_words=12):
        issues.append("verbatim_span_12w")

    overlap = _ngram_overlap_ratio(bg_toks, abs_toks, n=6)
    if overlap >= 0.45:
        issues.append(f"ngram_overlap_{overlap:.2f}")

    return issues


def _parse_llm_json_object(text: str) -> Dict[str, Any]:
    """Parse a JSON object from LLM output, tolerant to fenced wrappers."""
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty_response")

    # Common case: markdown fenced block.
    fenced = raw
    if fenced.startswith("```"):
        fenced = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", fenced)
        fenced = re.sub(r"\s*```$", "", fenced)
        fenced = fenced.strip()
        raw = fenced

    # Fallback: extract first top-level object substring.
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]

    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("bad_json_root")
    return obj


def build_record_v2_from_abstract(
    *,
    paper_id: str,
    track_id: str,
    title: str,
    abstract: str,
    dependencies: List[str],
    llm: Optional[LLMClient],
    ids: Optional[Dict[str, Optional[str]]] = None,
    strict_paraphrase: bool = False,
    max_retries: int = 0,
    prompt_version: Optional[str] = None,
    taxonomy: Optional[Dict[str, Any]] = None,
    forbid_names: bool = False,
    name_allowlist: Optional[List[str]] = None,
) -> PaperRecordInternalV2:
    """Build an internal v2 record (public + mapping metadata)."""
    ids = ids or {}
    prompt = EXTRACT_V2_PROMPT.format(title=title[:200], abstract=abstract[:4000])
    extracted: Dict[str, Any] = {}
    llm_parse_ok = False

    if strict_paraphrase and llm is None:
        raise RecordBuildError(
            "llm_required",
            "strict_paraphrase=true requires a real LLM client (llm is None)",
        )

    attempts = 1 if not strict_paraphrase else max(1, int(max_retries) + 1)
    last_llm_error: Optional[str] = None
    last_policy_issues: List[str] = []

    for attempt in range(attempts):
        extracted = {}
        llm_parse_ok = False
        last_llm_error = None
        last_policy_issues = []

        if llm is None:
            break

        if hasattr(llm, "structured_chat"):
            resp = llm.structured_chat(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1200,
            )
        else:
            resp = llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1200,
            )
        extracted = _parse_llm_json_object(resp.content)
        llm_parse_ok = True

        if not strict_paraphrase:
            break

        background_candidate = str(extracted.get("background") or "").strip()
        if not background_candidate:
            last_policy_issues = ["background_missing"]
            continue

        policy_issues = _validate_strict_background(
            background_candidate,
            abstract=abstract,
            forbid_names=forbid_names,
            name_allowlist=name_allowlist,
        )
        if policy_issues:
            last_policy_issues = policy_issues
            continue

        # Strict policy satisfied.
        break

    background_raw = str(extracted.get("background") or "").strip()
    if strict_paraphrase:
        if not background_raw:
            raise RecordBuildError(
                "background_missing",
                f"strict_paraphrase=true but background is empty (last_llm_error={last_llm_error}, policy_issues={last_policy_issues})",
            )
        policy_issues = _validate_strict_background(
            background_raw,
            abstract=abstract,
            forbid_names=forbid_names,
            name_allowlist=name_allowlist,
        )
        if policy_issues:
            raise RecordBuildError(
                "background_policy_fail",
                f"strict_paraphrase=true but background failed policy: {policy_issues}",
            )
        background = _normalize_public_text(background_raw, max_chars=2000)
    else:
        if not background_raw:
            # Best-effort: take a short prefix from the abstract as a fallback.
            background_raw = str(abstract or "").strip()[:600]
        background = _redact_public_text(background_raw, max_chars=2000, forbid_names=forbid_names)
        if not background:
            background = "This work proposes a method and evaluates it on standard benchmarks."
    mech_tags = extracted.get("mechanism_tags") or ["other"]
    mech_tags = _normalize_mechanism_tags(mech_tags, taxonomy=taxonomy, max_tags=6)

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
        mechanism_tags=mech_tags,
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
            "builder": (
                "llm_v1_strict"
                if strict_paraphrase
                else ("llm_v1" if llm_parse_ok else ("heuristic_v0" if llm is None else "llm_failed_fallback_v0"))
            ),
            **({"prompt_version": str(prompt_version)} if prompt_version else {}),
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
