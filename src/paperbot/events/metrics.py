from __future__ import annotations

from typing import Optional
from prometheus_client import Counter, Histogram, REGISTRY

_events_total: Optional[Counter] = None
_orders_rejected_total: Optional[Counter] = None
_order_fill_latency_seconds: Optional[Histogram] = None
_slippage_bps: Optional[Histogram] = None


def get_events_total():
    global _events_total
    if _events_total is None:
        _events_total = Counter("events_total", "Paperbot events", ["type"])  # type: ignore[arg-type]
    return _events_total


def get_orders_rejected_total():
    global _orders_rejected_total
    if _orders_rejected_total is None:
        _orders_rejected_total = Counter("orders_rejected_total", "Orders rejected", ["reason"])  # type: ignore[arg-type]
    return _orders_rejected_total


def get_order_fill_latency_seconds():
    global _order_fill_latency_seconds
    if _order_fill_latency_seconds is None:
        _order_fill_latency_seconds = Histogram(
            "order_fill_latency_seconds",
            "Latency from submit to fill",
            buckets=(0.5, 1, 2, 5, 10, 30, 60),
        )
    return _order_fill_latency_seconds


def get_slippage_bps():
    global _slippage_bps
    if _slippage_bps is None:
        _slippage_bps = Histogram(
            "slippage_bps",
            "Slippage in basis points",
            buckets=(0.1, 0.5, 1, 2, 5, 10, 20),
        )
    return _slippage_bps

