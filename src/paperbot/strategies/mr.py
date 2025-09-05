from __future__ import annotations

"""
Mean Reversion strategy using z-score to session VWAP with hysteresis and a
realized-volatility gate.
"""

from typing import Any, Dict, Optional
from .base import Strategy, Signal


class MeanReversionStrategy(Strategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(name="mr", config=config)
        # Thresholds with defaults
        self.enter_long_if_below = float(config.get("enter_long_if_below", -1.5))
        self.exit_long_if_above = float(config.get("exit_long_if_above", -0.3))
        self.enter_short_if_above = float(config.get("enter_short_if_above", 1.5))
        self.exit_short_if_below = float(config.get("exit_short_if_below", 0.3))
        self.vol_gate_rv_30m_max = float(config.get("vol_gate_rv_30m_max", 0.03))
        # Per-symbol state: "long" | "short" | "flat"
        self._state: Dict[str, str] = {}
        self._suppressed_counter = None

    def bind_metrics(self, suppressed_counter):
        """Optionally bind a Prometheus counter for suppressed signals."""
        self._suppressed_counter = suppressed_counter

    def on_bar(self, features: Dict[str, Any]) -> Optional[Signal]:
        symbol = str(features.get("symbol", ""))
        ts = int(features.get("timestamp", 0))
        z_vwap = float(features.get("z_vwap", 0.0))
        rv_30m = float(features.get("rv_30m", 0.0))

        # Volatility gate: suppress entries when realized vol is too high
        if rv_30m >= self.vol_gate_rv_30m_max:
            if self._suppressed_counter is not None:
                try:
                    self._suppressed_counter.labels(strat=self.name, reason="vol_gate").inc()
                except Exception:
                    pass
            return None

        state = self._state.get(symbol, "flat")
        params = {
            "enter_long_if_below": self.enter_long_if_below,
            "exit_long_if_above": self.exit_long_if_above,
            "enter_short_if_above": self.enter_short_if_above,
            "exit_short_if_below": self.exit_short_if_below,
            "vol_gate_rv_30m_max": self.vol_gate_rv_30m_max,
        }

        # Entries from flat
        if state == "flat":
            if z_vwap <= self.enter_long_if_below:
                strength = min(1.0, abs(z_vwap) / 2.5)
                self._state[symbol] = "long"
                return Signal(ts=ts, symbol=symbol, strategy=self.name, side="long",
                              strength=strength, reason=f"enter_long:z<={self.enter_long_if_below}",
                              params=params)
            if z_vwap >= self.enter_short_if_above:
                strength = min(1.0, abs(z_vwap) / 2.5)
                self._state[symbol] = "short"
                return Signal(ts=ts, symbol=symbol, strategy=self.name, side="short",
                              strength=strength, reason=f"enter_short:z>={self.enter_short_if_above}",
                              params=params)

        # Exits via hysteresis
        if state == "long" and z_vwap >= self.exit_long_if_above:
            self._state[symbol] = "flat"
            return Signal(ts=ts, symbol=symbol, strategy=self.name, side="flat",
                          strength=1.0, reason=f"exit_long:z>={self.exit_long_if_above}",
                          params=params)

        if state == "short" and z_vwap <= self.exit_short_if_below:
            self._state[symbol] = "flat"
            return Signal(ts=ts, symbol=symbol, strategy=self.name, side="flat",
                          strength=1.0, reason=f"exit_short:z<={self.exit_short_if_below}",
                          params=params)

        return None
