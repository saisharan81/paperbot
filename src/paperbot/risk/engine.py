from __future__ import annotations

from typing import Any, Dict, Optional
from ..metrics.exec import get_orders_blocked_total, get_killswitch_trips_total
from ..strategies.base import Signal
from ..exec.model import Order, new_id


class RiskEngine:
    def __init__(self, config: Dict[str, Any], equity_start: float):
        cfg = config or {}
        self.risk_frac = float(cfg.get("risk_frac", 0.0025))
        self.atr_stop_mult = float(cfg.get("atr_stop_mult", 1.5))
        self.atr_tp_mult = float(cfg.get("atr_tp_mult", 1.0))
        self.daily_loss_cap_pct = float(cfg.get("daily_loss_cap_pct", 0.01))
        self.max_positions = int(cfg.get("max_positions", 3))
        self.max_position_value_per_symbol = float(cfg.get("max_position_value_per_symbol", 0.2))
        self.equity_start_of_day = float(equity_start)
        self.killswitch_on = False
        self.open_positions: Dict[str, bool] = {}
        # Metrics
        self.orders_blocked = get_orders_blocked_total()
        self.killswitch_trips = get_killswitch_trips_total()

    def on_realized_pnl(self, equity: float) -> None:
        if equity <= self.equity_start_of_day * (1.0 - self.daily_loss_cap_pct):
            if not self.killswitch_on:
                self.killswitch_on = True
                self.killswitch_trips.inc()

    def approve(self, signal: Signal, features: Dict[str, Any], equity: float) -> Optional[Order]:
        if self.killswitch_on:
            self.orders_blocked.labels("killswitch", signal.symbol).inc()
            return None

        symbol = signal.symbol
        side = signal.side
        price = float(features.get("price", 0.0)) or float(features.get("close", 0.0))
        atr14 = float(features.get("atr14", 0.0))
        ts = int(features.get("timestamp", signal.ts))

        # Manage max positions
        open_count = sum(1 for v in self.open_positions.values() if v)
        if side in ("long", "short") and open_count >= self.max_positions and not self.open_positions.get(symbol, False):
            self.orders_blocked.labels("max_positions", symbol).inc()
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
            return None
        # Enforce per-symbol notional cap
        if equity > 0:
            notional_frac = abs(qty * price) / equity if price > 0 else 1.0
            if notional_frac > self.max_position_value_per_symbol:
                self.orders_blocked.labels("symbol_value_cap", symbol).inc()
                return None

        order_side = "buy" if side == "long" else "sell"
        self.open_positions[symbol] = True
        return Order(
            id=new_id(), ts=ts, symbol=symbol, side=order_side, type="market",
            qty=float(qty), price=None, strategy=signal.strategy, reason=signal.reason, params=signal.params,
        )
