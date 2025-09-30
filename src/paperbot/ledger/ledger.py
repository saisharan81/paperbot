from __future__ import annotations

from typing import Any, Dict, List
import os
import pandas as pd
from ..exec.model import Position, Fill, Trade, LedgerRow
from ..metrics.exec import get_realized_pnl_total, get_equity_gauge, get_account_equity_usd


class Ledger:
    def __init__(self, equity_start: float = 10_000.0):
        self.positions: Dict[str, Position] = {}
        self.equity_start = float(equity_start)
        self.realized_total = 0.0
        self.equity = float(equity_start)
        self.peak_equity = float(equity_start)
        self.trades: List[Trade] = []
        self.rows: List[LedgerRow] = []
        self._realized_counter = get_realized_pnl_total()
        self._equity_gauge = get_equity_gauge()
        # New USD equity gauge (labeled by market); keep legacy gauge in parallel
        self._equity_usd_by_market = get_account_equity_usd()

    def _get_pos(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol=symbol, qty=0.0, avg_price=0.0))

    def on_fill(self, f: Fill) -> None:
        pos = self._get_pos(f.symbol)
        # Determine if this increases or reduces position
        filled_qty = f.qty if f.qty >= 0 else -abs(f.qty)
        fee_cost = getattr(f, "fee_usd", f.fee)
        if pos.qty == 0.0:
            # Opening
            pos.qty = filled_qty
            pos.avg_price = f.price
            realized = -fee_cost
        elif (pos.qty > 0 and filled_qty > 0) or (pos.qty < 0 and filled_qty < 0):
            # Adding to existing in same direction: new avg price
            new_qty = pos.qty + filled_qty
            if new_qty != 0:
                pos.avg_price = (pos.avg_price * abs(pos.qty) + f.price * abs(filled_qty)) / abs(new_qty)
            pos.qty = new_qty
            realized = -fee_cost
        else:
            # Reducing / closing (opposite sign)
            reduce_qty = min(abs(pos.qty), abs(filled_qty))
            direction = 1.0 if pos.qty > 0 else -1.0
            realized_pnl = (f.price - pos.avg_price) * (reduce_qty * direction) - fee_cost
            realized = realized_pnl
            pos.qty = pos.qty + filled_qty  # will reduce magnitude
            if pos.qty == 0:
                pos.avg_price = 0.0
        self.positions[f.symbol] = pos
        self.realized_total += realized
        # Counters cannot be decremented; only accumulate positive realized PnL
        if realized > 0:
            self._realized_counter.labels(f.symbol).inc(realized)
        self.trades.append(
            Trade(
                ts=f.ts,
                symbol=f.symbol,
                side="buy" if f.qty > 0 else "sell",
                qty=f.qty,
                price=f.price,
                fee=f.fee,
                fee_currency=f.fee_currency,
                fee_usd=fee_cost,
                realized_pnl=realized,
            )
        )

    def mark_to_market(self, ts: int, price_by_symbol: Dict[str, float]) -> None:
        unreal_total = 0.0
        for sym, pos in self.positions.items():
            px = float(price_by_symbol.get(sym, 0.0))
            if pos.qty != 0:
                unreal_total += (px - pos.avg_price) * pos.qty
        self.equity = self.equity_start + self.realized_total + unreal_total
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        drawdown = 1.0 - (self.equity / self.peak_equity if self.peak_equity > 0 else 1.0)
        # Label as total account equity (robust against missing gauge instances)
        try:
            if self._equity_gauge is None:
                from ..metrics.exec import get_equity_gauge as _get_eq
                self._equity_gauge = _get_eq()
            # Preferred: labeled by symbol
            try:
                self._equity_gauge.labels("total").set(self.equity)  # type: ignore[attr-defined]
            except Exception:
                # Fallback for unlabeled gauges in constrained runs
                self._equity_gauge.set(self.equity)  # type: ignore[attr-defined]
        except Exception:
            pass
        # Also emit USD equity per inferred market (heuristic: pure alpha symbols => stocks)
        try:
            if price_by_symbol:
                # Prefer the first symbol to infer market for this snapshot
                first_sym = next(iter(price_by_symbol.keys()))
                market = "stocks" if str(first_sym).isalpha() else "crypto"
            else:
                market = "crypto"
            self._equity_usd_by_market.labels(market=market).set(self.equity)  # type: ignore[attr-defined]
        except Exception:
            # Metrics optional in tests; ignore if not available
            pass
        # store a single consolidated row (symbol blank) for eq/dd snapshot
        self.rows.append(LedgerRow(ts=ts, symbol="", realized_pnl=self.realized_total, unrealized_pnl=unreal_total, equity=self.equity, drawdown=max(0.0, drawdown)))

    def write_parquet(self, base_dir: str = "data") -> None:
        os.makedirs(base_dir, exist_ok=True)
        trades_df = pd.DataFrame([t.__dict__ for t in self.trades])
        ledger_df = pd.DataFrame([r.__dict__ for r in self.rows])
        trades_df.to_parquet(os.path.join(base_dir, "trades.parquet"))
        ledger_df.to_parquet(os.path.join(base_dir, "ledger.parquet"))
