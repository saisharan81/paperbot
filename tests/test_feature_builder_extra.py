import numpy as np
from src.paperbot.features.feature_builder import FeatureBuilder


def make_candles(prices, highs=None, lows=None, volumes=None):
    n = len(prices)
    if highs is None:
        highs = prices + 1.0
    if lows is None:
        lows = prices - 1.0
    if volumes is None:
        volumes = np.ones(n)
    base = 1704067200000
    out = []
    for i in range(n):
        out.append({
            "timestamp": base + i*60_000,
            "open": float(prices[i-1] if i>0 else prices[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(prices[i]),
            "volume": float(volumes[i]),
            "symbol": "TEST/XYZ"
        })
    return out


def test_extra_indicators_present_and_sane():
    rng = np.random.default_rng(0)
    prices = 100 + np.cumsum(rng.normal(0, 0.5, 120))
    highs = prices + 1
    lows = prices - 1
    vols = rng.uniform(1, 5, 120)
    candles = make_candles(prices, highs, lows, vols)
    fb = FeatureBuilder({})
    feats = fb.compute_latest(candles)
    assert "cci20" in feats
    assert "stochrsi_k" in feats
    assert "stochrsi_d" in feats
    assert "mfi14" in feats
    # sanity ranges
    assert -500 <= feats["cci20"] <= 500
    assert 0.0 <= feats["stochrsi_k"] <= 1.0
    assert 0.0 <= feats["stochrsi_d"] <= 1.0
    assert 0.0 <= feats["mfi14"] <= 100.0
