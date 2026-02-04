"""Semi-automated data collection pipeline.

Flow:
  1. Define a curated list of milestone papers (Semantic Scholar IDs or titles)
  2. Fetch metadata from Semantic Scholar API (no auth needed for basic fields)
  3. Use LLM to extract structured PaperRecord fields from abstract + metadata
  4. Output draft JSONL for human review

This follows the MLE-bench pattern of curating tasks from an existing source
(Kaggle for MLE-bench, Semantic Scholar for us), then standardising the format.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import urllib.request
import urllib.error
import urllib.parse

from provetok.data.schema import PaperRecord, ExperimentResult, save_records
from provetok.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ======================================================================
# Semantic Scholar API client (no auth required for basic fields)
# ======================================================================

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "paperId,title,abstract,year,venue,authors,citationCount,references,fieldsOfStudy"


@dataclass
class S2Paper:
    """Raw paper metadata from Semantic Scholar."""
    paper_id: str
    title: str
    abstract: str
    year: Optional[int]
    venue: Optional[str]
    authors: List[str]
    citation_count: int
    reference_ids: List[str]  # S2 paper IDs of references
    fields_of_study: List[str]
    raw: Dict[str, Any] = field(default_factory=dict)


def fetch_paper_by_id(s2_id: str, api_key: Optional[str] = None) -> Optional[S2Paper]:
    """Fetch a single paper by Semantic Scholar ID or DOI."""
    url = f"{S2_API_BASE}/paper/{s2_id}?fields={S2_FIELDS}"
    return _fetch(url, api_key)


def search_paper_by_title(title: str, api_key: Optional[str] = None) -> Optional[S2Paper]:
    """Search for a paper by title, return best match."""
    query = urllib.parse.quote(title)
    url = f"{S2_API_BASE}/paper/search?query={query}&limit=1&fields={S2_FIELDS}"
    try:
        data = _http_get(url, api_key)
        if data and data.get("data"):
            return _parse_s2_paper(data["data"][0])
    except Exception as e:
        logger.error("Search failed for '%s': %s", title, e)
    return None


def _fetch(url: str, api_key: Optional[str] = None) -> Optional[S2Paper]:
    try:
        data = _http_get(url, api_key)
        if data:
            return _parse_s2_paper(data)
    except Exception as e:
        logger.error("Fetch failed: %s", e)
    return None


def _http_get(url: str, api_key: Optional[str] = None) -> Optional[dict]:
    """Simple HTTP GET with rate-limit retry."""
    headers = {"User-Agent": "ProveTok/0.1"}
    if api_key:
        headers["x-api-key"] = api_key

    req = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
            else:
                raise
    return None


def _parse_s2_paper(d: dict) -> S2Paper:
    authors = [a.get("name", "") for a in d.get("authors", [])]
    ref_ids = [r.get("paperId", "") for r in d.get("references", []) if r.get("paperId")]
    return S2Paper(
        paper_id=d.get("paperId", ""),
        title=d.get("title", ""),
        abstract=d.get("abstract", "") or "",
        year=d.get("year"),
        venue=d.get("venue", ""),
        authors=authors,
        citation_count=d.get("citationCount", 0),
        reference_ids=ref_ids,
        fields_of_study=d.get("fieldsOfStudy") or [],
        raw=d,
    )


# ======================================================================
# LLM-based structured extraction
# ======================================================================

EXTRACTION_PROMPT = """You are a research paper analyst. Given a paper's title and abstract,
extract structured information for a research benchmark dataset.

Paper title: {title}
Year: {year}
Abstract: {abstract}

Extract the following fields as JSON:
{{
  "background": "1-3 sentences describing the problem and limitations of prior work",
  "mechanism": "2-4 sentences describing the core technical mechanism/contribution. Include key architectural details, formulas in plain text if important.",
  "experiment": "1-3 sentences describing the main experimental setup, datasets, metrics, and ablation studies",
  "results_metric_main": <float, normalized to 0-1 range, representing the main performance metric>,
  "results_delta_vs_prev": <float, approximate improvement over the best prior work, as a fraction>,
  "keywords": ["keyword1", "keyword2", ...],  // 5-8 key technical terms that are distinctive to this paper
  "phase": "early|mid|late"  // early=foundational, mid=incremental improvements, late=paradigm shifts or mature
}}

IMPORTANT:
- For results_metric_main: normalize accuracy to 0-1, error rate should be 1-error_rate. If exact numbers aren't in the abstract, estimate based on your knowledge.
- For keywords: pick terms that would identify this specific paper or approach if seen. Include model names, technique names, dataset names.
- Be factual and precise. Do not hallucinate details not supported by the abstract.

Output ONLY the JSON object, no other text."""


def extract_record_with_llm(
    s2_paper: S2Paper,
    llm: LLMClient,
    local_id: str,
    dependencies: List[str],
) -> Optional[PaperRecord]:
    """Use LLM to extract a PaperRecord from Semantic Scholar metadata."""

    prompt = EXTRACTION_PROMPT.format(
        title=s2_paper.title,
        year=s2_paper.year or "unknown",
        abstract=s2_paper.abstract[:2000],
    )

    resp = llm.chat(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1024,
    )

    try:
        text = resp.content.strip()
        # Handle markdown code blocks
        if "```" in text:
            start = text.index("```") + 3
            if text[start:start + 4] == "json":
                start += 4
            end = text.index("```", start)
            text = text[start:end].strip()

        data = json.loads(text)

        return PaperRecord(
            paper_id=local_id,
            title=s2_paper.title,
            phase=data.get("phase", "mid"),
            background=data.get("background", ""),
            mechanism=data.get("mechanism", ""),
            experiment=data.get("experiment", ""),
            results=ExperimentResult(
                metric_main=float(data.get("results_metric_main", 0.0)),
                delta_vs_prev=float(data.get("results_delta_vs_prev", 0.0)),
            ),
            dependencies=dependencies,
            keywords=data.get("keywords", []),
            year=s2_paper.year,
            venue=s2_paper.venue,
            authors=[a for a in s2_paper.authors[:3]],  # keep top 3
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Failed to parse LLM output for '%s': %s", s2_paper.title, e)
        logger.debug("Raw LLM output: %s", resp.content[:500])
        return None


# ======================================================================
# Curated milestone lists
# ======================================================================

@dataclass
class MilestoneEntry:
    """One entry in a curated milestone list."""
    local_id: str              # e.g. "A_001"
    title: str                 # paper title for search
    s2_id: Optional[str]       # Semantic Scholar paper ID (if known)
    dependencies: List[str]    # local_ids of prerequisite papers
    phase: str = "mid"         # fallback phase if LLM fails


# Pre-curated Track A: Vision Representation Evolution (30 milestones)
TRACK_A_MILESTONES: List[MilestoneEntry] = [
    MilestoneEntry("A_001", "Gradient-based learning applied to document recognition", None, [], "early"),
    MilestoneEntry("A_002", "ImageNet Classification with Deep Convolutional Neural Networks", None, ["A_001"], "early"),
    MilestoneEntry("A_003", "Very Deep Convolutional Networks for Large-Scale Image Recognition", None, ["A_002"], "early"),
    MilestoneEntry("A_004", "Network In Network", None, ["A_002"], "early"),
    MilestoneEntry("A_005", "Going Deeper with Convolutions", None, ["A_003", "A_004"], "mid"),
    MilestoneEntry("A_006", "Batch Normalization: Accelerating Deep Network Training", None, ["A_005"], "mid"),
    MilestoneEntry("A_007", "Deep Residual Learning for Image Recognition", None, ["A_003", "A_006"], "mid"),
    MilestoneEntry("A_008", "Densely Connected Convolutional Networks", None, ["A_007"], "mid"),
    MilestoneEntry("A_009", "Squeeze-and-Excitation Networks", None, ["A_007"], "mid"),
    MilestoneEntry("A_010", "MobileNets: Efficient Convolutional Neural Networks for Mobile Vision Applications", None, ["A_007"], "mid"),
    MilestoneEntry("A_011", "Neural Architecture Search with Reinforcement Learning", None, ["A_007", "A_005"], "mid"),
    MilestoneEntry("A_012", "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks", None, ["A_011", "A_007"], "mid"),
    MilestoneEntry("A_013", "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale", None, ["A_007"], "late"),
    MilestoneEntry("A_014", "Training data-efficient image transformers & distillation through attention", None, ["A_013"], "late"),
    MilestoneEntry("A_015", "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows", None, ["A_013"], "late"),
    MilestoneEntry("A_016", "Masked Autoencoders Are Scalable Vision Learners", None, ["A_013"], "late"),
    MilestoneEntry("A_017", "Learning Transferable Visual Models From Natural Language Supervision", None, ["A_013"], "late"),
    MilestoneEntry("A_018", "A ConvNet for the 2020s", None, ["A_007", "A_015"], "late"),
    MilestoneEntry("A_019", "Scaling Vision Transformers to 22 Billion Parameters", None, ["A_013", "A_016"], "late"),
    MilestoneEntry("A_020", "Segment Anything", None, ["A_013", "A_017"], "late"),
    MilestoneEntry("A_021", "DINOv2: Learning Robust Visual Features without Supervision", None, ["A_016", "A_013"], "late"),
    MilestoneEntry("A_022", "Flamingo: a Visual Language Model for Few-Shot Learning", None, ["A_017", "A_019"], "late"),
    MilestoneEntry("A_023", "Deformable Convolutional Networks", None, ["A_007"], "mid"),
    MilestoneEntry("A_024", "Feature Pyramid Networks for Object Detection", None, ["A_007"], "mid"),
    MilestoneEntry("A_025", "Focal Loss for Dense Object Detection", None, ["A_024"], "mid"),
    MilestoneEntry("A_026", "DETR: End-to-End Object Detection with Transformers", None, ["A_013", "A_024"], "late"),
    MilestoneEntry("A_027", "Momentum Contrast for Unsupervised Visual Representation Learning", None, ["A_007"], "late"),
    MilestoneEntry("A_028", "A Simple Framework for Contrastive Learning of Visual Representations", None, ["A_027"], "late"),
    MilestoneEntry("A_029", "BYOL: Bootstrap Your Own Latent", None, ["A_028"], "late"),
    MilestoneEntry("A_030", "Emerging Properties in Self-Supervised Vision Transformers", None, ["A_013", "A_029"], "late"),
]

# Pre-curated Track B: Sequence Modeling Evolution (30 milestones)
TRACK_B_MILESTONES: List[MilestoneEntry] = [
    MilestoneEntry("B_001", "Long Short-Term Memory", None, [], "early"),
    MilestoneEntry("B_002", "Learning Phrase Representations using RNN Encoder-Decoder", None, ["B_001"], "early"),
    MilestoneEntry("B_003", "Sequence to Sequence Learning with Neural Networks", None, ["B_001"], "early"),
    MilestoneEntry("B_004", "Neural Machine Translation by Jointly Learning to Align and Translate", None, ["B_003"], "early"),
    MilestoneEntry("B_005", "Effective Approaches to Attention-based Neural Machine Translation", None, ["B_004"], "early"),
    MilestoneEntry("B_006", "Attention Is All You Need", None, ["B_004", "B_005"], "mid"),
    MilestoneEntry("B_007", "Improving Language Understanding by Generative Pre-Training", None, ["B_006"], "mid"),
    MilestoneEntry("B_008", "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", None, ["B_006"], "mid"),
    MilestoneEntry("B_009", "Language Models are Unsupervised Multitask Learners", None, ["B_007"], "mid"),
    MilestoneEntry("B_010", "RoBERTa: A Robustly Optimized BERT Pretraining Approach", None, ["B_008"], "mid"),
    MilestoneEntry("B_011", "ALBERT: A Lite BERT for Self-supervised Learning of Language Representations", None, ["B_008"], "mid"),
    MilestoneEntry("B_012", "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer", None, ["B_008"], "mid"),
    MilestoneEntry("B_013", "Language Models are Few-Shot Learners", None, ["B_009"], "late"),
    MilestoneEntry("B_014", "Switch Transformers: Scaling to Trillion Parameter Models", None, ["B_012", "B_013"], "late"),
    MilestoneEntry("B_015", "LoRA: Low-Rank Adaptation of Large Language Models", None, ["B_013"], "late"),
    MilestoneEntry("B_016", "Training language models to follow instructions with human feedback", None, ["B_013"], "late"),
    MilestoneEntry("B_017", "Constitutional AI: Harmlessness from AI Feedback", None, ["B_016"], "late"),
    MilestoneEntry("B_018", "LLaMA: Open and Efficient Foundation Language Models", None, ["B_013"], "late"),
    MilestoneEntry("B_019", "Scaling Data-Constrained Language Models", None, ["B_013", "B_018"], "late"),
    MilestoneEntry("B_020", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", None, ["B_008", "B_013"], "late"),
    MilestoneEntry("B_021", "Toolformer: Language Models Can Teach Themselves to Use Tools", None, ["B_013"], "late"),
    MilestoneEntry("B_022", "Mamba: Linear-Time Sequence Modeling with Selective State Spaces", None, ["B_006"], "late"),
    MilestoneEntry("B_023", "Efficiently Modeling Long Sequences with Structured State Spaces", None, ["B_006"], "late"),
    MilestoneEntry("B_024", "FlashAttention: Fast and Memory-Efficient Exact Attention", None, ["B_006"], "late"),
    MilestoneEntry("B_025", "Mixture of Experts Meets Instruction Tuning", None, ["B_014", "B_016"], "late"),
    MilestoneEntry("B_026", "Direct Preference Optimization: Your Language Model is Secretly a Reward Model", None, ["B_016"], "late"),
    MilestoneEntry("B_027", "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", None, ["B_013"], "late"),
    MilestoneEntry("B_028", "Tree of Thoughts: Deliberate Problem Solving with Large Language Models", None, ["B_027"], "late"),
    MilestoneEntry("B_029", "Self-Instruct: Aligning Language Models with Self-Generated Instructions", None, ["B_016"], "late"),
    MilestoneEntry("B_030", "Textbooks Are All You Need", None, ["B_018", "B_019"], "late"),
]


# ======================================================================
# Batch collection pipeline
# ======================================================================

def collect_track(
    milestones: List[MilestoneEntry],
    llm: LLMClient,
    output_path: Path,
    s2_api_key: Optional[str] = None,
    delay: float = 1.0,
) -> List[PaperRecord]:
    """Collect and extract records for a full track.

    Args:
        milestones: ordered list of milestone entries
        llm: LLM client for extraction
        output_path: where to save the draft JSONL
        s2_api_key: optional Semantic Scholar API key (higher rate limits)
        delay: seconds between API calls (rate limiting)

    Returns:
        list of PaperRecords (some may be partial if extraction failed)
    """
    records: List[PaperRecord] = []
    failed: List[str] = []

    for i, ms in enumerate(milestones):
        logger.info("[%d/%d] Processing: %s", i + 1, len(milestones), ms.title)

        # Step 1: Fetch from Semantic Scholar
        s2_paper = None
        if ms.s2_id:
            s2_paper = fetch_paper_by_id(ms.s2_id, s2_api_key)
        if s2_paper is None:
            s2_paper = search_paper_by_title(ms.title, s2_api_key)

        if s2_paper is None or not s2_paper.abstract:
            logger.warning("  Could not fetch paper or no abstract: %s", ms.title)
            # Create a minimal placeholder
            records.append(PaperRecord(
                paper_id=ms.local_id,
                title=ms.title,
                phase=ms.phase,
                background="[TODO: fill manually]",
                mechanism="[TODO: fill manually]",
                experiment="[TODO: fill manually]",
                results=ExperimentResult(metric_main=0.0, delta_vs_prev=0.0),
                dependencies=ms.dependencies,
                keywords=[],
            ))
            failed.append(ms.local_id)
            time.sleep(delay)
            continue

        logger.info("  Fetched: %s (%d)", s2_paper.title, s2_paper.year or 0)

        # Step 2: LLM extraction
        record = extract_record_with_llm(s2_paper, llm, ms.local_id, ms.dependencies)

        if record is None:
            logger.warning("  LLM extraction failed for %s", ms.title)
            records.append(PaperRecord(
                paper_id=ms.local_id,
                title=s2_paper.title,
                phase=ms.phase,
                background=s2_paper.abstract[:300],
                mechanism="[TODO: fill manually]",
                experiment="[TODO: fill manually]",
                results=ExperimentResult(metric_main=0.0, delta_vs_prev=0.0),
                dependencies=ms.dependencies,
                keywords=[],
                year=s2_paper.year,
                venue=s2_paper.venue,
                authors=s2_paper.authors[:3],
            ))
            failed.append(ms.local_id)
        else:
            records.append(record)
            logger.info("  Extracted OK: phase=%s, %d keywords",
                         record.phase, len(record.keywords))

        time.sleep(delay)

    # Save draft
    save_records(records, output_path)
    logger.info("Saved %d records to %s (%d need manual review)",
                 len(records), output_path, len(failed))

    if failed:
        logger.warning("Papers needing manual attention: %s", failed)

    return records


# ======================================================================
# Review / validation helpers
# ======================================================================

def validate_records(records: List[PaperRecord]) -> List[str]:
    """Check for common issues in collected records."""
    issues = []
    id_set = {r.paper_id for r in records}

    for r in records:
        # Check for placeholder text
        if "[TODO" in r.background or "[TODO" in r.mechanism:
            issues.append(f"{r.paper_id}: has TODO placeholders")

        # Check dependencies reference valid IDs
        for dep in r.dependencies:
            if dep not in id_set:
                issues.append(f"{r.paper_id}: dependency {dep} not in dataset")

        # Check keywords exist
        if len(r.keywords) < 3:
            issues.append(f"{r.paper_id}: fewer than 3 keywords ({len(r.keywords)})")

        # Check results are reasonable
        if r.results.metric_main == 0.0:
            issues.append(f"{r.paper_id}: metric_main is 0.0 (likely placeholder)")

        # Check phase
        if r.phase not in ("early", "mid", "late"):
            issues.append(f"{r.paper_id}: invalid phase '{r.phase}'")

    return issues
