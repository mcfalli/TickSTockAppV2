"""
Unit tests for MACD (Moving Average Convergence Divergence) indicator.

Sprint 68: Core Analysis Migration - Indicator unit tests
"""

import unittest

import numpy as np
import pandas as pd

from src.analysis.indicators.macd import MACD, MACDParams
from src.analysis.exceptions import IndicatorError


class TestMACDParams(unittest.TestCase):
    """Test MACD parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = MACDParams(period=26, fast_period=12, slow_period=26, signal_period=9)
        self.assertEqual(params.fast_period, 12)
        self.assertEqual(params.slow_period, 26)
        self.assertEqual(params.signal_period, 9)

    def test_invalid_fast_period(self):
        """Test invalid fast period."""
        with self.assertRaises(ValueError):
            MACDParams(period=26, fast_period=0, slow_period=26, signal_period=9)

    def test_fast_greater_than_slow(self):
        """Test fast_period >= slow_period."""
        with self.assertRaises(ValueError):
            MACDParams(period=26, fast_period=26, slow_period=12, signal_period=9)


class TestMACD(unittest.TestCase):
    """Test MACD indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create trending data for MACD calculation
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
        """Test basic MACD calculation."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "macd")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("macd", result["value_data"])
        self.assertIn("signal", result["value_data"])
        self.assertIn("histogram", result["value_data"])
        # Primary value should be MACD line, NOT histogram
        self.assertEqual(result["value"], result["value_data"]["macd"])

    def test_bullish_crossover(self):
        """Test bullish crossover detection."""
        # Create data with crossover
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        prices = np.concatenate(
            [
                np.linspace(100, 90, 50),  # Downtrend
                np.linspace(90, 120, 50),  # Strong uptrend (crossover)
            ]
        )

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(100) * 1000000,
            }
        )
        data.index = dates

        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(data)

        # Should detect bullish signal at some point
        self.assertIn(result["value_data"]["macd_signal"], ["bullish", "bullish_crossover"])

    def test_bearish_crossover(self):
        """Test bearish crossover detection."""
        # Create data with bearish crossover
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        prices = np.concatenate(
            [
                np.linspace(100, 130, 50),  # Uptrend
                np.linspace(130, 90, 50),  # Strong downtrend (crossover)
            ]
        )

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(100) * 1000000,
            }
        )
        data.index = dates

        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(data)

        # Should detect bearish signal
        self.assertIn(result["value_data"]["macd_signal"], ["bearish", "bearish_crossover"])

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:20]  # Only 20 bars, need 35 (26 + 9)
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None values
        self.assertIsNone(result["value"])
        self.assertIsNone(result["value_data"]["macd"])
        self.assertIsNone(result["value_data"]["signal"])
        self.assertIsNone(result["value_data"]["histogram"])

    def test_calculate_series(self):
        """Test full series calculation."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        series_dict = indicator.calculate_series(self.data)

        self.assertIn("macd", series_dict)
        self.assertIn("signal", series_dict)
        self.assertIn("histogram", series_dict)

        macd_series = series_dict["macd"]
        signal_series = series_dict["signal"]
        histogram_series = series_dict["histogram"]

        self.assertEqual(len(macd_series), len(self.data))
        self.assertEqual(len(signal_series), len(self.data))
        self.assertEqual(len(histogram_series), len(self.data))

        # Histogram should equal MACD - Signal
        np.testing.assert_array_almost_equal(
            histogram_series.values, (macd_series - signal_series).values, decimal=10
        )

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        # MACD needs slow_period + signal_period bars
        self.assertEqual(indicator.get_minimum_periods(), 35)

    def test_histogram_calculation(self):
        """Test histogram is correctly calculated as MACD - Signal."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(self.data)

        macd_value = result["value_data"]["macd"]
        signal_value = result["value_data"]["signal"]
        histogram_value = result["value_data"]["histogram"]

        # Histogram should be MACD - Signal
        expected_histogram = macd_value - signal_value
        self.assertAlmostEqual(histogram_value, expected_histogram, places=10)

    def test_uptrend_produces_positive_macd(self):
        """Test that uptrend produces positive MACD."""
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        prices = np.linspace(100, 200, 100)  # Strong uptrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(100) * 1000000,
            }
        )
        data.index = dates

        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(data)

        # In strong uptrend, MACD should be positive
        self.assertGreater(result["value"], 0.0)

    def test_downtrend_produces_negative_macd(self):
        """Test that downtrend produces negative MACD."""
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")
        prices = np.linspace(200, 100, 100)  # Strong downtrend

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 0.5,
                "high": prices + 0.5,
                "low": prices - 0.5,
                "close": prices,
                "volume": np.ones(100) * 1000000,
            }
        )
        data.index = dates

        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(data)

        # In strong downtrend, MACD should be negative
        self.assertLess(result["value"], 0.0)

    def test_confidence_scoring(self):
        """Test confidence scoring based on signal strength."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(self.data)

        # Confidence should be between 0 and 1
        confidence = result["value_data"]["confidence"]
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_custom_periods(self):
        """Test MACD with custom periods."""
        # Use different periods (faster MACD)
        indicator = MACD({"fast_period": 5, "slow_period": 10, "signal_period": 5})
        result = indicator.calculate(self.data)

        self.assertIsNotNone(result["value"])
        self.assertEqual(result["metadata"]["fast_period"], 5)
        self.assertEqual(result["metadata"]["slow_period"], 10)
        self.assertEqual(result["metadata"]["signal_period"], 5)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = MACD({"fast_period": 12, "slow_period": 26, "signal_period": 9})
        result = indicator.calculate(self.data, timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])


if __name__ == "__main__":
    unittest.main()
