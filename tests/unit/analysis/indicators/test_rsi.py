"""
Unit tests for RSI (Relative Strength Index) indicator.

Sprint 68: Core Analysis Migration - Indicator unit tests
"""

import unittest
from datetime import datetime

import numpy as np
import pandas as pd

from src.analysis.indicators.rsi import RSI, RSIParams
from src.analysis.exceptions import IndicatorError


class TestRSIParams(unittest.TestCase):
    """Test RSI parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = RSIParams(period=14, overbought=70.0, oversold=30.0)
        self.assertEqual(params.period, 14)
        self.assertEqual(params.overbought, 70.0)
        self.assertEqual(params.oversold, 30.0)

    def test_invalid_overbought(self):
        """Test invalid overbought threshold."""
        with self.assertRaises(ValueError):
            RSIParams(period=14, overbought=105.0)

    def test_invalid_oversold(self):
        """Test invalid oversold threshold."""
        with self.assertRaises(ValueError):
            RSIParams(period=14, oversold=-10.0)

    def test_oversold_greater_than_overbought(self):
        """Test oversold >= overbought."""
        with self.assertRaises(ValueError):
            RSIParams(period=14, overbought=30.0, oversold=70.0)


class TestRSI(unittest.TestCase):
    """Test RSI indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create trending data for RSI calculation
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        # Uptrend followed by downtrend
        prices = np.concatenate(
            [
                np.linspace(100, 150, 50),  # Uptrend
                np.linspace(150, 120, 50),  # Downtrend
            ]
        )

        self.data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 1,
                "high": prices + 1,
                "low": prices - 2,
                "close": prices,
                "volume": np.random.randint(1000000, 2000000, 100),
            }
        )
        # Ensure OHLC consistency
        self.data["high"] = self.data[["open", "high", "low", "close"]].max(axis=1)
        self.data["low"] = self.data[["open", "high", "low", "close"]].min(axis=1)
        self.data.index = dates

    def test_basic_calculation(self):
        """Test basic RSI calculation."""
        indicator = RSI({"period": 14})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "rsi")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("rsi_14", result["value_data"])
        # RSI should be between 0 and 100
        self.assertGreaterEqual(result["value"], 0.0)
        self.assertLessEqual(result["value"], 100.0)

    def test_overbought_detection(self):
        """Test overbought signal detection."""
        # Create strongly uptrending data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = np.linspace(100, 200, 50)  # Strong uptrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 1,
                "high": prices + 1,
                "low": prices - 2,
                "close": prices,
                "volume": np.ones(50) * 1000000,
            }
        )
        data.index = dates

        indicator = RSI({"period": 14, "overbought": 70.0})
        result = indicator.calculate(data)

        # Strong uptrend should produce high RSI
        self.assertGreater(result["value"], 60.0)  # Should be relatively high

    def test_oversold_detection(self):
        """Test oversold signal detection."""
        # Create strongly downtrending data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = np.linspace(200, 100, 50)  # Strong downtrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 1,
                "high": prices + 1,
                "low": prices - 2,
                "close": prices,
                "volume": np.ones(50) * 1000000,
            }
        )
        data.index = dates

        indicator = RSI({"period": 14, "oversold": 30.0})
        result = indicator.calculate(data)

        # Strong downtrend should produce low RSI
        self.assertLess(result["value"], 40.0)  # Should be relatively low

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:10]  # Only 10 bars, need 15 (period + 1)
        indicator = RSI({"period": 14})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None
        self.assertIsNone(result["value"])
        self.assertIsNone(result["value_data"]["rsi_14"])

    def test_calculate_series(self):
        """Test full series calculation."""
        indicator = RSI({"period": 14})
        series = indicator.calculate_series(self.data)

        self.assertEqual(len(series), len(self.data))
        # RSI fills NaN with 100.0, so all values should be non-NaN
        self.assertFalse(pd.isna(series.iloc[13]))
        self.assertFalse(pd.isna(series.iloc[14]))
        # All values should be between 0 and 100
        self.assertTrue((series >= 0).all())
        self.assertTrue((series <= 100).all())

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = RSI({"period": 14})
        # RSI needs period + 1 bars
        self.assertEqual(indicator.get_minimum_periods(), 15)

    def test_wilder_smoothing(self):
        """Test that Wilder's smoothing is used correctly."""
        # Create data with known gains/losses
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = np.array([100] * 20 + [101] * 30)  # Step change

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(50) * 1000000,
            }
        )
        data.index = dates

        indicator = RSI({"period": 14})
        result = indicator.calculate(data)

        # After upward move, RSI should be > 50
        self.assertGreater(result["value"], 50.0)

    def test_sma_mode(self):
        """Test RSI with SMA smoothing instead of Wilder's."""
        indicator_wilder = RSI({"period": 14, "use_sma": False})
        indicator_sma = RSI({"period": 14, "use_sma": True})

        result_wilder = indicator_wilder.calculate(self.data)
        result_sma = indicator_sma.calculate(self.data)

        # Both should produce valid RSI
        self.assertIsNotNone(result_wilder["value"])
        self.assertIsNotNone(result_sma["value"])
        # Values should be different
        self.assertNotEqual(result_wilder["value"], result_sma["value"])

    def test_extreme_uptrend(self):
        """Test RSI approaches 100 in extreme uptrend."""
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = 100 + np.arange(50) * 2  # Consistent gains

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(50) * 1000000,
            }
        )
        data.index = dates

        indicator = RSI({"period": 14})
        result = indicator.calculate(data)

        # Should be high but not necessarily 100
        self.assertGreater(result["value"], 70.0)
        self.assertLessEqual(result["value"], 100.0)

    def test_extreme_downtrend(self):
        """Test RSI approaches 0 in extreme downtrend."""
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = 200 - np.arange(50) * 2  # Consistent losses

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(50) * 1000000,
            }
        )
        data.index = dates

        indicator = RSI({"period": 14})
        result = indicator.calculate(data)

        # Should be low but not necessarily 0
        self.assertLess(result["value"], 30.0)
        self.assertGreaterEqual(result["value"], 0.0)


if __name__ == "__main__":
    unittest.main()
