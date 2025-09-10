from __future__ import annotations

from typing import Optional, Dict
import os
from prometheus_client import Counter, Gauge, REGISTRY

_orders_submitted: Optional[Counter] = None
_orders_blocked: Optional[Counter] = None
_fills_total: Optional[Counter] = None
_fees_paid_total: Optional[Counter] = None
_realized_pnl_total: Optional[Counter] = None
_equity_gauge: Optional[Gauge] = None
_killswitch_trips: Optional[Counter] = None
_fees_paid_usd_total: Optional[Counter] = None
_account_equity_usd: Optional[Gauge] = None
_mtm_tick_total: Optional[Counter] = None


class _NoOp:
    def labels(self, *args, **kwargs):
        return self
    def inc(self, *args, **kwargs):
        return None
    def set(self, *args, **kwargs):
        return None


def _safe_counter(name: str, doc: str, labelnames):
    if os.getenv("DISABLE_PROMETHEUS", "0") == "1":
        return _NoOp()
    try:
        return Counter(name, doc, labelnames)
    except ValueError:
        # Try to find existing collector in default REGISTRY
        try:
            for coll in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
                if isinstance(coll, Counter) and getattr(coll, "_name", None) == name:
                    return coll
        except Exception:
            pass
        return _NoOp()


def _safe_gauge(name: str, doc: str):
    if os.getenv("DISABLE_PROMETHEUS", "0") == "1":
        return _NoOp()


def _safe_gauge_labels(name: str, doc: str, labelnames):
    if os.getenv("DISABLE_PROMETHEUS", "0") == "1":
        return _NoOp()
    try:
        return Gauge(name, doc, labelnames)
    except ValueError:
        try:
            for coll in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
                if isinstance(coll, Gauge) and getattr(coll, "_name", None) == name:
                    return coll
        except Exception:
            pass
        return _NoOp()
    try:
        return Gauge(name, doc)
    except ValueError:
        try:
            for coll in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
                if isinstance(coll, Gauge) and getattr(coll, "_name", None) == name:
                    return coll
        except Exception:
            pass
        return _NoOp()


def get_orders_submitted_total():
    global _orders_submitted
    if _orders_submitted is None:
        _orders_submitted = _safe_counter("orders_submitted_total", "Orders submitted", ["type", "symbol"])
    return _orders_submitted


def get_orders_blocked_total():
    global _orders_blocked
    if _orders_blocked is None:
        _orders_blocked = _safe_counter("orders_blocked_total", "Orders blocked", ["reason", "symbol"])
    return _orders_blocked


def get_fills_total():
    global _fills_total
    if _fills_total is None:
        _fills_total = _safe_counter("fills_total", "Fills produced", ["liquidity", "symbol"])
    return _fills_total


def get_fees_paid_total():
    global _fees_paid_total
    if _fees_paid_total is None:
        _fees_paid_total = _safe_counter("fees_paid_total", "Fees paid", ["symbol"])
    return _fees_paid_total


def get_fees_paid_usd_total():
    """Counter: fees paid in USD, labeled by market and symbol.

    Note: This runs in parallel with legacy `fees_paid_total` for one release.
    """
    global _fees_paid_usd_total
    if _fees_paid_usd_total is None:
        _fees_paid_usd_total = _safe_counter(
            "fees_paid_usd_total", "Fees paid in USD", ["market", "symbol"]
        )
    return _fees_paid_usd_total


def get_realized_pnl_total():
    global _realized_pnl_total
    if _realized_pnl_total is None:
        _realized_pnl_total = _safe_counter("realized_pnl_total", "Realized PnL", ["symbol"])
    return _realized_pnl_total


def get_equity_gauge():
    global _equity_gauge
    if _equity_gauge is None:
        # Labeled by symbol; use symbol="total" for account equity snapshots
        _equity_gauge = _safe_gauge_labels("equity_gauge", "Equity value", ["symbol"])
    return _equity_gauge


def get_account_equity_usd():
    """Gauge: account equity in USD, labeled by market.

    Note: This runs in parallel with legacy `equity_gauge` for one release.
    """
    global _account_equity_usd
    if _account_equity_usd is None:
        _account_equity_usd = _safe_gauge_labels(
            "account_equity_usd", "Account equity in USD", ["market"]
        )
    return _account_equity_usd


def get_mtm_tick_total():
    """Counter: count of MTM ticks executed per market."""
    global _mtm_tick_total
    if _mtm_tick_total is None:
        _mtm_tick_total = _safe_counter(
            "mtm_tick_total", "Mark-to-market ticks executed", ["market"]
        )
    return _mtm_tick_total


def set_equity_gauges(equity_by_market: Dict[str, float]) -> None:
    """Set account_equity_usd gauge for each provided market.

    Keeps legacy metrics unchanged; this only affects the USD-labeled gauge.
    """
    g = get_account_equity_usd()
    for mkt, val in equity_by_market.items():
        try:
            g.labels(market=str(mkt)).set(float(val))  # type: ignore[attr-defined]
        except Exception:
            # Metrics are optional in constrained environments
            continue


def get_killswitch_trips_total():
    global _killswitch_trips
    if _killswitch_trips is None:
        _killswitch_trips = _safe_counter("killswitch_trips_total", "Kill switch trips", [])
    return _killswitch_trips
