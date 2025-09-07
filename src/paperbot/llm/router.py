from __future__ import annotations

import yaml
from typing import Any, Dict
from .providers.gemini import GeminiClient
from .providers.local_openai import LocalOpenAIClient


def load_llm_config(path: str = "config/llm.yaml") -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def get_client(cfg: Dict[str, Any]):
    provider = (cfg.get("provider") or "gemini").lower()
    if provider == "gemini":
        return GeminiClient(cfg)
    if provider == "local_openai":
        return LocalOpenAIClient(cfg.get("local_openai", {}))
    return GeminiClient(cfg)

