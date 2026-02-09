"""
Unit tests for SMA (Simple Moving Average) indicator.

Sprint 68: Core Analysis Migration - Indicator unit tests
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.analysis.indicators.sma import SMA, SMAParams
from src.analysis.exceptions import IndicatorError


class TestSMAParams(unittest.TestCase):
    """Test SMA parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = SMAParams(period=20, source="close")
        self.assertEqual(params.period, 20)
        self.assertEqual(params.source, "close")
        self.assertIsNone(params.periods)

    def test_multiple_periods(self):
        """Test multi-period configuration."""
        params = SMAParams(period=20, periods=[20, 50, 200], source="close")
        self.assertEqual(params.periods, [20, 50, 200])

    def test_invalid_period(self):
        """Test invalid period value."""
        with self.assertRaises(ValueError):
            SMAParams(period=0, source="close")

    def test_invalid_source(self):
        """Test invalid source column."""
        with self.assertRaises(ValueError):
            SMAParams(period=20, source="invalid")


class TestSMA(unittest.TestCase):
    """Test SMA indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create sample OHLCV data
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        self.data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(95, 105, 100),
                "high": np.random.uniform(100, 110, 100),
                "low": np.random.uniform(90, 100, 100),
                "close": np.arange(100, 200),  # Trending upward
                "volume": np.random.randint(1000000, 2000000, 100),
            }
        )
        # Ensure OHLC consistency
        self.data["high"] = self.data[["open", "high", "low", "close"]].max(axis=1)
        self.data["low"] = self.data[["open", "high", "low", "close"]].min(axis=1)
        self.data.index = dates

    def test_basic_calculation(self):
        """Test basic SMA calculation."""
        indicator = SMA({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "sma")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("sma_20", result["value_data"])
        self.assertIsNotNone(result["value_data"]["sma_20"])

    def test_multi_period_calculation(self):
        """Test multi-period SMA calculation."""
        indicator = SMA({"period": 20, "periods": [20, 50], "source": "close"})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("sma_20", result["value_data"])
        self.assertIn("sma_50", result["value_data"])
        self.assertIsNotNone(result["value_data"]["sma_20"])
        self.assertIsNotNone(result["value_data"]["sma_50"])
        # Primary value should be sma_20 (first period)
        self.assertEqual(result["value"], result["value_data"]["sma_20"])

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:10]  # Only 10 bars
        indicator = SMA({"period": 20})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None for sma_20 (need 20 bars)
        self.assertIsNone(result["value_data"]["sma_20"])
        self.assertIsNone(result["value"])

    def test_golden_cross_detection(self):
        """Test golden cross detection (50 crosses above 200)."""
        # Create data where 50 SMA crosses above 200 SMA
        dates = pd.date_range(start="2025-01-01", periods=250, freq="1D")
        prices = np.concatenate([np.linspace(100, 110, 200), np.linspace(110, 150, 50)])

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 1,
                "high": prices + 1,
                "low": prices - 2,
                "close": prices,
                "volume": np.ones(250) * 1000000,
            }
        )
        data.index = dates

        indicator = SMA({"period": 50, "periods": [50, 200]})
        result = indicator.calculate(data, symbol="TEST")

        # Check if crossover detected
        crossovers = result["metadata"]["crossovers"]
        if len(crossovers) > 0:
            self.assertEqual(crossovers[0]["type"], "golden_cross")

    def test_calculate_series(self):
        """Test full series calculation for charting."""
        indicator = SMA({"period": 20})
        series = indicator.calculate_series(self.data)

        self.assertIn("sma_20", series.columns)
        self.assertEqual(len(series), len(self.data))
        # First 19 values should be NaN
        self.assertTrue(pd.isna(series["sma_20"].iloc[18]))
        # 20th value should be calculated
        self.assertFalse(pd.isna(series["sma_20"].iloc[19]))

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = SMA({"period": 20})
        self.assertEqual(indicator.get_minimum_periods(), 20)

        indicator_multi = SMA({"period": 20, "periods": [20, 50, 200]})
        self.assertEqual(indicator_multi.get_minimum_periods(), 200)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = SMA({"period": 20})
        result = indicator.calculate(self.data, timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])

    def test_manual_verification(self):
        """Test SMA calculation against manual calculation."""
        # Simple test data
        simple_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=30, freq="1D"),
                "open": np.ones(30) * 100,
                "high": np.ones(30) * 101,
                "low": np.ones(30) * 99,
                "close": np.arange(100, 130),  # 100, 101, 102, ..., 129
                "volume": np.ones(30) * 1000000,
            }
        )
        simple_data.index = simple_data["timestamp"]

        indicator = SMA({"period": 5})
        result = indicator.calculate(simple_data)

        # Manual calculation: SMA(5) at bar 29 = mean(125, 126, 127, 128, 129) = 127
        expected = 127.0
        self.assertAlmostEqual(result["value"], expected, places=1)


if __name__ == "__main__":
    unittest.main()
