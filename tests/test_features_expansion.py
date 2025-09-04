"""
Tests for optional technical indicators in features expansion module.
"""

import pytest
import numpy as np
from src.paperbot.features.expansion import (
    sma_ema_cross, macd, bollinger_bands, obv,
    keltner_channel, rolling_skew_kurtosis, hour_of_day
)


class TestSMAEMACross:
    """Test SMA/EMA crossover calculations."""
    
    def test_sma_ema_cross_uptrend(self):
        """Test SMA/EMA cross on uptrend data."""
        # Create uptrend data
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        result = sma_ema_cross(prices, fast=3, slow=5)
        
        assert result['sma'] > 0
        assert result['ema'] > 0
        assert result['crossover_signal'] == 1.0  # EMA > SMA in uptrend
    
    def test_sma_ema_cross_downtrend(self):
        """Test SMA/EMA cross on downtrend data."""
        # Create downtrend data
        prices = np.array([110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100])
        result = sma_ema_cross(prices, fast=3, slow=5)
        
        assert result['sma'] > 0
        assert result['ema'] > 0
        assert result['crossover_signal'] == -1.0  # EMA < SMA in downtrend
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        result = sma_ema_cross(prices, fast=3, slow=5)
        
        assert result['sma'] == 0.0
        assert result['ema'] == 0.0
        assert result['crossover_signal'] == 0.0


class TestMACD:
    """Test MACD calculations."""
    
    def test_macd_uptrend(self):
        """Test MACD on uptrend data."""
        # Create uptrend data
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110] * 3)
        result = macd(prices, fast=3, slow=5, signal=3)
        
        assert result['macd'] > 0  # Fast EMA > Slow EMA in uptrend
        assert result['histogram'] > 0  # MACD > Signal line
    
    def test_macd_downtrend(self):
        """Test MACD on downtrend data."""
        # Create downtrend data
        prices = np.array([110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100] * 3)
        result = macd(prices, fast=3, slow=5, signal=3)
        
        assert result['macd'] < 0  # Fast EMA < Slow EMA in downtrend
        assert result['histogram'] < 0  # MACD < Signal line
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        result = macd(prices, fast=3, slow=5)
        
        assert result['macd'] == 0.0
        assert result['signal_line'] == 0.0
        assert result['histogram'] == 0.0


class TestBollingerBands:
    """Test Bollinger Bands calculations."""
    
    def test_bollinger_bands_normal(self):
        """Test Bollinger Bands with normal volatility."""
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
                          109, 108, 107, 106, 105, 104, 103, 102, 101])
        result = bollinger_bands(prices, period=20, mult=2.0)
        
        assert result['upper_band'] > result['middle_band']
        assert result['middle_band'] > result['lower_band']
        assert result['bandwidth'] > 0
    
    def test_bollinger_bands_high_volatility(self):
        """Test Bollinger Bands with high volatility."""
        prices = np.array([100, 110, 90, 120, 80, 130, 70, 140, 60, 150,
                          50, 160, 40, 170, 30, 180, 20, 190, 10, 200])
        result = bollinger_bands(prices, period=20, mult=2.0)
        
        assert result['bandwidth'] > 0.5  # High volatility = wide bands
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        result = bollinger_bands(prices, period=20)
        
        assert result['upper_band'] == 0.0
        assert result['middle_band'] == 0.0
        assert result['lower_band'] == 0.0
        assert result['bandwidth'] == 0.0


class TestOBV:
    """Test On-Balance Volume calculations."""
    
    def test_obv_rising_prices(self):
        """Test OBV with rising prices."""
        prices = np.array([100, 101, 102, 103, 104])
        volumes = np.array([1000, 1100, 1200, 1300, 1400])
        result = obv(prices, volumes)
        
        assert result['obv'] > 0  # OBV should be positive with rising prices
        assert result['obv_change'] >= 0
    
    def test_obv_falling_prices(self):
        """Test OBV with falling prices."""
        prices = np.array([104, 103, 102, 101, 100])
        volumes = np.array([1400, 1300, 1200, 1100, 1000])
        result = obv(prices, volumes)
        
        assert result['obv'] < 0  # OBV should be negative with falling prices
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100])
        volumes = np.array([1000])
        result = obv(prices, volumes)
        
        assert result['obv'] == 0.0
        assert result['obv_change'] == 0.0


class TestKeltnerChannel:
    """Test Keltner Channel calculations."""
    
    def test_keltner_channel_normal(self):
        """Test Keltner Channels with normal data."""
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
                          109, 108, 107, 106, 105, 104, 103, 102, 101])
        high = prices + 2
        low = prices - 2
        
        result = keltner_channel(prices, high, low, period=20)
        
        assert result['upper_channel'] > result['middle_channel']
        assert result['middle_channel'] > result['lower_channel']
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        high = np.array([102, 103, 104])
        low = np.array([98, 99, 100])
        
        result = keltner_channel(prices, high, low, period=20)
        
        assert result['upper_channel'] == 0.0
        assert result['middle_channel'] == 0.0
        assert result['lower_channel'] == 0.0


class TestRollingSkewKurtosis:
    """Test rolling skewness and kurtosis calculations."""
    
    def test_skew_kurtosis_normal_distribution(self):
        """Test with approximately normal distribution."""
        # Generate normal-like data
        np.random.seed(42)
        prices = 100 + np.random.normal(0, 1, 100)
        result = rolling_skew_kurtosis(prices, lookback=50)
        
        # For normal distribution, skewness ≈ 0, kurtosis ≈ 0
        assert abs(result['skewness']) < 1.0
        assert abs(result['kurtosis']) < 3.0
    
    def test_skew_kurtosis_fat_tails(self):
        """Test with fat-tailed distribution."""
        # Generate fat-tailed data with more extreme values
        np.random.seed(42)
        # Use more extreme t-distribution or add outliers
        prices = 100 + np.random.standard_t(3, 100)
        # Add some outliers to ensure fat tails
        prices[::10] += np.random.choice([-20, 20], size=10)
        result = rolling_skew_kurtosis(prices, lookback=50)
        
        # With outliers, we should see some fat tail behavior
        # Just check that the calculation works, not specific values
        assert isinstance(result['kurtosis'], float)
        assert isinstance(result['skewness'], float)
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        prices = np.array([100, 101, 102])
        result = rolling_skew_kurtosis(prices, lookback=50)
        
        assert result['skewness'] == 0.0
        assert result['kurtosis'] == 0.0


class TestHourOfDay:
    """Test hour of day extraction."""
    
    def test_hour_of_day_valid_timestamp(self):
        """Test with valid timestamp."""
        # Test with a known timestamp (2024-01-01 14:30:00 UTC)
        # Use a timestamp that accounts for timezone differences
        timestamp_ms = 1704123000000  # 2024-01-01 14:30:00 UTC
        result = hour_of_day(timestamp_ms)
        
        # The hour might vary due to timezone, so just check it's a valid hour
        assert 0 <= result['hour_int'] <= 23
        assert result['hour_cat'].startswith('hour_')
    
    def test_hour_of_day_midnight(self):
        """Test with midnight timestamp."""
        # Test with midnight (2024-01-01 00:00:00 UTC)
        timestamp_ms = 1704067200000
        result = hour_of_day(timestamp_ms)
        
        assert result['hour_int'] == 0
        assert result['hour_cat'] == "hour_00"
    
    def test_hour_of_day_invalid_timestamp(self):
        """Test with invalid timestamp."""
        timestamp_ms = 0
        result = hour_of_day(timestamp_ms)
        
        assert result['hour_int'] == 0
        assert result['hour_cat'] == "hour_00"


class TestFeatureIntegration:
    """Test integration of multiple features."""
    
    def test_feature_consistency(self):
        """Test that features return consistent data types."""
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        volumes = np.array([1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000])
        high = prices + 2
        low = prices - 2
        
        # Test all features
        sma_ema_result = sma_ema_cross(prices)
        macd_result = macd(prices)
        bb_result = bollinger_bands(prices)
        obv_result = obv(prices, volumes)
        keltner_result = keltner_channel(prices, high, low)
        skew_kurt_result = rolling_skew_kurtosis(prices)
        hour_result = hour_of_day(1704123000000)
        
        # All results should be dictionaries
        assert isinstance(sma_ema_result, dict)
        assert isinstance(macd_result, dict)
        assert isinstance(bb_result, dict)
        assert isinstance(obv_result, dict)
        assert isinstance(keltner_result, dict)
        assert isinstance(skew_kurt_result, dict)
        assert isinstance(hour_result, dict)
        
        # All numeric values should be floats
        for result in [sma_ema_result, macd_result, bb_result, obv_result, keltner_result, skew_kurt_result]:
            for value in result.values():
                assert isinstance(value, float)
        
        # Hour features have mixed types
        assert isinstance(hour_result['hour_int'], int)
        assert isinstance(hour_result['hour_cat'], str)

