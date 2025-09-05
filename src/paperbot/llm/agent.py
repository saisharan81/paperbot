from __future__ import annotations

"""
LLM client stub for bounded JSON decisions (future).

Not used in Phase 2; present to establish structure and tests can import it if
needed. Implementations should enforce strict JSON parsing.
"""

from typing import Any, Dict


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}

    def decide(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Return a bounded JSON decision. Stub returns a no-op decision.

        Example schema (future): {"side": "flat", "confidence": 0.0, "reason": "stub"}
        """
        return {"side": "flat", "confidence": 0.0, "reason": "stub"}

