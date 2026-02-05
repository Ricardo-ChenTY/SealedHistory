"""Configuration loader with YAML support and CLI override."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class SDGConfig:
    enable_l1: bool = True
    enable_l2: bool = True
    enable_l3: bool = True
    numeric_bins: int = 10


@dataclass
class AuditConfig:
    run_term_recovery: bool = True
    run_phase_pred: bool = True
    run_next_milestone: bool = True
    run_order_bias: bool = True
    attacker_model: str = "dummy"   # "dummy" | "deepseek" | "openai" | "local"


@dataclass
class EnvConfig:
    budget: int = 30
    fast_mode: bool = True
    multi_agent: bool = False
    n_agents: int = 1


@dataclass
class LLMProviderConfig:
    model: str = "deepseek-chat"
    api_base: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class EvalConfig:
    rubric_weights: Dict[str, float] = field(default_factory=lambda: {
        "problem_shift": 1.0,
        "mechanism_class": 1.0,
        "dependency": 1.0,
        "claim_validity": 2.0,
        "ablation": 1.0,
        "clarity": 0.5,
    })


@dataclass
class ProjectConfig:
    """Top-level project configuration."""
    project: str = "provetok"
    seed: int = 42
    sdg: SDGConfig = field(default_factory=SDGConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
    llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)


def load_config(path: Optional[Path] = None) -> ProjectConfig:
    """Load config from YAML file, with defaults for missing fields."""
    cfg = ProjectConfig()

    if path is None or not path.exists():
        return cfg

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if "seed" in raw:
        cfg.seed = raw["seed"]
    if "project" in raw:
        cfg.project = raw["project"]

    # SDG
    if "sdg" in raw:
        for k, v in raw["sdg"].items():
            if hasattr(cfg.sdg, k):
                setattr(cfg.sdg, k, v)

    # Audit
    if "audit" in raw:
        for k, v in raw["audit"].items():
            if hasattr(cfg.audit, k):
                setattr(cfg.audit, k, v)

    # Env
    if "env" in raw:
        for k, v in raw["env"].items():
            if hasattr(cfg.env, k):
                setattr(cfg.env, k, v)

    # LLM
    if "llm" in raw:
        for k, v in raw["llm"].items():
            if hasattr(cfg.llm, k):
                setattr(cfg.llm, k, v)

    # Eval
    if "eval" in raw:
        if "rubric_weights" in raw["eval"]:
            cfg.eval.rubric_weights.update(raw["eval"]["rubric_weights"])

    return cfg
