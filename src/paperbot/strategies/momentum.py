from __future__ import annotations

"""
Momentum strategy: long-only using RSI bands with optional confirmation bars.
"""

from typing import Any, Dict, Optional
from .base import Strategy, Signal


class MomentumStrategy(Strategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(name="momentum", config=config)
        self.enter_long = float(config.get("enter_long_if_rsi_at_least", 60))
        self.exit_long = float(config.get("exit_long_if_rsi_at_most", 50))
        self.confirm_bars = int(config.get("confirm_bars", 0))
        self._state: Dict[str, str] = {}
        self._confirm: Dict[str, int] = {}
        self._suppressed_counter = None

    def bind_metrics(self, suppressed_counter):
        """Optionally bind a Prometheus counter for suppressed signals."""
        self._suppressed_counter = suppressed_counter

    def _inc_confirm(self, symbol: str) -> int:
        self._confirm[symbol] = self._confirm.get(symbol, 0) + 1
        return self._confirm[symbol]

    def _reset_confirm(self, symbol: str) -> None:
        self._confirm[symbol] = 0

    def on_bar(self, features: Dict[str, Any]) -> Optional[Signal]:
        symbol = str(features.get("symbol", ""))
        ts = int(features.get("timestamp", 0))
        rsi = float(features.get("rsi14", 50.0))
        state = self._state.get(symbol, "flat")

        params = {
            "enter_long_if_rsi_at_least": self.enter_long,
            "exit_long_if_rsi_at_most": self.exit_long,
            "confirm_bars": self.confirm_bars,
        }

        # Enter long from flat
        if state == "flat":
            if rsi >= self.enter_long:
                if self.confirm_bars > 0:
                    cnt = self._inc_confirm(symbol)
                    if cnt < self.confirm_bars:
                        if self._suppressed_counter is not None:
                            try:
                                self._suppressed_counter.labels(strat=self.name, reason="debounce").inc()
                            except Exception:
                                pass
                        return None
                # confirmed
                self._reset_confirm(symbol)
                self._state[symbol] = "long"
                denom = max(1.0, (self.enter_long - self.exit_long))
                strength = max(0.0, min(1.0, (rsi - self.exit_long) / denom))
                return Signal(ts=ts, symbol=symbol, strategy=self.name, side="long",
                              strength=strength, reason=f"enter_long:rsi>={self.enter_long}",
                              params=params)
            else:
                self._reset_confirm(symbol)

        # Exit to flat from long
        if state == "long":
            if rsi <= self.exit_long:
                if self.confirm_bars > 0:
                    cnt = self._inc_confirm(symbol)
                    if cnt < self.confirm_bars:
                        if self._suppressed_counter is not None:
                            try:
                                self._suppressed_counter.labels(strat=self.name, reason="debounce").inc()
                            except Exception:
                                pass
                        return None
                self._reset_confirm(symbol)
                self._state[symbol] = "flat"
                return Signal(ts=ts, symbol=symbol, strategy=self.name, side="flat",
                              strength=1.0, reason=f"exit_long:rsi<={self.exit_long}",
                              params=params)
            else:
                self._reset_confirm(symbol)

        return None
