"""Sealed Domain Generator (SDG): three-layer sealing pipeline.

L1 – Lexical Sealing   : replace identifiable terms with codebook pseudotokens.
L2 – Structural Sealing: rewrite mechanism / formula descriptions.
L3 – Numeric Sealing   : bin / perturb absolute numbers while preserving order.
"""

from __future__ import annotations

import copy
import math
import random
import re
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from provetok.data.schema import ExperimentResult, PaperRecord
from provetok.sdg.codebook import Codebook


# ======================================================================
# L1 – Lexical Sealing
# ======================================================================

class LexicalSealer:
    """Replace keywords, authors, venues, titles with codebook pseudotokens."""

    def __init__(self, codebook: Codebook):
        self.cb = codebook

    def seal(self, record: PaperRecord) -> PaperRecord:
        rec = copy.deepcopy(record)

        # 1. Seal keywords and build replacement map for text fields
        sealed_kw = self.cb.seal_keywords(rec.keywords)
        kw_map = dict(zip(rec.keywords, sealed_kw))
        rec.keywords = sealed_kw

        # 2. Seal authors
        if rec.authors:
            rec.authors = self.cb.seal_terms(rec.authors, "author")

        # 3. Seal venue
        if rec.venue:
            rec.venue = self.cb.seal_term(rec.venue, "venue")

        # 4. Seal year -> remove
        rec.year = None

        # 5. Seal title
        rec.title = self.cb.seal_term(rec.title, "model")

        # 6. Replace known keywords in text fields
        for field in ("background", "mechanism", "experiment"):
            text = getattr(rec, field)
            for real, pseudo in kw_map.items():
                # case-insensitive replacement
                pattern = re.compile(re.escape(real), re.IGNORECASE)
                text = pattern.sub(pseudo, text)
            setattr(rec, field, text)

        return rec


# ======================================================================
# L2 – Structural Sealing
# ======================================================================

class StructuralSealer:
    """Rewrite mechanism descriptions to reduce formula-shape fingerprinting.

    MVP: template-based rewriting with symbol renaming.
    """

    _SYMBOL_MAP = {
        "x": "u", "y": "v", "z": "w",
        "W": "M", "b": "c", "h": "g",
        "F": "G", "H": "P", "f": "q",
    }

    _TEMPLATE_REWRITES = [
        # (pattern, replacement) – lightweight structural transforms
        (r"(\w+)\s*=\s*(\w+)\s*\+\s*(\w+)", r"\1 = \3 + \2"),          # commutative swap
        (r"learn(?:s|ed)?\s+residual", "optimise the difference"),     # paraphrase
        (r"skip\s+connection", "bypass pathway"),
        (r"shortcut\s+connection", "direct path"),
        (r"feed\s+through", "process via"),
        (r"stack(?:s|ed|ing)?\s+(\d+)", r"compose \1"),
        (r"concatenat(?:e|ed|ing)", "merge along channel axis"),
    ]

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def seal(self, record: PaperRecord) -> PaperRecord:
        rec = copy.deepcopy(record)

        # Symbol rename in mechanism
        rec.mechanism = self._rename_symbols(rec.mechanism)

        # Template rewrites in mechanism + experiment
        for field in ("mechanism", "experiment"):
            text = getattr(rec, field)
            text = self._apply_templates(text)
            setattr(rec, field, text)

        return rec

    def _rename_symbols(self, text: str) -> str:
        for old, new in self._SYMBOL_MAP.items():
            # only replace standalone symbols (word boundaries)
            text = re.sub(rf"\b{re.escape(old)}\b", new, text)
        return text

    def _apply_templates(self, text: str) -> str:
        for pat, repl in self._TEMPLATE_REWRITES:
            text = re.compile(pat, re.IGNORECASE).sub(repl, text)
        return text


# ======================================================================
# L3 – Numeric Sealing
# ======================================================================

class NumericSealer:
    """Bin / perturb absolute numbers while preserving ordinal relationships."""

    def __init__(self, n_bins: int = 10, seed: int = 42):
        self.n_bins = n_bins
        self._rng = random.Random(seed)

    def seal(self, record: PaperRecord) -> PaperRecord:
        rec = copy.deepcopy(record)
        rec.results = self._perturb_results(rec.results)
        # Perturb numeric literals in text fields
        for field in ("mechanism", "experiment"):
            text = getattr(rec, field)
            text = self._perturb_text_numbers(text)
            setattr(rec, field, text)
        return rec

    def _perturb_results(self, res: ExperimentResult) -> ExperimentResult:
        return ExperimentResult(
            metric_main=self._bin_value(res.metric_main),
            delta_vs_prev=self._bin_value(res.delta_vs_prev),
            extra={k: self._bin_value(v) for k, v in res.extra.items()},
        )

    def _bin_value(self, val: float) -> float:
        """Quantise to n_bins levels in [0, 1], add small noise."""
        if val == 0.0:
            return 0.0
        binned = round(val * self.n_bins) / self.n_bins
        noise = self._rng.uniform(-0.005, 0.005)
        return round(max(0.0, min(1.0, binned + noise)), 4)

    def _perturb_text_numbers(self, text: str) -> str:
        """Replace standalone integers in text with perturbed versions."""
        def _replace(m: re.Match) -> str:
            n = int(m.group())
            if n < 2:
                return m.group()
            # perturb by ±10-20%
            factor = self._rng.uniform(0.8, 1.2)
            return str(int(round(n * factor)))

        return re.sub(r"\b(\d{2,})\b", _replace, text)


# ======================================================================
# Pipeline
# ======================================================================

class SDGPipeline:
    """Full sealing pipeline: L1 -> L2 -> L3 (configurable)."""

    def __init__(
        self,
        seed: int = 42,
        enable_l1: bool = True,
        enable_l2: bool = True,
        enable_l3: bool = True,
        numeric_bins: int = 10,
    ):
        self.codebook = Codebook(seed=seed)
        self.l1 = LexicalSealer(self.codebook) if enable_l1 else None
        self.l2 = StructuralSealer(seed=seed) if enable_l2 else None
        self.l3 = NumericSealer(n_bins=numeric_bins, seed=seed) if enable_l3 else None

    def seal_record(self, record: PaperRecord) -> PaperRecord:
        rec = record
        if self.l1:
            rec = self.l1.seal(rec)
        if self.l2:
            rec = self.l2.seal(rec)
        if self.l3:
            rec = self.l3.seal(rec)
        return rec

    def seal_records(self, records: List[PaperRecord]) -> List[PaperRecord]:
        return [self.seal_record(r) for r in records]
