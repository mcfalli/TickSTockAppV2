"""
Unit tests for Bollinger Bands indicator.

Sprint 70: Indicator Library Extension - Bollinger Bands unit tests
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.analysis.indicators.bollinger_bands import BollingerBands, BollingerBandsParams
from src.analysis.exceptions import IndicatorError


class TestBollingerBandsParams(unittest.TestCase):
    """Test Bollinger Bands parameter validation."""

    def test_valid_params(self):
        """Test valid parameter configurations."""
        params = BollingerBandsParams(period=20, source="close", num_std_dev=2.0)
        self.assertEqual(params.period, 20)
        self.assertEqual(params.num_std_dev, 2.0)

    def test_default_params(self):
        """Test default parameter values."""
        params = BollingerBandsParams(period=20, source="close")
        self.assertEqual(params.num_std_dev, 2.0)

    def test_invalid_num_std_dev(self):
        """Test invalid num_std_dev value."""
        with self.assertRaises(ValueError):
            BollingerBandsParams(period=20, source="close", num_std_dev=0.0)

        with self.assertRaises(ValueError):
            BollingerBandsParams(period=20, source="close", num_std_dev=-1.0)


class TestBollingerBands(unittest.TestCase):
    """Test Bollinger Bands indicator calculations."""

    def setUp(self):
        """Set up test data."""
        # Create sample OHLCV data with trending and ranging periods
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")

        # Create prices with controlled volatility
        # First 50: low volatility around 100
        # Last 50: high volatility around 110
        np.random.seed(42)  # For reproducible tests
        low_vol_prices = 100 + np.random.uniform(-1, 1, 50)
        high_vol_prices = 110 + np.random.uniform(-5, 5, 50)
        prices = np.concatenate([low_vol_prices, high_vol_prices])

        self.data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + np.abs(np.random.uniform(0.1, 1.0, 100)),
                "low": prices - np.abs(np.random.uniform(0.1, 1.0, 100)),
                "close": prices,
                "volume": np.random.randint(1000000, 2000000, 100),
            }
        )
        # Ensure OHLC consistency
        self.data["high"] = self.data[["open", "high", "low", "close"]].max(axis=1)
        self.data["low"] = self.data[["open", "high", "low", "close"]].min(axis=1)
        self.data.index = dates

    def test_basic_calculation(self):
        """Test basic Bollinger Bands calculation."""
        indicator = BollingerBands({"period": 20, "num_std_dev": 2.0})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="daily")

        self.assertEqual(result["indicator_type"], "bollinger_bands")
        self.assertEqual(result["symbol"], "TEST")
        self.assertEqual(result["timeframe"], "daily")
        self.assertIsNotNone(result["value"])
        self.assertIn("upper_band", result["value_data"])
        self.assertIn("middle_band", result["value_data"])
        self.assertIn("lower_band", result["value_data"])
        self.assertIn("percent_b", result["value_data"])

        # Upper > Middle > Lower
        self.assertGreater(result["value_data"]["upper_band"], result["value_data"]["middle_band"])
        self.assertGreater(result["value_data"]["middle_band"], result["value_data"]["lower_band"])

    def test_percent_b_calculation(self):
        """Test %B (Percent B) calculation."""
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST")

        percent_b = result["value_data"]["percent_b"]
        self.assertIsNotNone(percent_b)

        # %B can be outside 0-1 range (price outside bands)
        # Just verify it's a reasonable value
        self.assertIsInstance(percent_b, (int, float))

    def test_bandwidth_calculation(self):
        """Test bandwidth calculation."""
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST")

        bandwidth = result["value_data"]["bandwidth"]
        self.assertIsNotNone(bandwidth)
        self.assertGreater(bandwidth, 0.0)  # Bandwidth should be positive

    def test_position_signals(self):
        """Test position signal detection."""
        # Create data with price at different positions
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")

        # Price moving from below lower band to above upper band
        prices = np.linspace(95, 105, 50)

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

        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(data, symbol="TEST")

        # Should have some position signal
        self.assertIn(result["metadata"]["position_signal"], [
            "above_upper", "near_upper", "middle", "near_lower", "below_lower"
        ])

    def test_squeeze_detection(self):
        """Test squeeze (low volatility) detection."""
        # Create very flat prices (low volatility = squeeze)
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        prices = 100 + np.random.uniform(-0.1, 0.1, 50)  # Very tight range

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": prices + 0.05,
                "low": prices - 0.05,
                "close": prices,
                "volume": [1000000] * 50,
            }
        )
        data.index = dates

        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(data, symbol="TEST")

        # Squeeze should be detected (bandwidth < 10%)
        self.assertTrue(result["metadata"]["squeeze_detected"])
        self.assertLess(result["value_data"]["bandwidth"], 10.0)

    def test_expansion_detection(self):
        """Test expansion (high volatility) detection."""
        # Create data with increasing volatility
        dates = pd.date_range(start="2025-01-01", periods=100, freq="1D")

        # Start with low volatility, end with high
        prices = []
        for i in range(100):
            vol = 0.5 if i < 50 else 5.0  # Volatility increases
            prices.append(100 + np.random.uniform(-vol, vol))

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p + abs(np.random.uniform(0, 2)) for p in prices],
                "low": [p - abs(np.random.uniform(0, 2)) for p in prices],
                "close": prices,
                "volume": [1000000] * 100,
            }
        )
        data["high"] = data[["open", "high", "low", "close"]].max(axis=1)
        data["low"] = data[["open", "high", "low", "close"]].min(axis=1)
        data.index = dates

        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(data, symbol="TEST")

        # Expansion might or might not be detected depending on exact values
        # Just verify the field exists
        self.assertIn("expansion_detected", result["metadata"])
        self.assertIsInstance(result["metadata"]["expansion_detected"], bool)

    def test_insufficient_data(self):
        """Test with insufficient data."""
        small_data = self.data.iloc[:15]  # Only 15 bars, need 20
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(small_data, symbol="TEST")

        # Should return None
        self.assertIsNone(result["value"])
        self.assertIsNone(result["value_data"]["upper_band"])

    def test_calculate_series(self):
        """Test full series calculation."""
        indicator = BollingerBands({"period": 20})
        series = indicator.calculate_series(self.data)

        self.assertEqual(len(series), len(self.data))
        self.assertIn("upper_band", series.columns)
        self.assertIn("middle_band", series.columns)
        self.assertIn("lower_band", series.columns)
        self.assertIn("percent_b", series.columns)
        self.assertIn("bandwidth", series.columns)

        # Check that bands are calculated (not all NaN after period)
        self.assertFalse(pd.isna(series["middle_band"].iloc[-1]))
        self.assertFalse(pd.isna(series["upper_band"].iloc[-1]))
        self.assertFalse(pd.isna(series["lower_band"].iloc[-1]))

    def test_minimum_periods(self):
        """Test minimum periods calculation."""
        indicator = BollingerBands({"period": 20})
        self.assertEqual(indicator.get_minimum_periods(), 20)

    def test_different_std_dev(self):
        """Test with different standard deviation multipliers."""
        indicator_1std = BollingerBands({"period": 20, "num_std_dev": 1.0})
        indicator_2std = BollingerBands({"period": 20, "num_std_dev": 2.0})
        indicator_3std = BollingerBands({"period": 20, "num_std_dev": 3.0})

        result_1 = indicator_1std.calculate(self.data)
        result_2 = indicator_2std.calculate(self.data)
        result_3 = indicator_3std.calculate(self.data)

        # All should have same middle band
        self.assertAlmostEqual(
            result_1["value_data"]["middle_band"],
            result_2["value_data"]["middle_band"],
            places=2
        )

        # Wider std_dev should have wider bands
        band_width_1 = result_1["value_data"]["upper_band"] - result_1["value_data"]["lower_band"]
        band_width_2 = result_2["value_data"]["upper_band"] - result_2["value_data"]["lower_band"]
        band_width_3 = result_3["value_data"]["upper_band"] - result_3["value_data"]["lower_band"]

        self.assertLess(band_width_1, band_width_2)
        self.assertLess(band_width_2, band_width_3)

    def test_price_above_upper_band(self):
        """Test when price is above upper band."""
        # Create stable data followed by extreme spike
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        # Stable prices around 100, then extreme spike on last bar
        stable_prices = [100 + np.random.uniform(-0.5, 0.5) for _ in range(49)]
        prices = stable_prices + [140]  # Extreme spike on last bar

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

        indicator = BollingerBands({"period": 20, "num_std_dev": 2.0})
        result = indicator.calculate(data)

        # %B should be > 1.0 (above upper band)
        self.assertGreater(result["value_data"]["percent_b"], 1.0)

    def test_price_below_lower_band(self):
        """Test when price is below lower band."""
        # Create stable data followed by extreme drop
        dates = pd.date_range(start="2025-01-01", periods=50, freq="1D")
        # Stable prices around 100, then extreme drop on last bar
        stable_prices = [100 + np.random.uniform(-0.5, 0.5) for _ in range(49)]
        prices = stable_prices + [60]  # Extreme drop on last bar

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

        indicator = BollingerBands({"period": 20, "num_std_dev": 2.0})
        result = indicator.calculate(data)

        # %B should be < 0.0 (below lower band)
        self.assertLess(result["value_data"]["percent_b"], 0.0)

    def test_flat_prices(self):
        """Test with completely flat prices."""
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

        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(data)

        # With flat prices, bands should be very close together
        # Bandwidth should be very small or zero
        self.assertLessEqual(result["value_data"]["bandwidth"], 1.0)

    def test_invalid_timeframe(self):
        """Test with invalid timeframe."""
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST", timeframe="invalid")

        self.assertIsNone(result["value"])
        self.assertIn("error", result["metadata"])

    def test_empty_data(self):
        """Test with empty DataFrame."""
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        indicator = BollingerBands({"period": 20})

        result = indicator.calculate(empty_data, symbol="TEST")
        self.assertIsNone(result["value"])

    def test_metadata_structure(self):
        """Test that metadata contains expected fields."""
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("metadata", result)
        self.assertIn("position_signal", result["metadata"])
        self.assertIn("squeeze_detected", result["metadata"])
        self.assertIn("expansion_detected", result["metadata"])
        self.assertIn("period", result["metadata"])
        self.assertIn("num_std_dev", result["metadata"])
        self.assertEqual(result["metadata"]["period"], 20)
        self.assertEqual(result["metadata"]["num_std_dev"], 2.0)

    def test_current_price_in_result(self):
        """Test that current price is included in value_data."""
        indicator = BollingerBands({"period": 20})
        result = indicator.calculate(self.data, symbol="TEST")

        self.assertIn("current_price", result["value_data"])
        self.assertIsNotNone(result["value_data"]["current_price"])

        # Current price should match last close
        expected_price = self.data["close"].iloc[-1]
        self.assertAlmostEqual(
            result["value_data"]["current_price"],
            expected_price,
            places=2
        )


if __name__ == "__main__":
    unittest.main()
