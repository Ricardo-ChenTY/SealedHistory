"""Unified LLM client supporting OpenAI-compatible APIs (DeepSeek, vLLM, etc.).

Follows MLE-bench pattern: abstract the model backend behind a simple interface
so benchmark code doesn't depend on a specific provider.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for an OpenAI-compatible LLM endpoint."""
    model: str = "deepseek-chat"
    api_base: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Allow env-var override
        if not self.api_key:
            self.api_key = os.environ.get("LLM_API_KEY", "")
        if not self.api_base:
            self.api_base = os.environ.get("LLM_API_BASE", self.api_base)


@dataclass
class LLMResponse:
    content: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Optional[Dict] = None


class LLMClient:
    """Thin wrapper around OpenAI-compatible chat completion endpoints.

    Supports: DeepSeek, OpenAI, local vLLM / Ollama (any /v1/chat/completions).
    Falls back to a dummy mode when no API key is set.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key or "dummy",
                base_url=self.config.api_base,
                timeout=self.config.timeout,
            )
        except ImportError:
            logger.warning("openai package not installed; using dummy mode")
            self._client = None

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: list of {"role": ..., "content": ...}
            temperature: override config temperature
            max_tokens: override config max_tokens

        Returns:
            LLMResponse with content and usage info.
        """
        self._ensure_client()

        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **self.config.extra_params,
            **kwargs,
        }

        if self._client is None or not self.config.api_key:
            return self._dummy_response(messages)

        try:
            resp = self._client.chat.completions.create(**params)
            choice = resp.choices[0]
            usage = {}
            if resp.usage:
                usage = {
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                    "total_tokens": resp.usage.total_tokens,
                }
            return LLMResponse(
                content=choice.message.content or "",
                usage=usage,
                raw=resp.model_dump() if hasattr(resp, "model_dump") else None,
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return self._dummy_response(messages)

    def _dummy_response(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Return a placeholder when no real LLM is available."""
        logger.info("Using dummy LLM response (no API key or client)")
        return LLMResponse(
            content="[DUMMY] This is a placeholder response. Configure LLM_API_KEY to use a real model.",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    def structured_chat(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        **kwargs,
    ) -> LLMResponse:
        """Chat with optional JSON response format.

        For models supporting response_format (DeepSeek, GPT-4o, etc.).
        """
        extra = {}
        if response_format:
            extra["response_format"] = response_format
        return self.chat(messages, **extra, **kwargs)

    def is_configured(self) -> bool:
        """Return True if a real client + API key are available.

        This is stricter than "API key is set": it also checks that the OpenAI
        client dependency is importable.
        """
        self._ensure_client()
        return self._client is not None and bool(self.config.api_key)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client_from_dict(cfg: Dict[str, Any]) -> LLMClient:
    """Create LLMClient from a config dict (e.g. loaded from YAML)."""
    return LLMClient(LLMConfig(**{
        k: v for k, v in cfg.items() if k in LLMConfig.__dataclass_fields__
    }))
