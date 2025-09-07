from __future__ import annotations

from typing import Dict, Any


class LLMClient:
    def generate_decision(self, features: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

