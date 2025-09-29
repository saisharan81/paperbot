from __future__ import annotations

from typing import Dict, Any, List
import json
import logging

from .contracts import Decision
logger = logging.getLogger(__name__)


class GuardrailError(ValueError):
    """Raised when an LLM decision violates guardrails."""
    pass


def input_sanitize(features: Dict[str, Any], allowlist: List[str]) -> Dict[str, Any]:
    return {k: features[k] for k in features.keys() if k in allowlist}


def output_validate(
    dec: Dict[str, Any],
    allow_symbols: List[str],
    market: str,
    symbol: str,
    confidence_floor: float,
    max_notional_usd: float,
) -> Decision:
    d = Decision(**dec)
    if d.symbol not in allow_symbols:
        raise ValueError("symbol not allowed")
    if d.market != market or d.symbol != symbol:
        raise ValueError("market/symbol mismatch")
    if d.confidence < confidence_floor:
        raise ValueError("confidence below floor")

    allowed_notional = float(max_notional_usd or d.max_notional_usd)
    limit = allowed_notional if allowed_notional > 0 else float(d.max_notional_usd)

    reported_notional, price_source, price_used = _resolve_notional(dec, d.size)
    if reported_notional > limit:
        payload = {
            "event": "llm_guard_denied",
            "reason": "max_notional_exceeded",
            "symbol": d.symbol,
            "market": d.market,
            "size": d.size,
            "notional_usd": reported_notional,
            "max_notional_usd": limit,
            "price_source": price_source,
            "price_used": price_used,
        }
        try:
            logger.error(json.dumps(payload))
        except Exception:
            logger.error("llm_guard_denied", extra=payload)
        raise GuardrailError("decision exceeds max_notional_usd")
    return d


def _resolve_notional(dec: Dict[str, Any], size: float) -> tuple[float, str, float]:
    """Return the USD notional implied by size along with metadata."""

    try:
        base_size = abs(float(size))
    except (TypeError, ValueError):
        base_size = 0.0

    override = dec.get("notional_usd")
    if override is not None:
        try:
            value = abs(float(override))
            price = value / base_size if base_size > 0 else 0.0
            return value, "notional_usd", price
        except (TypeError, ValueError):
            pass

    price_fields = (
        "quote_price",
        "price",
        "reference_price",
        "mark_price",
        "mid_price",
        "close",
    )
    for field in price_fields:
        if field not in dec:
            continue
        try:
            price_val = float(dec[field])
        except (TypeError, ValueError):
            continue
        if price_val > 0:
            return base_size * price_val, field, price_val

    return base_size, "size_only", 1.0 if base_size > 0 else 0.0
