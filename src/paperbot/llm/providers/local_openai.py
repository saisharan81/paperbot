from __future__ import annotations

from typing import Dict, Any
from ..client import LLMClient
import time


class LocalOpenAIClient(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config or {}

    def generate_decision(self, features: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get("symbol", "?")
        market = context.get("market", "crypto")
        run_id = context.get("run_id", str(int(time.time()*1000)))
        return {
            "run_id": run_id,
            "ts": int(time.time()*1000),
            "market": market,
            "symbol": symbol,
            "side": "flat",
            "size": 0.0,
            "max_notional_usd": float(context.get("max_notional_usd", 200.0)),
            "confidence": 0.6,
            "reason": ["local-openai-stub"],
            "ttl_s": 15,
            "features_used": list(features.keys())[:5],
            "signals_used": [],
            "risk_context": "demo",
            "flow_evidence": "llm-advisory-stub",
            "gates_passed": [],
            "gates_failed": [],
            "outcome": "proposed",
            "slippage_model": context.get("slippage_model", ""),
            "profile": context.get("profile", ""),
        }

