"""
Chart utilities to render candlestick images from OHLCV data.

Generates simple candlestick charts with optional session VWAP overlay.
Saves PNGs to a destination path (ensures parent directories exist).
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import matplotlib

# Use a non-interactive backend for headless environments
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402


def _session_vwap_series(candles: List[Dict[str, Any]]) -> List[float]:
    """Compute per-bar session VWAP (UTC day.reset) across the provided candles."""
    vwap_series: List[float] = []
    pv_sum = 0.0
    v_sum = 0.0
    current_day: Optional[datetime.date] = None
    for c in candles:
        ts = int(c.get("timestamp", 0))
        day = datetime.utcfromtimestamp(ts / 1000.0).date()
        if current_day is None or day != current_day:
            pv_sum = 0.0
            v_sum = 0.0
            current_day = day
        price = float(c.get("close", 0.0))
        vol = float(c.get("volume", 0.0))
        pv_sum += price * vol
        v_sum += vol
        vwap_series.append(pv_sum / v_sum if v_sum > 0 else 0.0)
    return vwap_series


def save_candlestick_png(
    candles: List[Dict[str, Any]],
    symbol: str,
    timeframe: str,
    out_path: str,
    overlay_session_vwap: bool = True,
) -> str:
    """Render a candlestick chart and save to `out_path` (PNG).

    Returns the absolute path to the saved file.
    """
    if not candles:
        raise ValueError("No candles provided for charting")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Prepare OHLC arrays
    times = [mdates.date2num(datetime.utcfromtimestamp(c["timestamp"] / 1000.0)) for c in candles]
    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title(f"{symbol} — {timeframe} candlesticks")

    # Draw wicks
    for t, h, l in zip(times, highs, lows):
        ax.vlines(t, l, h, color="black", linewidth=0.8)

    # Draw bodies
    width = 0.6 * (times[1] - times[0]) if len(times) > 1 else 0.01
    for t, o, c in zip(times, opens, closes):
        color = "green" if c >= o else "red"
        lower = min(o, c)
        height = abs(c - o)
        ax.add_patch(plt.Rectangle((t - width / 2, lower), width, max(height, 1e-9), color=color, alpha=0.6))

    if overlay_session_vwap:
        vwap = _session_vwap_series(candles)
        ax.plot(times, vwap, color="blue", linewidth=1.0, label="session VWAP")
        ax.legend(loc="best")

    # Format x-axis as time
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M\n%m-%d"))
    ax.grid(True, linestyle=":", alpha=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return os.path.abspath(out_path)
