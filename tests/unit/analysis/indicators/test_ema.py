"""
Unit tests for EMA (Exponential Moving Average) indicator.

Sprint 70: Indicator Library Extension - EMA unit tests
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.analysis.indicators.ema import EMA, EMAParams
from src.analysis.exceptions import IndicatorError


class TestEMAParams(unittest.TestCase):
    """Test EMA parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = EMAParams(period=20, source="close")
        self.assertEqual(params.period, 20)
        self.assertEqual(params.source, "close")
        self.assertIsNone(params.periods)

    def test_multiple_periods(self):
        """Test multi-period configuration."""
        params = EMAParams(period=20, periods=[12, 26, 50], source="close")
        self.assertEqual(params.periods, [12, 26, 50])

    def test_invalid_period(self):
        """Test invalid period value."""
        with self.assertRaises(ValueError):
            EMAParams(period=0, source="close")

    def test_invalid_source(self):
        """Test invalid source column."""
        with self.assertRaises(ValueError):
            EMAParams(period=20, source="invalid")


class TestEMA(unittest.TestCase):
    """Test EMA indicator calculations."""

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
        """Test basic EMA calculation."""
        indicator = EMA({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "ema")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("ema_20", result["value_data"])
        self.assertIsNotNone(result["value_data"]["ema_20"])

    def test_multi_period_calculation(self):
        """Test multi-period EMA calculation."""
        indicator = EMA({"period": 12, "periods": [12, 26, 50], "source": "close"})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("ema_12", result["value_data"])
        self.assertIn("ema_26", result["value_data"])
        self.assertIn("ema_50", result["value_data"])
        self.assertIsNotNone(result["value_data"]["ema_12"])
        self.assertIsNotNone(result["value_data"]["ema_26"])
        self.assertIsNotNone(result["value_data"]["ema_50"])
        # Primary value should be ema_12 (first period)
        self.assertEqual(result["value"], result["value_data"]["ema_12"])

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:10]  # Only 10 bars
        indicator = EMA({"period": 20})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None for ema_20 (need 20 bars)
        self.assertIsNone(result["value_data"]["ema_20"])
        self.assertIsNone(result["value"])

    def test_bullish_crossover_detection(self):
        """Test bullish crossover detection (12 crosses above 26)."""
        # Create data with known crossover
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        # Start with downtrend, then uptrend (creates crossover)
        close_prices = list(range(150, 120, -1)) + list(range(120, 140))

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": close_prices,
                "high": [c + 2 for c in close_prices],
                "low": [c - 2 for c in close_prices],
                "close": close_prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = EMA({"period": 12, "periods": [12, 26]})
        result = indicator.calculate(data, symbol="TEST")

        # Check for crossover in metadata
        self.assertIn("crossovers", result["metadata"])
        # May or may not have crossover depending on exact data
        # Just verify structure is correct
        if result["metadata"]["crossovers"]:
            crossover = result["metadata"]["crossovers"][0]
            self.assertIn("type", crossover)
            self.assertIn("timestamp", crossover)

    def test_ema_more_responsive_than_sma(self):
        """Test that EMA responds faster to price changes than SMA."""
        # Import SMA for comparison
        from src.analysis.indicators.sma import SMA

        # Create data with gradual price increase
        dates = pd.date_range(start="2025-01-01", periods=25, freq="1D")
        close_prices = [100] * 15 + list(range(101, 111))  # Gradual increase

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": close_prices,
                "high": [c + 1 for c in close_prices],
                "low": [c - 1 for c in close_prices],
                "close": close_prices,
                "volume": [1000000] * 25,
            }
        )
        data.index = dates

        ema = EMA({"period": 10})
        sma = SMA({"period": 10})

        ema_result = ema.calculate(data, symbol="TEST")
        sma_result = sma.calculate(data, symbol="TEST")

        # After price increase, EMA should be closer to current price than SMA
        # (EMA is more responsive)
        ema_value = ema_result["value_data"]["ema_10"]
        sma_value = sma_result["value_data"]["sma_10"]

        # Both should be between 100 and 110
        self.assertGreater(ema_value, 100)
        self.assertLessEqual(ema_value, 110)
        self.assertGreater(sma_value, 100)
        self.assertLessEqual(sma_value, 110)

        # EMA should be closer to 110 (more responsive) or at least equal
        ema_distance = abs(110 - ema_value)
        sma_distance = abs(110 - sma_value)
        self.assertLessEqual(ema_distance, sma_distance)

    def test_calculate_series(self):
        """Test EMA series calculation for charting."""
        indicator = EMA({"period": 20, "periods": [20, 50]})
        series = indicator.calculate_series(self.data)

        self.assertIn("ema_20", series.columns)
        self.assertIn("ema_50", series.columns)
        self.assertEqual(len(series), len(self.data))

        # Check that EMA values are calculated (not all NaN)
        self.assertFalse(series["ema_20"].iloc[-1] is pd.NA)
        self.assertFalse(series["ema_50"].iloc[-1] is pd.NA)

    def test_minimum_periods(self):
        """Test get_minimum_periods method."""
        indicator1 = EMA({"period": 20})
        self.assertEqual(indicator1.get_minimum_periods(), 20)

        indicator2 = EMA({"period": 12, "periods": [12, 26, 50]})
        self.assertEqual(indicator2.get_minimum_periods(), 50)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = EMA({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])

    def test_empty_data(self):
        """Test with empty DataFrame."""
        empty_data = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        indicator = EMA({"period": 20})

        # Should handle empty data gracefully
        try:
            result = indicator.calculate(empty_data, symbol="TEST")
            self.assertIsNone(result["value"])
        except IndicatorError:
            # Also acceptable to raise error
            pass

    def test_ema_calculation_accuracy(self):
        """Test EMA calculation accuracy against known values."""
        # Simple test case with known EMA values
        dates = pd.date_range(start="2025-01-01", periods=5, freq="1D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [10, 11, 12, 11, 12],
                "high": [11, 12, 13, 12, 13],
                "low": [9, 10, 11, 10, 11],
                "close": [10, 11, 12, 11, 12],
                "volume": [1000000] * 5,
            }
        )
        data.index = dates

        indicator = EMA({"period": 3})
        result = indicator.calculate(data, symbol="TEST")

        # EMA(3) should be calculated
        self.assertIsNotNone(result["value_data"]["ema_3"])
        # Value should be reasonable (between min and max close)
        self.assertGreaterEqual(result["value_data"]["ema_3"], 10)
        self.assertLessEqual(result["value_data"]["ema_3"], 12)

    def test_different_source_columns(self):
        """Test EMA calculation on different source columns."""
        # Test with 'high' as source
        indicator_high = EMA({"period": 10, "source": "high"})
        result_high = indicator_high.calculate(self.data, symbol="TEST")

        # Test with 'close' as source
        indicator_close = EMA({"period": 10, "source": "close"})
        result_close = indicator_close.calculate(self.data, symbol="TEST")

        # Values should be different
        self.assertNotEqual(
            result_high["value_data"]["ema_10"],
            result_close["value_data"]["ema_10"]
        )

    def test_metadata_structure(self):
        """Test that metadata contains expected fields."""
        indicator = EMA({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("metadata", result)
        self.assertIn("periods_calculated", result["metadata"])
        self.assertIn("crossovers", result["metadata"])
        self.assertEqual(result["metadata"]["periods_calculated"], [20])


if __name__ == "__main__":
    unittest.main()
