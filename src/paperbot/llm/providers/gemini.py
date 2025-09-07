from __future__ import annotations

import os
import time
from typing import Dict, Any
from ..client import LLMClient


class GeminiClient(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.cfg = config or {}

    def generate_decision(self, features: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # For offline/demo/testing: return a fast stub decision based on features
        symbol = context.get("symbol", "?")
        market = context.get("market", "crypto")
        run_id = context.get("run_id", str(int(time.time()*1000)))
        # simple heuristic
        side = "buy" if float(features.get("rsi14", 50)) >= 55 else "flat"
        conf = 0.7 if side == "buy" else 0.6
        return {
            "run_id": run_id,
            "ts": int(time.time()*1000),
            "market": market,
            "symbol": symbol,
            "side": side,
            "size": 0.0,
            "max_notional_usd": float(context.get("max_notional_usd", 200.0)),
            "confidence": conf,
            "reason": ["gemini-stub"],
            "ttl_s": 30,
            "features_used": [k for k in ("rsi14","cci20","stochrsi_k","mfi14") if k in features],
            "signals_used": [],
            "risk_context": "demo",
            "flow_evidence": "llm-advisory-stub",
            "gates_passed": [],
            "gates_failed": [],
            "outcome": "proposed",
            "slippage_model": context.get("slippage_model", ""),
            "profile": context.get("profile", ""),
        }

