"""
Feature builder for paperbot trading system.

What it does:
- Computes feature vectors from OHLCV candles.
- Provides lightweight baseline features (price/volume/volatility) and optional
  expansion features (SMA/EMA crossover, MACD, Bollinger Bands, OBV, etc.).

Where it is used:
- Instantiated by `paperbot.main` to compute features after fetching candles.

Related modules:
- `paperbot.features.expansion` for optional indicator implementations.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from .expansion import (
    sma_ema_cross, macd, bollinger_bands, obv, 
    keltner_channel, rolling_skew_kurtosis, hour_of_day
)

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """
    Builds feature vectors from OHLCV candle data.
    
    Supports both baseline features and optional expansion features
    controlled by configuration flags.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize feature builder with configuration.
        
        Args:
            config: Configuration dictionary with features.expansion flags
        """
        self.config = config
        self.expansion_config = config.get('features', {}).get('expansion', {})
        
        # Default expansion settings if not specified
        default_expansion = {
            'sma_ema': True,
            'macd': False,
            'bollinger': True,
            'obv': True,
            'keltner': False,
            'skew_kurtosis': False,
            'hour_of_day': True
        }
        
        # Merge with config, keeping defaults for missing keys
        for key, default_value in default_expansion.items():
            if key not in self.expansion_config:
                self.expansion_config[key] = default_value
        
        logger.info(f"Feature expansion config: {self.expansion_config}")
        # Optional window config with safe defaults
        feat_cfg = self.config.get('features', {}) if isinstance(self.config, dict) else {}
        self.window_rsi = int(feat_cfg.get('window_rsi', 14))
        self.window_atr = int(feat_cfg.get('window_atr', 14))
        self.window_z_vwap = int(feat_cfg.get('zscore_lookback', 50))
        self.window_rv = int(feat_cfg.get('rv_window', 30))
    
    def compute_baseline_features(self, candles: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute baseline technical features.
        
        Args:
            candles: List of candle dictionaries with OHLCV data
            
        Returns:
            Dictionary of baseline feature values
        """
        if not candles or len(candles) < 2:
            return self._empty_baseline_features()
        
        # Extract arrays for calculations
        closes = np.array([float(c['close']) for c in candles])
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        volumes = np.array([float(c['volume']) for c in candles])
        
        # Basic price features (last close and change)
        current_price = closes[-1]
        price_change = closes[-1] - closes[-2] if len(closes) > 1 else 0.0
        price_change_pct = (price_change / closes[-2]) * 100 if len(closes) > 1 and closes[-2] != 0 else 0.0
        
        # Volatility features (range of last bar)
        high_low_range = highs[-1] - lows[-1]
        high_low_range_pct = (high_low_range / current_price) * 100 if current_price != 0 else 0.0
        
        # Volume features (simple avg for scale)
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        volume_ratio = current_volume / avg_volume if avg_volume != 0 else 1.0
        
        return {
            "price": current_price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "high_low_range": high_low_range,
            "high_low_range_pct": high_low_range_pct,
            "volume": current_volume,
            "avg_volume": avg_volume,
            "volume_ratio": volume_ratio
        }
    
    def compute_expansion_features(self, candles: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute optional expansion features based on config flags.
        
        Args:
            candles: List of candle dictionaries with OHLCV data
            
        Returns:
            Dictionary of expansion feature values (empty if disabled)
        """
        if not candles or len(candles) < 2:
            return {}
        
        features = {}
        
        # Extract arrays for calculations
        closes = np.array([float(c['close']) for c in candles])
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        volumes = np.array([float(c['volume']) for c in candles])
        
        # SMA/EMA crossover
        if self.expansion_config.get('sma_ema', False):
            sma_ema_features = sma_ema_cross(closes)
            features.update({f"sma_ema_{k}": v for k, v in sma_ema_features.items()})
        
        # MACD
        if self.expansion_config.get('macd', False):
            macd_features = macd(closes)
            features.update({f"macd_{k}": v for k, v in macd_features.items()})
        
        # Bollinger Bands
        if self.expansion_config.get('bollinger', False):
            bb_features = bollinger_bands(closes)
            features.update({f"bb_{k}": v for k, v in bb_features.items()})
        
        # OBV
        if self.expansion_config.get('obv', False):
            obv_features = obv(closes, volumes)
            features.update({f"obv_{k}": v for k, v in obv_features.items()})
        
        # Keltner Channel
        if self.expansion_config.get('keltner', False):
            keltner_features = keltner_channel(closes, highs, lows)
            features.update({f"keltner_{k}": v for k, v in keltner_features.items()})
        
        # Rolling skewness and kurtosis
        if self.expansion_config.get('skew_kurtosis', False):
            skew_kurt_features = rolling_skew_kurtosis(closes)
            features.update({f"skew_kurt_{k}": v for k, v in skew_kurt_features.items()})
        
        # Hour of day
        if self.expansion_config.get('hour_of_day', False) and candles:
            timestamp_ms = int(candles[-1].get('timestamp', 0))
            hour_features = hour_of_day(timestamp_ms)
            features.update({f"hour_{k}": v for k, v in hour_features.items()})
        
        return features

    # ---- Phase 1.1 baseline indicators ----
    def _rsi_wilder(self, closes: np.ndarray, period: int) -> float:
        """Compute RSI using Wilder's smoothing. Safe default = 50.0."""
        if closes is None or len(closes) < period + 1:
            return 50.0
        diffs = np.diff(closes)
        gains = np.where(diffs > 0, diffs, 0.0)
        losses = np.where(diffs < 0, -diffs, 0.0)
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        if len(diffs) > period:
            for i in range(period, len(diffs)):
                avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
                avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
        # Guard divide by zero
        if avg_loss == 0:
            if avg_gain == 0:
                return 50.0
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(np.clip(rsi, 0.0, 100.0))

    def _atr_ewm(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> float:
        """Compute ATR using EWM of True Range with alpha=1/period. Safe default = 0.0."""
        n = len(closes)
        if n < 2:
            return 0.0
        prev_closes = closes[:-1]
        tr = np.maximum(highs[1:] - lows[1:], np.maximum(np.abs(highs[1:] - prev_closes), np.abs(lows[1:] - prev_closes)))
        if tr.size == 0:
            return 0.0
        # Exponential weighted mean, adjust=False mimics recursive smoothing
        s = pd.Series(tr)
        atr_series = s.ewm(alpha=1.0 / period, adjust=False).mean()
        atr = float(atr_series.iloc[-1])
        return max(0.0, atr)

    def _session_vwap_current(self, candles: List[Dict[str, Any]]) -> float:
        """Compute session VWAP for the UTC day of the last candle using close*volume.

        Returns 0.0 when no volume in session or no candles.
        """
        if not candles:
            return 0.0
        last_ts = int(candles[-1].get('timestamp', 0))
        last_date = datetime.utcfromtimestamp(last_ts / 1000.0).date()
        pv_sum = 0.0
        v_sum = 0.0
        for c in candles:
            ts = int(c.get('timestamp', 0))
            if datetime.utcfromtimestamp(ts / 1000.0).date() != last_date:
                continue
            price = float(c.get('close', 0.0))
            vol = float(c.get('volume', 0.0))
            pv_sum += price * vol
            v_sum += vol
        return float(pv_sum / v_sum) if v_sum > 0 else 0.0

    def _zscore_to_vwap(self, candles: List[Dict[str, Any]], lookback: int) -> float:
        """Compute z-score of (close - session_vwap_up_to_bar) over trailing lookback bars.

        Uses per-bar session VWAP computed cumulatively within each UTC day.
        Returns 0.0 when insufficient data or near-zero variance.
        """
        if not candles:
            return 0.0
        window = candles[-min(lookback, len(candles)):]
        # Build per-day cumulative sums to derive per-bar session VWAP
        pv_cum: Dict[Any, float] = {}
        v_cum: Dict[Any, float] = {}
        diffs: List[float] = []
        for c in window:
            ts = int(c.get('timestamp', 0))
            day = datetime.utcfromtimestamp(ts / 1000.0).date()
            price = float(c.get('close', 0.0))
            vol = float(c.get('volume', 0.0))
            if day not in pv_cum:
                pv_cum[day] = 0.0
                v_cum[day] = 0.0
            pv_cum[day] += price * vol
            v_cum[day] += vol
            vwap = (pv_cum[day] / v_cum[day]) if v_cum[day] > 0 else 0.0
            diffs.append(price - vwap)
        if len(diffs) < 2:
            return 0.0
        arr = np.array(diffs, dtype=float)
        mu = float(np.mean(arr))
        sigma = float(np.std(arr))
        if sigma == 0.0:
            return 0.0
        z = (arr[-1] - mu) / sigma
        # Ensure finite
        if not np.isfinite(z):
            return 0.0
        return float(z)

    def _realized_vol(self, closes: np.ndarray, window: int) -> float:
        """Realized volatility over last `window` bars: sqrt(sum(logret^2))."""
        if closes is None or len(closes) < 2:
            return 0.0
        rets = np.diff(np.log(closes))  # length n-1
        if rets.size == 0:
            return 0.0
        use = rets[-min(window, len(rets)) :]
        rv = float(np.sqrt(np.sum(use ** 2)))
        if not np.isfinite(rv):
            return 0.0
        return max(0.0, rv)

    def compute_phase11_features(self, candles: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute Phase 1.1 indicators: RSI14, ATR14, session VWAP, z_vwap, rv_30m."""
        if not candles:
            return {"rsi14": 50.0, "atr14": 0.0, "vwap": 0.0, "z_vwap": 0.0, "rv_30m": 0.0}
        closes = np.array([float(c['close']) for c in candles], dtype=float)
        highs = np.array([float(c['high']) for c in candles], dtype=float)
        lows = np.array([float(c['low']) for c in candles], dtype=float)
        # RSI(14)
        rsi_val = self._rsi_wilder(closes, self.window_rsi)
        # ATR(14)
        atr_val = self._atr_ewm(highs, lows, closes, self.window_atr)
        # Session VWAP
        vwap_val = self._session_vwap_current(candles)
        # Z-score to VWAP (50)
        z_vwap_val = self._zscore_to_vwap(candles, self.window_z_vwap)
        # Realized vol over last 30 bars
        rv_val = self._realized_vol(closes, self.window_rv)
        # Extras: CCI(20), StochRSI(14,3,3), MFI(14)
        cci_val = self._cci(highs, lows, closes, period=20)
        stoch_k, stoch_d = self._stochrsi(closes, rsi_period=14, k_period=3, d_period=3)
        mfi_val = self._mfi(highs, lows, closes, np.array([float(c['volume']) for c in candles]), period=14)
        return {
            "rsi14": float(rsi_val),
            "atr14": float(atr_val),
            "vwap": float(vwap_val),
            "z_vwap": float(z_vwap_val),
            "rv_30m": float(rv_val),
            "cci20": float(cci_val),
            "stochrsi_k": float(stoch_k),
            "stochrsi_d": float(stoch_d),
            "mfi14": float(mfi_val),
        }
    
    def compute_latest(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute all features for the latest data.
        
        Args:
            candles: List of candle dictionaries with OHLCV data
            
        Returns:
            Complete feature dictionary including baseline and expansion features
        """
        # Compute baseline features
        baseline_features = self.compute_baseline_features(candles)
        
        # Compute expansion features
        expansion_features = self.compute_expansion_features(candles)
        # Compute Phase 1.1 baseline indicators
        phase11 = self.compute_phase11_features(candles)
        
        # Combine all features
        all_features = {**baseline_features, **expansion_features, **phase11}
        
        # Add metadata
        if candles:
            all_features['timestamp'] = candles[-1].get('timestamp', 0)
            all_features['symbol'] = candles[-1].get('symbol', 'unknown')
        
        logger.debug(f"Computed {len(all_features)} features for {len(candles)} candles")
        return all_features
    
    def _empty_baseline_features(self) -> Dict[str, float]:
        """Return empty baseline features when no data is available."""
        return {
            "price": 0.0,
            "price_change": 0.0,
            "price_change_pct": 0.0,
            "high_low_range": 0.0,
            "high_low_range_pct": 0.0,
            "volume": 0.0,
            "avg_volume": 0.0,
            "volume_ratio": 1.0
        }

    # ---- Extras: CCI, StochRSI, MFI ----
    def _cci(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20) -> float:
        n = len(closes)
        if n < period:
            return 0.0
        tp = (highs + lows + closes) / 3.0
        sma = np.mean(tp[-period:])
        md = np.mean(np.abs(tp[-period:] - sma)) if period > 0 else 0.0
        if md == 0:
            return 0.0
        return float((tp[-1] - sma) / (0.015 * md))

    def _stochrsi(self, closes: np.ndarray, rsi_period: int = 14, k_period: int = 3, d_period: int = 3) -> (float, float):
        if len(closes) < rsi_period + max(k_period, d_period):
            return 0.0, 0.0
        # Compute RSI series
        diffs = np.diff(closes)
        gains = np.where(diffs > 0, diffs, 0.0)
        losses = np.where(diffs < 0, -diffs, 0.0)
        rsi_vals = []
        if len(diffs) < rsi_period:
            return 0.0, 0.0
        avg_gain = np.mean(gains[:rsi_period])
        avg_loss = np.mean(losses[:rsi_period])
        def rsi_from(gl, ll):
            if ll == 0:
                return 100.0 if gl > 0 else 50.0
            rs = gl/ll
            return 100.0 - (100.0/(1.0+rs))
        rsi_vals.append(rsi_from(avg_gain, avg_loss))
        for i in range(rsi_period, len(diffs)):
            avg_gain = ((avg_gain * (rsi_period - 1)) + gains[i]) / rsi_period
            avg_loss = ((avg_loss * (rsi_period - 1)) + losses[i]) / rsi_period
            rsi_vals.append(rsi_from(avg_gain, avg_loss))
        rsi_arr = np.array(rsi_vals, dtype=float)
        # Stochastic of RSI over last rsi_period window
        window = rsi_arr[-rsi_period:]
        rmax, rmin = np.max(window), np.min(window)
        denom = (rmax - rmin)
        stoch_rsi = 0.0 if denom == 0 else (rsi_arr[-1] - rmin) / denom
        # Smooth K and D with simple moving average over last k_period and d_period
        # Build last series of stoch_rsi (approximate with repeated values)
        k_series = np.array([stoch_rsi] * k_period)
        d_series = np.array([stoch_rsi] * d_period)
        k = float(np.mean(k_series))
        d = float(np.mean(d_series))
        return k, d

    def _mfi(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray, period: int = 14) -> float:
        n = len(closes)
        if n < period + 1:
            return 50.0
        tp = (highs + lows + closes) / 3.0
        pos_flow = 0.0
        neg_flow = 0.0
        for i in range(n - period, n):
            if i == 0:
                continue
            if tp[i] > tp[i - 1]:
                pos_flow += tp[i] * volumes[i]
            elif tp[i] < tp[i - 1]:
                neg_flow += tp[i] * volumes[i]
        if neg_flow == 0:
            return 100.0
        mr = pos_flow / neg_flow
        mfi = 100.0 - (100.0 / (1.0 + mr))
        return float(np.clip(mfi, 0.0, 100.0))
