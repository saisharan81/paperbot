"""
Optional technical indicators for feature expansion.

What it does:
- Implements stand-alone indicator helpers (SMA/EMA crossover, MACD, Bollinger,
  OBV, Keltner Channel, rolling skew/kurtosis, hour-of-day extraction).
- Functions are pure and return safe defaults when insufficient data is available.

Where it is used:
- Imported by `FeatureBuilder` to conditionally compute expanded features.
- Unit-tested in `tests/test_features_expansion.py`.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone


def sma_ema_cross(prices: np.ndarray, fast: int = 5, slow: int = 10) -> Dict[str, float]:
    """
    Calculate SMA/EMA crossover signals.
    
    Args:
        prices: Array of closing prices
        fast: Fast period for EMA
        slow: Slow period for SMA
        
    Returns:
        Dict with sma, ema, crossover_signal values
    """
    if len(prices) < slow:
        return {"sma": 0.0, "ema": 0.0, "crossover_signal": 0.0}
    
    # Calculate SMA
    sma = np.mean(prices[-slow:])
    
    # Calculate EMA using the fast period (iterative EMA on recent window)
    if len(prices) >= fast:
        # Use the last 'fast' prices for EMA calculation
        recent_prices = prices[-fast:]
        alpha = 2.0 / (fast + 1)
        ema = recent_prices[0]
        for price in recent_prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
    else:
        ema = prices[-1]  # Use last price if insufficient data
    
    # Crossover signal: 1 if EMA > SMA (bullish), -1 if EMA < SMA (bearish)
    crossover_signal = 1.0 if ema > sma else -1.0
    
    return {
        "sma": float(sma),
        "ema": float(ema),
        "crossover_signal": crossover_signal
    }


def macd(prices: np.ndarray, fast: int = 8, slow: int = 15, signal: int = 5) -> Dict[str, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Array of closing prices
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        
    Returns:
        Dict with macd, signal_line, histogram values
    """
    if len(prices) < slow:
        return {"macd": 0.0, "signal_line": 0.0, "histogram": 0.0}
    
    # Calculate fast and slow EMAs
    alpha_fast = 2.0 / (fast + 1)
    alpha_slow = 2.0 / (slow + 1)
    
    ema_fast = prices[0]
    ema_slow = prices[0]
    
    for price in prices[1:]:
        ema_fast = alpha_fast * price + (1 - alpha_fast) * ema_fast
        ema_slow = alpha_slow * price + (1 - alpha_slow) * ema_slow
    
    macd_line = ema_fast - ema_slow
    
    # Signal line (EMA of MACD); approximate over trailing window
    if len(prices) >= slow + signal:
        macd_values = []
        for i in range(slow, len(prices)):
            alpha = 2.0 / (fast + 1)
            ema_fast_i = prices[i - slow]
            ema_slow_i = prices[i - slow]
            for j in range(i - slow + 1, i + 1):
                ema_fast_i = alpha * prices[j] + (1 - alpha) * ema_fast_i
                ema_slow_i = alpha * prices[j] + (1 - alpha) * ema_slow_i
            macd_values.append(ema_fast_i - ema_slow_i)
        
        if macd_values:
            signal_line = np.mean(macd_values[-signal:])
        else:
            signal_line = macd_line
    else:
        signal_line = macd_line
    
    histogram = macd_line - signal_line
    
    return {
        "macd": float(macd_line),
        "signal_line": float(signal_line),
        "histogram": float(histogram)
    }


def bollinger_bands(prices: np.ndarray, period: int = 20, mult: float = 2.0) -> Dict[str, float]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Array of closing prices
        period: Rolling window period
        mult: Standard deviation multiplier
        
    Returns:
        Dict with upper_band, middle_band, lower_band, bandwidth values
    """
    if len(prices) < period:
        return {
            "upper_band": 0.0,
            "middle_band": 0.0,
            "lower_band": 0.0,
            "bandwidth": 0.0
        }
    
    recent_prices = prices[-period:]
    middle_band = np.mean(recent_prices)
    std_dev = np.std(recent_prices)
    
    upper_band = middle_band + (mult * std_dev)
    lower_band = middle_band - (mult * std_dev)
    bandwidth = (upper_band - lower_band) / middle_band if middle_band != 0 else 0.0
    
    return {
        "upper_band": float(upper_band),
        "middle_band": float(middle_band),
        "lower_band": float(lower_band),
        "bandwidth": float(bandwidth)
    }


def obv(prices: np.ndarray, volumes: np.ndarray) -> Dict[str, float]:
    """
    Calculate On-Balance Volume (OBV).
    
    Args:
        prices: Array of closing prices
        volumes: Array of trading volumes
        
    Returns:
        Dict with obv, obv_change values
    """
    if len(prices) < 2 or len(volumes) < 2:
        return {"obv": 0.0, "obv_change": 0.0}
    
    obv_value = 0.0
    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            obv_value += volumes[i]
        elif prices[i] < prices[i-1]:
            obv_value -= volumes[i]
    
    obv_change = obv_value - (0.0 if len(prices) < 3 else obv_value)
    
    return {
        "obv": float(obv_value),
        "obv_change": float(obv_change)
    }


def keltner_channel(prices: np.ndarray, high: np.ndarray, low: np.ndarray, 
                    period: int = 20) -> Dict[str, float]:
    """
    Calculate Keltner Channels.
    
    Args:
        prices: Array of closing prices
        high: Array of high prices
        low: Array of low prices
        period: Rolling window period
        
    Returns:
        Dict with upper_channel, middle_channel, lower_channel values
    """
    if len(prices) < period:
        return {
            "upper_channel": 0.0,
            "middle_channel": 0.0,
            "lower_channel": 0.0
        }
    
    recent_prices = prices[-period:]
    recent_high = high[-period:]
    recent_low = low[-period:]
    
    # Middle channel (EMA of close)
    alpha = 2.0 / (period + 1)
    middle_channel = recent_prices[0]
    for price in recent_prices[1:]:
        middle_channel = alpha * price + (1 - alpha) * middle_channel
    
    # ATR calculation (True Range average over recent window)
    tr_values = []
    for i in range(1, len(recent_high)):
        tr = max(
            recent_high[i] - recent_low[i],
            abs(recent_high[i] - recent_prices[i-1]),
            abs(recent_low[i] - recent_prices[i-1])
        )
        tr_values.append(tr)
    
    atr = np.mean(tr_values) if tr_values else 0.0
    
    upper_channel = middle_channel + (2.0 * atr)
    lower_channel = middle_channel - (2.0 * atr)
    
    return {
        "upper_channel": float(upper_channel),
        "middle_channel": float(middle_channel),
        "lower_channel": float(lower_channel)
    }


def rolling_skew_kurtosis(prices: np.ndarray, lookback: int = 20) -> Dict[str, float]:
    """
    Calculate rolling skewness and kurtosis.
    
    Args:
        prices: Array of closing prices
        lookback: Rolling window period
        
    Returns:
        Dict with skewness, kurtosis values
    """
    if len(prices) < lookback:
        return {"skewness": 0.0, "kurtosis": 0.0}
    
    recent_prices = prices[-lookback:]
    returns = np.diff(recent_prices) / recent_prices[:-1]
    
    if len(returns) < 3:
        return {"skewness": 0.0, "kurtosis": 0.0}
    
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return {"skewness": 0.0, "kurtosis": 0.0}
    
    # Skewness
    skewness = np.mean(((returns - mean_return) / std_return) ** 3)
    
    # Kurtosis (excess kurtosis, subtract 3 so normal≈0)
    kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
    
    return {
        "skewness": float(skewness),
        "kurtosis": float(kurtosis)
    }


def hour_of_day(timestamp_ms: int) -> Dict[str, Any]:
    """
    Extract hour of day from timestamp.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        
    Returns:
        Dict with hour_int, hour_cat values
    """
    try:
        # Use UTC to avoid local timezone skew in tests and runtime.
        ts = datetime.utcfromtimestamp(timestamp_ms / 1000.0).replace(tzinfo=timezone.utc)
        hour_int = ts.hour
        hour_cat = f"hour_{hour_int:02d}"
    except (ValueError, OSError):
        hour_int = 0
        hour_cat = "hour_00"
    
    return {
        "hour_int": hour_int,
        "hour_cat": hour_cat,
        "hour": hour_int,
    }
