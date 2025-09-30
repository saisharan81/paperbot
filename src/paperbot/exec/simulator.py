from __future__ import annotations

import json
import logging
import random
from typing import Any, Dict, List, Tuple

from .model import Order, Fill
from ..metrics.exec import (
    get_orders_submitted_total,
    get_fills_total,
    get_fees_paid_total,
    get_fees_paid_usd_total,
)
from ..events.schema import EventEnvelope, OrderSubmitted, OrderPartiallyFilled, OrderFilled, OrderRejected
from ..events.bus import publish as publish_event


logger = logging.getLogger(__name__)


class PriceOracle:
    STABLE_COINS = {"USD", "USDT", "USDC", "BUSD", "TUSD"}

    def __init__(self, profile: Dict[str, Any] | None = None):
        cfg = profile or {}
        self.fx_overrides = {str(k).upper(): float(v) for k, v in cfg.get("fx_overrides", {}).items()}
        self.symbol_overrides = {str(k).upper(): float(v) for k, v in cfg.get("symbol_overrides", {}).items()}

    @staticmethod
    def split_symbol(symbol: str) -> Tuple[str, str]:
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
            return base.upper(), quote.upper()
        return symbol.upper(), "USD"

    def quote_usd_rate(self, quote: str) -> float:
        q = quote.upper()
        if q in self.STABLE_COINS:
            return 1.0
        return self.fx_overrides.get(q, 1.0)

    def base_usd_price(self, symbol: str, candle: Dict[str, Any]) -> float:
        key = symbol.upper()
        if key in self.symbol_overrides:
            return self.symbol_overrides[key]
        base, quote = self.split_symbol(symbol)
        close = float(candle.get("close", 0.0) or 0.0)
        return close * self.quote_usd_rate(quote)


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
        # New: USD-denominated fees counter (runs alongside legacy metric)
        self.fees_paid_usd = get_fees_paid_usd_total()
        self.oracle = PriceOracle(prof.get("oracle", {}))

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
            try:
                evt = OrderRejected(
                    ts=ts,
                    market="stocks" if order.symbol.isalpha() else "crypto",
                    symbol=order.symbol,
                    strategy=order.strategy,
                    side=order.side,
                    reason="min_notional",
                )
                publish_event(EventEnvelope(correlation_id=order.id, event=evt))
            except Exception:
                pass
            return fills

        # remaining qty
        remaining = self._remaining.get(order.id, float(order.qty))
        to_fill = min(remaining, float(order.qty) * self.liquidity_fraction)
        to_fill = self._round_step(to_fill)
        if to_fill <= 0:
            return fills

        fee_currency = (order.fee_currency or self._default_fee_currency(order.symbol)).upper()
        base_asset, quote_asset = PriceOracle.split_symbol(order.symbol)
        fee_amount: float

        if order.type == "market":
            slip_bps = self._slippage_bps(close, features or {})
            slip_mult = 1.0 + (slip_bps / 10_000.0) * (1 if order.side == "buy" else -1)
            price = self._round_tick(close * slip_mult)
            fee_amount = self._compute_fee_amount(
                rate_bps=self.taker_bps,
                price=price,
                qty=to_fill,
                fee_currency=fee_currency,
                base=base_asset,
                quote=quote_asset,
                override=order.fee_amount,
            )
            qty_signed = to_fill if order.side == "buy" else -to_fill
            try:
                evt = OrderSubmitted(
                    ts=ts,
                    market="stocks" if order.symbol.isalpha() else "crypto",
                    symbol=order.symbol,
                    strategy=order.strategy,
                    side=order.side,
                    order_id=order.id,
                    qty=float(order.qty),
                    price=None,
                )
                publish_event(EventEnvelope(correlation_id=order.id, event=evt))
            except Exception:
                pass
            fee_usd = self._convert_fee_to_usd(fee_amount, fee_currency, order.symbol, candle)
            fills.append(
                Fill(
                    order_id=order.id,
                    ts=ts,
                    symbol=order.symbol,
                    qty=qty_signed,
                    price=price,
                    fee=fee_amount,
                    fee_currency=fee_currency,
                    fee_usd=fee_usd,
                    liquidity="taker",
                )
            )
        else:
            limit_price = self._round_tick(float(order.price or close))
            crossed = (order.side == "buy" and low <= limit_price) or (order.side == "sell" and high >= limit_price)
            if crossed:
                fee_amount = self._compute_fee_amount(
                    rate_bps=self.maker_bps,
                    price=limit_price,
                    qty=to_fill,
                    fee_currency=fee_currency,
                    base=base_asset,
                    quote=quote_asset,
                    override=order.fee_amount,
                )
                qty_signed = to_fill if order.side == "buy" else -to_fill
                fee_usd = self._convert_fee_to_usd(fee_amount, fee_currency, order.symbol, candle)
                fills.append(
                    Fill(
                        order_id=order.id,
                        ts=ts,
                        symbol=order.symbol,
                        qty=qty_signed,
                        price=limit_price,
                        fee=fee_amount,
                        fee_currency=fee_currency,
                        fee_usd=fee_usd,
                        liquidity="maker",
                    )
                )
            else:
                to_fill = 0.0

        new_remaining = max(0.0, remaining - abs(to_fill))
        self._remaining[order.id] = new_remaining

        for f in fills:
            self.fills_total.labels(f.liquidity, f.symbol).inc()
            self.fees_paid.labels(f.symbol).inc(f.fee)
            # Determine market from symbol heuristic used elsewhere in the codebase
            market = "stocks" if f.symbol.isalpha() else "crypto"
            self.fees_paid_usd.labels(market=market, symbol=f.symbol).inc(f.fee_usd)
            # Emit partial-fill event (even if full fill occurs later)
            try:
                evt = OrderPartiallyFilled(
                    ts=f.ts,
                    market=market,
                    symbol=f.symbol,
                    strategy=order.strategy,
                    side=order.side,
                    order_id=f.order_id,
                    qty=abs(f.qty),
                    price=f.price,
                    fee_usd=f.fee_usd,
                    slippage_bps=None,
                )
                publish_event(EventEnvelope(correlation_id=order.id, event=evt))
            except Exception:
                pass
        # If fully filled on this call, emit order_filled
        try:
            if new_remaining == 0.0 and fills:
                total_qty = sum(abs(f.qty) for f in fills)
                avg_price = sum(abs(f.qty) * f.price for f in fills) / max(total_qty, 1e-9)
                evt2 = OrderFilled(
                    ts=fills[-1].ts,
                    market="stocks" if order.symbol.isalpha() else "crypto",
                    symbol=order.symbol,
                    strategy=order.strategy,
                    side=order.side,
                    order_id=order.id,
                    qty=total_qty,
                    avg_price=avg_price,
                    fee_usd=sum(float(f.fee_usd) for f in fills),
                )
                publish_event(EventEnvelope(correlation_id=order.id, event=evt2))
        except Exception:
            pass
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

    def _default_fee_currency(self, symbol: str) -> str:
        base, quote = PriceOracle.split_symbol(symbol)
        return quote

    def _convert_fee_to_usd(self, amount: float, currency: str, symbol: str, candle: Dict[str, Any]) -> float:
        curr = currency.upper()
        amt = float(amount)
        if curr in PriceOracle.STABLE_COINS:
            fee_usd = amt
            self._log_fee_conversion(symbol, curr, amt, 1.0, fee_usd)
            return fee_usd
        base, quote = PriceOracle.split_symbol(symbol)
        if curr == quote:
            rate = self.oracle.quote_usd_rate(quote)
            fee_usd = amt * rate
            self._log_fee_conversion(symbol, curr, amt, rate, fee_usd)
            return fee_usd
        if curr == base:
            price = self.oracle.base_usd_price(symbol, candle)
            fee_usd = amt * price
            self._log_fee_conversion(symbol, curr, amt, price, fee_usd)
            return fee_usd
        # Fallback: attempt FX override by currency code
        rate = self.oracle.quote_usd_rate(curr)
        fee_usd = amt * rate
        self._log_fee_conversion(symbol, curr, amt, rate, fee_usd)
        return fee_usd

    def _log_fee_conversion(self, symbol: str, currency: str, amount: float, rate: float, fee_usd: float) -> None:
        payload = {
            "event": "fee_converted",
            "symbol": symbol,
            "fee_currency": currency,
            "fee_amount": amount,
            "usd_rate": rate,
            "fee_usd": fee_usd,
        }
        try:
            logger.info(json.dumps(payload))
        except Exception:
            logger.info("fee_converted", extra=payload)

    def _compute_fee_amount(
        self,
        rate_bps: float,
        price: float,
        qty: float,
        fee_currency: str,
        base: str,
        quote: str,
        override: float,
    ) -> float:
        if override > 0:
            return abs(override)
        rate = abs(rate_bps) / 10_000.0
        if fee_currency == base:
            return abs(qty) * rate
        if fee_currency == quote:
            return abs(price * qty) * rate
        # Unknown currency – approximate using notional, conversion will adjust later
        return abs(price * qty) * rate
