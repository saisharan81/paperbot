from __future__ import annotations

from typing import Dict, Any, List
from .contracts import Decision


def input_sanitize(features: Dict[str, Any], allowlist: List[str]) -> Dict[str, Any]:
    return {k: features[k] for k in features.keys() if k in allowlist}


def output_validate(dec: Dict[str, Any], allow_symbols: List[str], market: str, symbol: str, confidence_floor: float) -> Decision:
    d = Decision(**dec)
    if d.symbol not in allow_symbols:
        raise ValueError("symbol not allowed")
    if d.market != market or d.symbol != symbol:
        raise ValueError("market/symbol mismatch")
    if d.confidence < confidence_floor:
        raise ValueError("confidence below floor")
    return d

