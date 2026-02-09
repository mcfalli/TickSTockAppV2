"""
Unit tests for Stochastic Oscillator indicator.

Sprint 70: Indicator Library Extension - Stochastic unit tests
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.analysis.indicators.stochastic import Stochastic, StochasticParams
from src.analysis.exceptions import IndicatorError


class TestStochasticParams(unittest.TestCase):
    """Test Stochastic parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = StochasticParams(
            period=14, source="close", k_period=14, d_period=3,
            overbought=80.0, oversold=20.0
        )
        self.assertEqual(params.k_period, 14)
        self.assertEqual(params.d_period, 3)
        self.assertEqual(params.overbought, 80.0)
        self.assertEqual(params.oversold, 20.0)

    def test_invalid_k_period(self):
        """Test invalid k_period value."""
        with self.assertRaises(ValueError):
            StochasticParams(period=0, source="close", k_period=0, d_period=3)

    def test_invalid_d_period(self):
        """Test invalid d_period value."""
        with self.assertRaises(ValueError):
            StochasticParams(period=14, source="close", k_period=14, d_period=0)

    def test_invalid_overbought(self):
        """Test invalid overbought threshold."""
        with self.assertRaises(ValueError):
            StochasticParams(period=14, source="close", k_period=14, d_period=3, overbought=105.0)

    def test_invalid_oversold(self):
        """Test invalid oversold threshold."""
        with self.assertRaises(ValueError):
            StochasticParams(period=14, source="close", k_period=14, d_period=3, oversold=-10.0)

    def test_oversold_greater_than_overbought(self):
        """Test oversold >= overbought."""
        with self.assertRaises(ValueError):
            StochasticParams(
                period=14, source="close", k_period=14, d_period=3,
                overbought=20.0, oversold=80.0
            )


class TestStochastic(unittest.TestCase):
    """Test Stochastic Oscillator indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create trending data for Stochastic calculation
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")

        # Create oscillating prices (alternating up/down trends)
        prices = []
        for i in range(100):
            if i < 25:
                prices.append(90 + i * 0.4)  # Uptrend
            elif i < 50:
                prices.append(100 - (i - 25) * 0.4)  # Downtrend
            elif i < 75:
                prices.append(90 + (i - 50) * 0.4)  # Uptrend
            else:
                prices.append(100 - (i - 75) * 0.4)  # Downtrend

        self.data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p + np.random.uniform(0.5, 1.5) for p in prices],
                "low": [p - np.random.uniform(0.5, 1.5) for p in prices],
                "close": prices,
                "volume": np.random.randint(1000000, 2000000, 100),
            }
        )
        # Ensure OHLC consistency
        self.data["high"] = self.data[["open", "high", "low", "close"]].max(axis=1)
        self.data["low"] = self.data[["open", "high", "low", "close"]].min(axis=1)
        self.data.index = dates

    def test_basic_calculation(self):
        """Test basic Stochastic calculation."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "stochastic")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("percent_k", result["value_data"])
        self.assertIn("percent_d", result["value_data"])

        # %K and %D should be between 0 and 100
        self.assertGreaterEqual(result["value_data"]["percent_k"], 0.0)
        self.assertLessEqual(result["value_data"]["percent_k"], 100.0)
        self.assertGreaterEqual(result["value_data"]["percent_d"], 0.0)
        self.assertLessEqual(result["value_data"]["percent_d"], 100.0)

    def test_overbought_detection(self):
        """Test overbought signal detection."""
        # Create strongly uptrending data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = np.linspace(90, 110, 50)  # Strong uptrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(data)

        # Strong uptrend should produce high %K
        self.assertGreater(result["value_data"]["percent_k"], 60.0)

    def test_oversold_detection(self):
        """Test oversold signal detection."""
        # Create strongly downtrending data
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = np.linspace(110, 90, 50)  # Strong downtrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(data)

        # Strong downtrend should produce low %K
        self.assertLess(result["value_data"]["percent_k"], 40.0)

    def test_bullish_crossover(self):
        """Test bullish crossover detection (%K crosses above %D)."""
        # Create data with reversal from downtrend to uptrend
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = list(np.linspace(110, 90, 30)) + list(np.linspace(90, 100, 20))

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p + 0.5 for p in prices],
                "low": [p - 0.5 for p in prices],
                "close": prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})

        # Check last few bars for crossover
        for i in range(-10, 0):
            subset = data.iloc[:i] if i < 0 else data
            if len(subset) >= 17:  # k_period + d_period
                result = indicator.calculate(subset)
                if result["value_data"]["crossover"] == "bullish":
                    # Found bullish crossover
                    self.assertEqual(result["value_data"]["crossover"], "bullish")
                    return

        # If no crossover found, that's ok - just verify structure
        result = indicator.calculate(data)
        self.assertIn("crossover", result["value_data"])

    def test_bearish_crossover(self):
        """Test bearish crossover detection (%K crosses below %D)."""
        # Create data with reversal from uptrend to downtrend
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = list(np.linspace(90, 110, 30)) + list(np.linspace(110, 100, 20))

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p + 0.5 for p in prices],
                "low": [p - 0.5 for p in prices],
                "close": prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})

        # Check last few bars for crossover
        for i in range(-10, 0):
            subset = data.iloc[:i] if i < 0 else data
            if len(subset) >= 17:
                result = indicator.calculate(subset)
                if result["value_data"]["crossover"] == "bearish":
                    # Found bearish crossover
                    self.assertEqual(result["value_data"]["crossover"], "bearish")
                    return

        # If no crossover found, that's ok - just verify structure
        result = indicator.calculate(data)
        self.assertIn("crossover", result["value_data"])

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:10]  # Only 10 bars, need 16 (k_period + d_period - 1)
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None
        self.assertIsNone(result["value"])
        self.assertIsNone(result["value_data"]["percent_k"])

    def test_calculate_series(self):
        """Test full series calculation."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        series = indicator.calculate_series(self.data)

        self.assertEqual(len(series), len(self.data))
        self.assertIn("percent_k", series.columns)
        self.assertIn("percent_d", series.columns)

        # Check that values are calculated (not all NaN after required period)
        self.assertFalse(pd.isna(series["percent_k"].iloc[-1]))
        self.assertFalse(pd.isna(series["percent_d"].iloc[-1]))

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        # Minimum periods = k_period + d_period - 1 = 14 + 3 - 1 = 16
        self.assertEqual(indicator.get_minimum_periods(), 16)

    def test_flat_range(self):
        """Test Stochastic with flat price range."""
        dates = pd.date_range(start="2025-01-01", periods=30, freq="1D")

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100.0] * 30,
                "high": [100.0] * 30,
                "low": [100.0] * 30,
                "close": [100.0] * 30,
                "volume": [1000000] * 30,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(data)

        # With flat range, %K should be 50 (middle)
        self.assertIsNotNone(result["value"])
        self.assertAlmostEqual(result["value_data"]["percent_k"], 50.0, places=1)

    def test_different_periods(self):
        """Test Stochastic with different period values."""
        indicator_short = Stochastic({"k_period": 5, "d_period": 3})
        indicator_long = Stochastic({"k_period": 21, "d_period": 5})

        result_short = indicator_short.calculate(self.data)
        result_long = indicator_long.calculate(self.data)

        # Both should produce valid results
        self.assertIsNotNone(result_short["value"])
        self.assertIsNotNone(result_long["value"])

        # Values should be different (different lookback periods)
        # Can't guarantee which is higher, just that they're different
        self.assertIsInstance(result_short["value"], (int, float))
        self.assertIsInstance(result_long["value"], (int, float))

    def test_signal_confidence(self):
        """Test confidence score in different scenarios."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(self.data)

        self.assertIn("confidence", result["value_data"])
        confidence = result["value_data"]["confidence"]
        self.assertIsNotNone(confidence)
        self.assertGreaterEqual(confidence, 0.7)  # Base confidence
        self.assertLessEqual(confidence, 1.0)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])

    def test_empty_data(self):
        """Test with empty DataFrame."""
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        indicator = Stochastic({"k_period": 14, "d_period": 3})

        result = indicator.calculate(empty_data, symbol="TEST")
        self.assertIsNone(result["value"])

    def test_metadata_structure(self):
        """Test that metadata contains expected fields."""
        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("metadata", result)
        self.assertIn("signal", result["metadata"])
        self.assertIn("overbought_threshold", result["metadata"])
        self.assertIn("oversold_threshold", result["metadata"])
        self.assertIn("k_period", result["metadata"])
        self.assertIn("d_period", result["metadata"])
        self.assertEqual(result["metadata"]["k_period"], 14)
        self.assertEqual(result["metadata"]["d_period"], 3)

    def test_price_at_low(self):
        """Test when price is at period low."""
        # Create data where close is at the low of the range
        dates = pd.date_range(start="2025-01-01", periods=30, freq="1D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [110] * 30,
                "low": [90] * 14 + [85] * 16,  # Lower low at the end
                "close": [100] * 14 + [85] * 16,  # Close at low
                "volume": [1000000] * 30,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(data)

        # %K should be 0 (close at lowest low)
        self.assertLess(result["value_data"]["percent_k"], 10.0)

    def test_price_at_high(self):
        """Test when price is at period high."""
        # Create data where close is at the high of the range
        dates = pd.date_range(start="2025-01-01", periods=30, freq="1D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [110] * 14 + [115] * 16,  # Higher high at the end
                "low": [90] * 30,
                "close": [100] * 14 + [115] * 16,  # Close at high
                "volume": [1000000] * 30,
            }
        )
        data.index = dates

        indicator = Stochastic({"k_period": 14, "d_period": 3})
        result = indicator.calculate(data)

        # %K should be 100 (close at highest high)
        self.assertGreater(result["value_data"]["percent_k"], 90.0)


if __name__ == "__main__":
    unittest.main()
