from __future__ import annotations

"""
StrategyRunner dispatches feature rows to strategies and tracks metrics.
"""

from typing import Any, Dict, List, Optional
from .base import Strategy, Signal
import os
from ..logs.decision_log import append_jsonl
from ..events.schema import OrderIntent, EventEnvelope
from ..events.bus import publish as publish_event
try:
    from ..metrics.exec import (
        inc_pattern_detected,
        inc_pattern_intent,
        observe_pattern_to_intent_latency,
    )
except Exception:  # pragma: no cover
    # Metrics optional during tests or constrained envs
    inc_pattern_detected = inc_pattern_intent = observe_pattern_to_intent_latency = None  # type: ignore

try:
    from ..logs.decision_log import log_pattern_event
except Exception:  # pragma: no cover
    log_pattern_event = None  # type: ignore

try:
    from prometheus_client import Counter
except Exception:  # pragma: no cover - metrics optional in tests
    Counter = None  # type: ignore


class StrategyRunner:
    def __init__(
        self,
        strategies: List[Strategy],
        signals_counter: Optional["Counter"] = None,
        suppressed_counter: Optional["Counter"] = None,
    ):
        self.strategies = strategies
        self.signals_counter = signals_counter
        self.suppressed_counter = suppressed_counter
        # Bind optional suppressed counter into strategies that support it
        for strat in self.strategies:
            if hasattr(strat, "bind_metrics"):
                try:
                    strat.bind_metrics(self.suppressed_counter)
                except Exception:
                    pass

    def on_feature_row(self, row: Dict[str, Any]) -> List[Signal]:
        signals: List[Signal] = []
        for strat in self.strategies:
            out = strat.on_bar(row)
            if out is not None:
                signals.append(out)
                if self.signals_counter is not None:
                    try:
                        self.signals_counter.labels(strat=out.strategy, side=out.side, symbol=out.symbol).inc()
                    except Exception:
                        # Ignore metrics failures in tests
                        pass
                # Decision log record (v2 groundwork)
                try:
                    market = os.getenv("APP_TRACK", "crypto")
                    rec = {
                        "ts": int(row.get("timestamp", out.ts)),
                        "symbol": out.symbol,
                        "market": market,
                        "strategy": out.strategy,
                        "action": out.side,
                        "confidence": float(out.strength),
                        "features_used": [k for k in ("rsi14","z_vwap","atr14") if k in row],
                        "signals_used": [out.strategy],
                        "risk_context": "n/a",
                        "flow_evidence": "runner:on_bar",
                        "gates_passed": [],
                        "gates_failed": [],
                        "outcome": "emitted",
                    }
                    path = os.getenv("DECISION_LOG_PATH", "data/decisions/phase2.jsonl")
                    append_jsonl(path, rec)
                except Exception:
                    pass
                # Emit an order_intent event (minimal) for strong signals
                try:
                    intent = OrderIntent(
                        ts=int(row.get("timestamp", out.ts)),
                        market=os.getenv("APP_TRACK", "crypto"),
                        symbol=out.symbol,
                        strategy=out.strategy,
                        side=out.side,
                        confidence=float(out.strength),
                        notional_usd=float(row.get("price", row.get("close", 0.0))) * 1.0,
                    )
                    env = EventEnvelope(correlation_id=out.symbol + ":" + out.strategy, event=intent)
                    publish_event(env)
                except Exception:
                    pass
        return signals


# ---- Phase 2.5: Pattern observability helpers ----

def record_pattern_detected(market: str, symbol: str, pattern: str, rsi: float, ts: int) -> None:
    """Increment detection counter and emit structured log."""
    try:
        if inc_pattern_detected is not None:
            inc_pattern_detected(market, symbol, pattern)
    except Exception:
        pass
    try:
        if log_pattern_event is not None:
            log_pattern_event("pattern_detected", market, symbol, pattern, rsi=rsi, ts=ts)
    except Exception:
        pass


def record_pattern_intent(
    market: str,
    symbol: str,
    pattern: str,
    side: str,
    ts_detected: int,
    ts_intent: int,
) -> None:
    """Increment intent counter, observe latency, and emit structured log."""
    try:
        if inc_pattern_intent is not None:
            inc_pattern_intent(market, pattern, side)
    except Exception:
        pass
    try:
        latency_s = max(0.0, (ts_intent - ts_detected) / 1000.0)
        if observe_pattern_to_intent_latency is not None:
            observe_pattern_to_intent_latency(latency_s)
    except Exception:
        pass
    try:
        if log_pattern_event is not None:
            log_pattern_event(
                "pattern_intent",
                market,
                symbol,
                pattern,
                side=side,
                ts=ts_intent,
                extra={"ts_detected": ts_detected},
            )
    except Exception:
        pass
