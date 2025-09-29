from __future__ import annotations

from typing import Any, Dict, Optional
from ..metrics.exec import get_orders_blocked_total, get_killswitch_trips_total
from ..strategies.base import Signal
from ..exec.model import Order, new_id
from ..events.schema import EventEnvelope, RiskBlocked
from ..events.bus import publish as publish_event
from .killswitch import check_killswitch, set_killswitch_state as record_killswitch_state


class RiskEngine:
    def __init__(self, config: Dict[str, Any], equity_start: float, market: str = "crypto"):
        cfg = config or {}
        self.risk_frac = float(cfg.get("risk_frac", 0.0025))
        self.atr_stop_mult = float(cfg.get("atr_stop_mult", 1.5))
        self.atr_tp_mult = float(cfg.get("atr_tp_mult", 1.0))
        self.daily_loss_cap_pct = float(cfg.get("daily_loss_cap_pct", 0.01))
        self.max_positions = int(cfg.get("max_positions", 3))
        self.max_position_value_per_symbol = float(cfg.get("max_position_value_per_symbol", 0.2))
        self.equity_start_of_day = float(equity_start)
        self.market = market or "crypto"
        existing_state = check_killswitch(market)
        self.is_active = bool(existing_state)
        self.killswitch_on = self.is_active  # backwards-compatibility alias
        self.open_positions: Dict[str, bool] = {}
        # Metrics
        self.orders_blocked = get_orders_blocked_total()
        self.killswitch_trips = get_killswitch_trips_total()
        if not self.is_active:
            record_killswitch_state(self.market, False)

    def on_realized_pnl(self, equity: float) -> None:
        if equity <= self.equity_start_of_day * (1.0 - self.daily_loss_cap_pct):
            if not self.is_active:
                self.killswitch_trips.inc()
                self._set_killswitch(True)

    def approve(self, signal: Signal, features: Dict[str, Any], equity: float) -> Optional[Order]:
        ts = int(features.get("timestamp", signal.ts))
        market = self.market if not signal.symbol.isalpha() else "stocks"
        if self.is_active or check_killswitch(self.market):
            self.orders_blocked.labels("killswitch", signal.symbol).inc()
            try:
                evt = RiskBlocked(
                    ts=ts,
                    market=market,
                    symbol=signal.symbol,
                    strategy=signal.strategy,
                    side=signal.side,
                    reason="killswitch",
                )
                publish_event(EventEnvelope(correlation_id=signal.symbol+":"+signal.strategy, event=evt))
            except Exception:
                pass
            return None

        symbol = signal.symbol
        side = signal.side
        price = float(features.get("price", 0.0)) or float(features.get("close", 0.0))
        atr14 = float(features.get("atr14", 0.0))

        # Manage max positions
        open_count = sum(1 for v in self.open_positions.values() if v)
        if side in ("long", "short") and open_count >= self.max_positions and not self.open_positions.get(symbol, False):
            self.orders_blocked.labels("max_positions", symbol).inc()
            try:
                evt = RiskBlocked(
                    ts=ts,
                    market="crypto",
                    symbol=symbol,
                    strategy=signal.strategy,
                    side=signal.side,
                    reason="max_positions",
                )
                publish_event(EventEnvelope(correlation_id=symbol+":"+signal.strategy, event=evt))
            except Exception:
                pass
            return None

        # flat = exit if open
        if side == "flat":
            if self.open_positions.get(symbol, False):
                order_side = "sell" if features.get("position_side", "long") == "long" else "buy"
                return Order(
                    id=new_id(), ts=ts, symbol=symbol, side=order_side, type="market",
                    qty=abs(float(features.get("position_qty", 0.0))) or 0.0, price=None,
                    strategy=signal.strategy, reason=signal.reason, params=signal.params,
                )
            return None

        # Sizing for entries
        stop_dist = max(atr14 * self.atr_stop_mult, 1e-9)
        qty = (equity * self.risk_frac) / stop_dist
        if qty <= 0:
            self.orders_blocked.labels("qty_zero", symbol).inc()
            try:
                evt = RiskBlocked(ts=ts, market="crypto", symbol=symbol, strategy=signal.strategy, side=signal.side, reason="qty_zero")
                publish_event(EventEnvelope(correlation_id=symbol+":"+signal.strategy, event=evt))
            except Exception:
                pass
            return None
        # Enforce per-symbol notional cap
        if equity > 0:
            notional_frac = abs(qty * price) / equity if price > 0 else 1.0
            if notional_frac > self.max_position_value_per_symbol:
                self.orders_blocked.labels("symbol_value_cap", symbol).inc()
                try:
                    evt = RiskBlocked(ts=ts, market="crypto", symbol=symbol, strategy=signal.strategy, side=signal.side, reason="symbol_value_cap")
                    publish_event(EventEnvelope(correlation_id=symbol+":"+signal.strategy, event=evt))
                except Exception:
                    pass
                return None

        order_side = "buy" if side == "long" else "sell"
        self.open_positions[symbol] = True
        return Order(
            id=new_id(), ts=ts, symbol=symbol, side=order_side, type="market",
            qty=float(qty), price=None, strategy=signal.strategy, reason=signal.reason, params=signal.params,
        )

    def _set_killswitch(self, active: bool) -> None:
        self.is_active = bool(active)
        self.killswitch_on = self.is_active
        record_killswitch_state(self.market, self.is_active)

    def reset_killswitch(self) -> None:
        self._set_killswitch(False)
