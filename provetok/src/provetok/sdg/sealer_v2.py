"""SDG pipeline for PaperRecordV2 (plan.md-aligned records).

Unlike the legacy SDG (which operates on `PaperRecord`), this pipeline focuses
on sealing the publishable v2 schema.
"""

from __future__ import annotations

import copy
import random
import re
from dataclasses import asdict
from typing import Dict, List, Optional

from provetok.data.schema_v2 import FormulaGraph, PaperRecordV2, Results
from provetok.sdg.codebook import Codebook


class SDGPipelineV2:
    def __init__(
        self,
        *,
        seed: int = 42,
        enable_l1: bool = True,
        enable_l2: bool = True,
        enable_l3: bool = True,
    ):
        self.seed = seed
        self.codebook = Codebook(seed=seed)
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2
        self.enable_l3 = enable_l3
        self._rng = random.Random(seed)

    def seal_record(self, record: PaperRecordV2, lexical_terms: Optional[List[str]] = None) -> PaperRecordV2:
        rec = copy.deepcopy(record)
        terms = [t for t in (lexical_terms or []) if t]

        if self.enable_l1 and terms:
            sealed = self.codebook.seal_terms(terms, category="keyword")
            term_map = dict(zip(terms, sealed))
            rec.background = _replace_terms(rec.background, term_map)

        if self.enable_l2:
            rec.formula_graph = _seal_formula_graph(rec.formula_graph)

        if self.enable_l3:
            rec.results = _seal_results(rec.results, self._rng)

        return rec


def _replace_terms(text: str, term_map: Dict[str, str]) -> str:
    out = text
    for real, pseudo in term_map.items():
        pat = re.compile(re.escape(real), re.IGNORECASE)
        out = pat.sub(pseudo, out)
    return out


def _seal_formula_graph(fg: FormulaGraph) -> FormulaGraph:
    # MVP: no-op for empty graphs, minimal renaming hook for future.
    return fg


def _seal_results(res: Results, rng: random.Random) -> Results:
    # MVP: keep rank stable; jitter delta bucket slightly but preserve bounds.
    out = copy.deepcopy(res)
    if isinstance(out.delta_over_baseline_bucket, int):
        if rng.random() < 0.2:
            out.delta_over_baseline_bucket = int(max(-3, min(3, out.delta_over_baseline_bucket + rng.choice([-1, 1]))))
    return out

