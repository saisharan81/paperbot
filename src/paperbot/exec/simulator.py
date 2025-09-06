from __future__ import annotations

from typing import Any, Dict, List
from .model import Order, Fill
import random
from ..metrics.exec import (
    get_orders_submitted_total,
    get_fills_total,
    get_fees_paid_total,
)


class ExecutionSimulator:
    def __init__(self, config: Dict[str, Any], profile: Dict[str, Any] | None = None):
        cfg = config or {}
        self.slippage_bps_market = float(cfg.get("slippage_bps_market", 3.0))
        self.taker_bps = float(cfg.get("taker_bps", 1.0))
        self.maker_bps = float(cfg.get("maker_bps", 0.5))
        # partial fills
        self.liquidity_fraction = float(cfg.get("liquidity_fraction", 0.25))
        # slippage model
        self.slippage_model = str(cfg.get("slippage_model", "fixed_bps"))
        rb = cfg.get("slippage_random_bps_range", [0, 3])
        try:
            self.random_bps_min = float(rb[0])
            self.random_bps_max = float(rb[1])
        except Exception:
            self.random_bps_min, self.random_bps_max = 0.0, 3.0
        self.atr_slip_mult = float(cfg.get("atr_slip_mult", 1.0))
        # exchange profile
        prof = profile or {}
        fees = prof.get("fees", {})
        self.maker_bps = float(fees.get("maker_bps", self.maker_bps))
        self.taker_bps = float(fees.get("taker_bps", self.taker_bps))
        self.min_notional = float(prof.get("min_notional", 0.0))
        self.tick_size = float(prof.get("tick_size", 0.01))
        self.step_size = float(prof.get("step_size", 0.0001))
        self.profile_slip_bps = float(prof.get("slippage_bps", self.slippage_bps_market))
        # state: remaining qty per order
        self._remaining: Dict[str, float] = {}
        # Metrics
        self.orders_submitted = get_orders_submitted_total()
        self.fills_total = get_fills_total()
        self.fees_paid = get_fees_paid_total()

    def submit(self, order: Order, candle: Dict[str, Any], features: Dict[str, Any] | None = None) -> List[Fill]:
        self.orders_submitted.labels(order.type, order.symbol).inc()
        fills: List[Fill] = []
        close = float(candle.get("close", 0.0))
        high = float(candle.get("high", close))
        low = float(candle.get("low", close))
        ts = int(candle.get("timestamp", order.ts))

        # min notional check
        notional = abs(order.qty * close)
        from ..metrics.exec import get_orders_blocked_total
        if self.min_notional and notional < self.min_notional:
            get_orders_blocked_total().labels("min_notional", order.symbol).inc()
            return fills

        # remaining qty
        remaining = self._remaining.get(order.id, float(order.qty))
        to_fill = min(remaining, float(order.qty) * self.liquidity_fraction)
        to_fill = self._round_step(to_fill)
        if to_fill <= 0:
            return fills

        if order.type == "market":
            slip_bps = self._slippage_bps(close, features or {})
            slip_mult = 1.0 + (slip_bps / 10_000.0) * (1 if order.side == "buy" else -1)
            price = self._round_tick(close * slip_mult)
            fee = abs(price * to_fill) * (self.taker_bps / 10_000.0)
            qty_signed = to_fill if order.side == "buy" else -to_fill
            fills.append(Fill(order_id=order.id, ts=ts, symbol=order.symbol, qty=qty_signed, price=price, fee=fee, liquidity="taker"))
        else:
            limit_price = self._round_tick(float(order.price or close))
            crossed = (order.side == "buy" and low <= limit_price) or (order.side == "sell" and high >= limit_price)
            if crossed:
                fee = abs(limit_price * to_fill) * (self.maker_bps / 10_000.0)
                qty_signed = to_fill if order.side == "buy" else -to_fill
                fills.append(Fill(order_id=order.id, ts=ts, symbol=order.symbol, qty=qty_signed, price=limit_price, fee=fee, liquidity="maker"))
            else:
                to_fill = 0.0

        new_remaining = max(0.0, remaining - abs(to_fill))
        self._remaining[order.id] = new_remaining

        for f in fills:
            self.fills_total.labels(f.liquidity, f.symbol).inc()
            self.fees_paid.labels(f.symbol).inc(f.fee)
        return fills

    def mark_to_market(self, positions: Dict[str, Any], price_by_symbol: Dict[str, float]) -> Dict[str, float]:
        unreal: Dict[str, float] = {}
        for sym, pos in positions.items():
            px = float(price_by_symbol.get(sym, 0.0))
            if pos.qty == 0:
                unreal[sym] = 0.0
            else:
                # Long qty>0, Short qty<0
                unreal_pnl = (px - pos.avg_price) * pos.qty
                unreal[sym] = float(unreal_pnl)
        return unreal

    # ---- helpers ----
    def _round_tick(self, price: float) -> float:
        if self.tick_size <= 0:
            return price
        return round(round(price / self.tick_size) * self.tick_size, 10)

    def _round_step(self, qty: float) -> float:
        if self.step_size <= 0:
            return qty
        steps = int(qty / self.step_size)
        return round(steps * self.step_size, 10)

    def _slippage_bps(self, price: float, features: Dict[str, Any]) -> float:
        base = self.profile_slip_bps if self.profile_slip_bps else self.slippage_bps_market
        if self.slippage_model == "random_bps":
            return float(random.uniform(self.random_bps_min, self.random_bps_max))
        if self.slippage_model == "atr_scaled":
            atr = float(features.get("atr14", 0.0))
            if price > 0:
                return float(base * (atr / price) * self.atr_slip_mult)
        return float(base)
