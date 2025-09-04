"""
Tests for Phase 1.1 baseline indicators in FeatureBuilder.
"""

import math
import numpy as np

from src.paperbot.features.feature_builder import FeatureBuilder


def make_candles(prices, volumes=None):
    """Create 1m synthetic candles with simple high/low envelopes."""
    if volumes is None:
        volumes = np.ones_like(prices, dtype=float)
    candles = []
    base = 1704067200000  # 2024-01-01 00:00:00 UTC
    prev = float(prices[0])
    for i, p in enumerate(prices):
        p = float(p)
        o = prev
        h = max(o, p) + 1.0
        l = min(o, p) - 1.0
        candles.append(
            {
                "timestamp": base + i * 60_000,
                "open": o,
                "high": h,
                "low": l,
                "close": p,
                "volume": float(volumes[i]),
                "symbol": "TEST/XYZ",
            }
        )
        prev = p
    return candles


def test_phase11_basic_bounds():
    # Slightly noisy upward trend
    rng = np.random.default_rng(42)
    prices = np.cumsum(rng.normal(0.1, 0.5, 120)) + 100.0
    vols = rng.uniform(0.5, 2.0, 120)
    candles = make_candles(prices, vols)
    fb = FeatureBuilder({})
    feats = fb.compute_latest(candles)
    print({k: round(float(feats[k]), 6) for k in ["rsi14", "atr14", "vwap", "z_vwap", "rv_30m"]})

    assert 0.0 <= feats["rsi14"] <= 100.0
    assert feats["atr14"] >= 0.0
    assert feats["vwap"] > 0.0
    assert math.isfinite(feats["z_vwap"])  # finite by construction
    assert feats["rv_30m"] >= 0.0


def test_z_vwap_on_flat_and_outlier():
    # Flat prices then outlier at the end
    prices = np.full(80, 100.0)
    vols = np.ones(80)
    candles = make_candles(prices, vols)
    fb = FeatureBuilder({})
    feats_flat = fb.compute_latest(candles)
    print("z_vwap_flat=", feats_flat["z_vwap"])
    # On perfectly flat series, variance is ~0 -> z=0
    assert feats_flat["z_vwap"] == 0.0

    # Inject outlier on last bar
    prices2 = prices.copy()
    prices2[-1] = 120.0
    candles2 = make_candles(prices2, vols)
    feats_outlier = fb.compute_latest(candles2)
    print("z_vwap_outlier=", feats_outlier["z_vwap"])
    assert feats_outlier["z_vwap"] != 0.0


def test_realized_vol_positive_on_noise():
    rng = np.random.default_rng(0)
    prices = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 100)))
    candles = make_candles(prices)
    fb = FeatureBuilder({})
    feats = fb.compute_latest(candles)
    print("rv_30m=", feats["rv_30m"])
    assert feats["rv_30m"] > 0.0


def test_vwap_pulled_by_high_volume_last_bar():
    # Mostly constant prices/volumes, then a last bar with same high price but huge volume
    prices = np.full(60, 100.0)
    vols_small = np.ones(60)
    vols_big = vols_small.copy()
    vols_big[-1] = 1000.0

    candles_small = make_candles(prices, vols_small)
    candles_big = make_candles(prices, vols_big)

    fb = FeatureBuilder({})
    vwap_small = fb.compute_latest(candles_small)["vwap"]
    # Make the last price slightly higher to pull VWAP up when volume is big
    prices2 = prices.copy()
    prices2[-1] = 110.0
    candles_big_price = make_candles(prices2, vols_big)
    vwap_big = fb.compute_latest(candles_big_price)["vwap"]
    print({"vwap_small": vwap_small, "vwap_big": vwap_big})

    assert vwap_big > vwap_small
