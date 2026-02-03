"""Codebook: deterministic pseudotoken mapping for lexical sealing (L1).

Given a seed, generates reproducible fake tokens for real terms,
ensuring the mapping is bijective and consistent across a session.
"""

from __future__ import annotations

import hashlib
import json
import random
import string
from pathlib import Path
from typing import Dict, List, Optional, Set


# Prefix pools per category – easy to extend
_CATEGORY_PREFIXES = {
    "model":      ["ZetaNet", "OmegaArch", "KappaModel", "SigmaBlock", "PhiStack",
                   "ThetaCore", "LambdaUnit", "DeltaFrame", "EpsilonNode", "RhoNet"],
    "dataset":    ["SynthBench", "PixelCorpus", "AuroraSuite", "NovaBatch", "QuantumSet",
                   "PrismData", "VortexBench", "NebulaSplit", "CoralSet", "TidalData"],
    "metric":     ["score_alpha", "index_beta", "ratio_gamma", "perf_delta", "val_epsilon",
                   "rate_zeta", "coeff_eta", "measure_theta", "stat_iota", "idx_kappa"],
    "technique":  ["CrossFold", "DualPath", "TriGate", "QuadMix", "PentaFuse",
                   "HexaLink", "SeptaPool", "OctaShift", "NonaBlend", "DecaSplit"],
    "venue":      ["AICONF", "VISIONEX", "LEARNCON", "NEUROSYM", "DATAFORGE",
                   "SIGNALX", "OPTICON", "COGNITA", "COMPULEARN", "DEEPEX"],
    "author":     ["J. Smith", "R. Chen", "M. Ivanova", "K. Tanaka", "S. Patel",
                   "L. Garcia", "A. Johansson", "D. Kowalski", "W. Okafor", "P. Dubois"],
    "keyword":    ["quark", "prism", "nexus", "vertex", "helix",
                   "lattice", "matrix", "tensor", "vector", "kernel"],
    "generic":    ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON",
                   "ZETA", "ETA", "THETA", "IOTA", "KAPPA"],
}


class Codebook:
    """Deterministic term -> pseudotoken mapping."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)
        self._forward: Dict[str, str] = {}   # real -> pseudo
        self._reverse: Dict[str, str] = {}   # pseudo -> real
        self._category_counters: Dict[str, int] = {}

    # ------------------------------------------------------------------
    def _next_pseudo(self, category: str) -> str:
        """Generate the next pseudotoken for *category*."""
        prefixes = _CATEGORY_PREFIXES.get(category, _CATEGORY_PREFIXES["generic"])
        idx = self._category_counters.get(category, 0)
        self._category_counters[category] = idx + 1

        prefix = prefixes[idx % len(prefixes)]
        suffix = idx // len(prefixes)
        if suffix == 0:
            return prefix
        return f"{prefix}_{suffix}"

    # ------------------------------------------------------------------
    def seal_term(self, term: str, category: str = "generic") -> str:
        """Map *term* to a pseudotoken (idempotent)."""
        key = term.lower().strip()
        if key in self._forward:
            return self._forward[key]
        pseudo = self._next_pseudo(category)
        self._forward[key] = pseudo
        self._reverse[pseudo] = key
        return pseudo

    def seal_terms(self, terms: List[str], category: str = "generic") -> List[str]:
        return [self.seal_term(t, category) for t in terms]

    # ------------------------------------------------------------------
    # Convenience: batch-seal a list of keywords
    def seal_keywords(self, keywords: List[str]) -> List[str]:
        return self.seal_terms(keywords, "keyword")

    # ------------------------------------------------------------------
    def lookup(self, term: str) -> Optional[str]:
        return self._forward.get(term.lower().strip())

    def reverse_lookup(self, pseudo: str) -> Optional[str]:
        return self._reverse.get(pseudo)

    # ------------------------------------------------------------------
    # Persistence
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seed": self.seed,
            "forward": self._forward,
            "category_counters": self._category_counters,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Codebook":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cb = cls(seed=data["seed"])
        cb._forward = data["forward"]
        cb._reverse = {v: k for k, v in cb._forward.items()}
        cb._category_counters = data.get("category_counters", {})
        return cb
