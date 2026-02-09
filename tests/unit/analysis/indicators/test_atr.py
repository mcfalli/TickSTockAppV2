"""
Unit tests for ATR (Average True Range) indicator.

Sprint 70: Indicator Library Extension - ATR unit tests
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.analysis.indicators.atr import ATR, ATRParams
from src.analysis.exceptions import IndicatorError


class TestATRParams(unittest.TestCase):
    """Test ATR parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = ATRParams(period=14, source="close", use_sma=False)
        self.assertEqual(params.period, 14)
        self.assertEqual(params.use_sma, False)

    def test_default_params(self):
        """Test default parameter values."""
        params = ATRParams(period=14, source="close")
        self.assertEqual(params.period, 14)
        self.assertFalse(params.use_sma)

    def test_invalid_period(self):
        """Test invalid period value."""
        with self.assertRaises(ValueError):
            ATRParams(period=0, source="close")


class TestATR(unittest.TestCase):
    """Test ATR indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create sample OHLCV data with varying volatility
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")

        # Create prices with controlled volatility
        base_price = 100
        prices = []
        for i in range(100):
            # Add some volatility - more in second half
            volatility = 1 if i < 50 else 3
            prices.append(base_price + np.random.uniform(-volatility, volatility))

        prices = np.array(prices)

        self.data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + np.random.uniform(0.5, 1.5, 100),
                "low": prices - np.random.uniform(0.5, 1.5, 100),
                "close": prices + np.random.uniform(-0.5, 0.5, 100),
                "volume": np.random.randint(1000000, 2000000, 100),
            }
        )
        # Ensure OHLC consistency
        self.data["high"] = self.data[["open", "high", "low", "close"]].max(axis=1)
        self.data["low"] = self.data[["open", "high", "low", "close"]].min(axis=1)
        self.data.index = dates

    def test_basic_calculation(self):
        """Test basic ATR calculation."""
        indicator = ATR({"period": 14})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "atr")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("atr_14", result["value_data"])
        # ATR should be positive
        self.assertGreater(result["value"], 0.0)

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:10]  # Only 10 bars, need 15 (period + 1)
        indicator = ATR({"period": 14})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None
        self.assertIsNone(result["value"])
        self.assertIsNone(result["value_data"]["atr_14"])

    def test_calculate_series(self):
        """Test full series calculation."""
        indicator = ATR({"period": 14})
        series = indicator.calculate_series(self.data)

        self.assertEqual(len(series), len(self.data))
        # ATR should be calculated after period bars
        self.assertFalse(pd.isna(series.iloc[14]))
        # All values should be non-negative
        valid_values = series[~pd.isna(series)]
        self.assertTrue((valid_values >= 0).all())

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = ATR({"period": 14})
        # ATR needs period + 1 bars (for previous close)
        self.assertEqual(indicator.get_minimum_periods(), 15)

    def test_wilder_smoothing(self):
        """Test that Wilder's smoothing is used correctly."""
        indicator = ATR({"period": 14, "use_sma": False})
        result = indicator.calculate(self.data)

        # Should produce valid ATR
        self.assertIsNotNone(result["value"])
        self.assertGreater(result["value"], 0.0)
        # Metadata should indicate Wilder's method
        self.assertEqual(result["metadata"]["calculation_method"], "wilder")

    def test_sma_mode(self):
        """Test ATR with SMA smoothing instead of Wilder's."""
        indicator_wilder = ATR({"period": 14, "use_sma": False})
        indicator_sma = ATR({"period": 14, "use_sma": True})

        result_wilder = indicator_wilder.calculate(self.data)
        result_sma = indicator_sma.calculate(self.data)

        # Both should produce valid ATR
        self.assertIsNotNone(result_wilder["value"])
        self.assertIsNotNone(result_sma["value"])
        # Values should be different
        self.assertNotEqual(result_wilder["value"], result_sma["value"])
        # Metadata should reflect method
        self.assertEqual(result_sma["metadata"]["calculation_method"], "sma")

    def test_high_volatility_detection(self):
        """Test high volatility signal detection."""
        # Create data with increasing volatility
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")

        # Low volatility followed by high volatility
        prices = np.concatenate([
            100 + np.random.uniform(-0.5, 0.5, 50),  # Low volatility
            100 + np.random.uniform(-5, 5, 50),  # High volatility
        ])

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + np.abs(np.random.uniform(0.1, 10, 100)),
                "low": prices - np.abs(np.random.uniform(0.1, 10, 100)),
                "close": prices + np.random.uniform(-1, 1, 100),
                "volume": np.ones(100) * 1000000,
            }
        )
        data["high"] = data[["open", "high", "low", "close"]].max(axis=1)
        data["low"] = data[["open", "high", "low", "close"]].min(axis=1)
        data.index = dates

        indicator = ATR({"period": 14})
        result = indicator.calculate(data)

        # Should detect volatility change (signal will be normal/high)
        self.assertIn(result["value_data"]["volatility_signal"], ["normal", "high"])

    def test_true_range_calculation(self):
        """Test True Range calculation with known values."""
        # Create simple data for manual verification
        dates = pd.date_range(start="2025-01-01", periods=5, freq="1D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "high": [105, 110, 108, 112, 115],
                "low": [100, 105, 103, 107, 110],
                "close": [103, 107, 105, 110, 113],
                "open": [102, 106, 106, 109, 111],
                "volume": [1000000] * 5,
            }
        )
        data.index = dates

        indicator = ATR({"period": 3})

        # Calculate True Range series
        tr_series = indicator._calculate_true_range(data)

        # First bar: TR = high - low = 105 - 100 = 5
        self.assertAlmostEqual(tr_series.iloc[0], 5.0, places=2)

        # Second bar: max(110-105=5, abs(110-103)=7, abs(105-103)=2) = 7
        self.assertAlmostEqual(tr_series.iloc[1], 7.0, places=2)

        # All TR values should be positive
        self.assertTrue((tr_series > 0).all())

    def test_gap_handling(self):
        """Test ATR handles gaps correctly."""
        # Create data with gap
        dates = pd.date_range(start="2025-01-01", periods=30, freq="1D")
        prices = [100] * 15 + [110] * 15  # Gap up on day 15

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p + 1 for p in prices],
                "low": [p - 1 for p in prices],
                "close": prices,
                "volume": [1000000] * 30,
            }
        )
        data.index = dates

        indicator = ATR({"period": 14})
        result = indicator.calculate(data)

        # ATR should be calculated successfully
        self.assertIsNotNone(result["value"])
        # ATR should capture the gap in volatility
        self.assertGreater(result["value"], 0.0)

    def test_flat_prices(self):
        """Test ATR with flat prices (no volatility)."""
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

        indicator = ATR({"period": 14})
        result = indicator.calculate(data)

        # ATR should be 0 or very close to 0 for flat prices
        self.assertIsNotNone(result["value"])
        self.assertAlmostEqual(result["value"], 0.0, places=2)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = ATR({"period": 14})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])

    def test_empty_data(self):
        """Test with empty DataFrame."""
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        indicator = ATR({"period": 14})

        # Should handle empty data gracefully
        result = indicator.calculate(empty_data, symbol="TEST")
        self.assertIsNone(result["value"])

    def test_current_true_range_in_result(self):
        """Test that current True Range is included in result."""
        indicator = ATR({"period": 14})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("current_true_range", result["value_data"])
        self.assertIsNotNone(result["value_data"]["current_true_range"])
        # Current TR should be positive
        self.assertGreater(result["value_data"]["current_true_range"], 0.0)

    def test_different_periods(self):
        """Test ATR with different period values."""
        indicator_7 = ATR({"period": 7})
        indicator_14 = ATR({"period": 14})
        indicator_21 = ATR({"period": 21})

        result_7 = indicator_7.calculate(self.data, symbol="TEST")
        result_14 = indicator_14.calculate(self.data, symbol="TEST")
        result_21 = indicator_21.calculate(self.data, symbol="TEST")

        # All should produce valid results
        self.assertIsNotNone(result_7["value"])
        self.assertIsNotNone(result_14["value"])
        self.assertIsNotNone(result_21["value"])

        # Shorter period should be more reactive (potentially different values)
        # But we can't guarantee which is higher, just that they're different
        self.assertTrue(
            result_7["value"] != result_14["value"]
            or result_14["value"] != result_21["value"]
        )

    def test_metadata_structure(self):
        """Test that metadata contains expected fields."""
        indicator = ATR({"period": 14})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("metadata", result)
        self.assertIn("volatility_signal", result["metadata"])
        self.assertIn("calculation_method", result["metadata"])
        self.assertIn("min_bars_required", result["metadata"])
        self.assertEqual(result["metadata"]["min_bars_required"], 15)


if __name__ == "__main__":
    unittest.main()
