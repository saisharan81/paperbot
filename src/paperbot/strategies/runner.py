from __future__ import annotations

"""
StrategyRunner dispatches feature rows to strategies and tracks metrics.
"""

from typing import Any, Dict, List, Optional
from .base import Strategy, Signal

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
        return signals
