from __future__ import annotations

from typing import Any, Dict, List
from .model import Order, Fill
from ..metrics.exec import (
    get_orders_submitted_total,
    get_fills_total,
    get_fees_paid_total,
)


class ExecutionSimulator:
    def __init__(self, config: Dict[str, Any]):
        cfg = config or {}
        self.slippage_bps_market = float(cfg.get("slippage_bps_market", 3.0))
        self.taker_bps = float(cfg.get("taker_bps", 1.0))
        self.maker_bps = float(cfg.get("maker_bps", 0.5))
        self.liquidity_fraction = float(cfg.get("liquidity_fraction", 0.15))
        # Metrics
        self.orders_submitted = get_orders_submitted_total()
        self.fills_total = get_fills_total()
        self.fees_paid = get_fees_paid_total()

    def submit(self, order: Order, candle: Dict[str, Any]) -> List[Fill]:
        self.orders_submitted.labels(order.type, order.symbol).inc()
        fills: List[Fill] = []
        close = float(candle.get("close", 0.0))
        high = float(candle.get("high", close))
        low = float(candle.get("low", close))
        ts = int(candle.get("timestamp", order.ts))

        if order.type == "market":
            slip_mult = 1.0 + (self.slippage_bps_market / 10_000.0) * (1 if order.side == "buy" else -1)
            price = close * slip_mult
            fee = abs(price * order.qty) * (self.taker_bps / 10_000.0)
            fill = Fill(order_id=order.id, ts=ts, symbol=order.symbol, qty=order.qty, price=price, fee=fee, liquidity="taker")
            fills.append(fill)
        else:  # limit
            limit_price = float(order.price or close)
            crossed = (order.side == "buy" and low <= limit_price) or (order.side == "sell" and high >= limit_price)
            if crossed:
                fee = abs(limit_price * order.qty) * (self.maker_bps / 10_000.0)
                fill = Fill(order_id=order.id, ts=ts, symbol=order.symbol, qty=order.qty, price=limit_price, fee=fee, liquidity="maker")
                fills.append(fill)
            # else: no fill on this candle

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

