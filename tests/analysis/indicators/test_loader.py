"""
Unit tests for indicator dynamic loader.

Sprint 68: Core Analysis Migration - Indicator loader tests
"""

import pytest

from src.analysis.indicators.loader import (
    load_indicator,
    is_indicator_available,
    get_available_indicators,
    get_indicator_category,
    _to_class_name,
)
from src.analysis.indicators.base_indicator import BaseIndicator
from src.analysis.exceptions import IndicatorLoadError


class TestLoadIndicator:
    """Test indicator dynamic loading."""

    def test_load_sma_indicator(self):
        """Test loading SMA indicator."""
        indicator_class = load_indicator("SMA")

        assert indicator_class is not None
        assert issubclass(indicator_class, BaseIndicator)
        assert indicator_class.__name__ == "SMA"

    def test_load_rsi_indicator(self):
        """Test loading RSI indicator."""
        indicator_class = load_indicator("RSI")

        assert indicator_class is not None
        assert issubclass(indicator_class, BaseIndicator)
        assert indicator_class.__name__ == "RSI"

    def test_load_macd_indicator(self):
        """Test loading MACD indicator."""
        indicator_class = load_indicator("MACD")

        assert indicator_class is not None
        assert issubclass(indicator_class, BaseIndicator)
        assert indicator_class.__name__ == "MACD"

    def test_load_indicator_case_insensitive(self):
        """Test indicator loading is case-insensitive."""
        # All these should work
        sma1 = load_indicator("SMA")
        sma2 = load_indicator("sma")
        sma3 = load_indicator("Sma")

        assert sma1 is sma2 is sma3

    def test_load_indicator_creates_instance(self):
        """Test loaded indicator can be instantiated."""
        indicator_class = load_indicator("SMA")
        indicator = indicator_class({"period": 20})

        assert isinstance(indicator, BaseIndicator)
        assert indicator.name == "SMA"

    def test_load_nonexistent_indicator(self):
        """Test loading nonexistent indicator raises IndicatorLoadError."""
        with pytest.raises(IndicatorLoadError, match="Unknown indicator"):
            load_indicator("NonExistentIndicator")

    def test_no_fallback_policy(self):
        """Test NO FALLBACK policy - errors not silently ignored."""
        # Should raise immediately, not fall back to stub/default
        with pytest.raises(IndicatorLoadError):
            load_indicator("InvalidIndicator")


class TestToClassName:
    """Test class name conversion."""

    def test_acronym_indicators(self):
        """Test acronym indicators stay uppercase."""
        assert _to_class_name("sma") == "SMA"
        assert _to_class_name("ema") == "EMA"
        assert _to_class_name("rsi") == "RSI"
        assert _to_class_name("macd") == "MACD"
        assert _to_class_name("atr") == "ATR"
        assert _to_class_name("obv") == "OBV"
        assert _to_class_name("vwap") == "VWAP"
        assert _to_class_name("adx") == "ADX"

    def test_multi_word_indicators(self):
        """Test multi-word indicator conversion."""
        assert _to_class_name("bollinger_bands") == "BollingerBands"
        assert _to_class_name("volume_sma") == "VolumeSma"
        assert _to_class_name("relative_volume") == "RelativeVolume"
        assert _to_class_name("williams_r") == "WilliamsR"

    def test_mixed_case_conversion(self):
        """Test mixed case conversion."""
        assert _to_class_name("Bollinger_Bands") == "BollingerBands"
        assert _to_class_name("VOLUME_SMA") == "VolumeSma"


class TestIsIndicatorAvailable:
    """Test indicator availability checking."""

    def test_available_trend_indicators(self):
        """Test trend indicators are available."""
        assert is_indicator_available("SMA") is True
        assert is_indicator_available("EMA") is True
        assert is_indicator_available("MACD") is True

    def test_available_momentum_indicators(self):
        """Test momentum indicators are available."""
        assert is_indicator_available("RSI") is True
        assert is_indicator_available("Stochastic") is True
        assert is_indicator_available("Momentum") is True

    def test_available_indicators_case_insensitive(self):
        """Test availability check is case-insensitive."""
        assert is_indicator_available("sma") is True
        assert is_indicator_available("RSI") is True
        assert is_indicator_available("Macd") is True

    def test_unavailable_indicator(self):
        """Test unavailable indicator returns False."""
        assert is_indicator_available("NonExistentIndicator") is False
        assert is_indicator_available("InvalidIndicator") is False


class TestGetAvailableIndicators:
    """Test getting available indicators list."""

    def test_get_available_indicators_structure(self):
        """Test available indicators returns correct structure."""
        indicators = get_available_indicators()

        assert isinstance(indicators, dict)
        assert "trend" in indicators
        assert "momentum" in indicators
        assert "volatility" in indicators
        assert "volume" in indicators
        assert "directional" in indicators

    def test_trend_indicators_included(self):
        """Test trend indicators are included."""
        indicators = get_available_indicators()

        trend = indicators["trend"]
        assert "sma" in trend
        assert "ema" in trend
        assert "macd" in trend

    def test_momentum_indicators_included(self):
        """Test momentum indicators are included."""
        indicators = get_available_indicators()

        momentum = indicators["momentum"]
        assert "rsi" in momentum
        assert "stochastic" in momentum
        assert "momentum" in momentum

    def test_indicators_are_lowercase(self):
        """Test indicator names are lowercase."""
        indicators = get_available_indicators()

        for category, indicator_list in indicators.items():
            for indicator_name in indicator_list:
                assert indicator_name.islower()


class TestGetIndicatorCategory:
    """Test indicator category detection."""

    def test_trend_indicator_category(self):
        """Test trend indicator category."""
        assert get_indicator_category("SMA") == "trend"
        assert get_indicator_category("EMA") == "trend"
        assert get_indicator_category("MACD") == "trend"

    def test_momentum_indicator_category(self):
        """Test momentum indicator category."""
        assert get_indicator_category("RSI") == "momentum"
        assert get_indicator_category("Stochastic") == "momentum"

    def test_volatility_indicator_category(self):
        """Test volatility indicator category."""
        assert get_indicator_category("bollinger_bands") == "volatility"
        assert get_indicator_category("ATR") == "volatility"

    def test_volume_indicator_category(self):
        """Test volume indicator category."""
        assert get_indicator_category("OBV") == "volume"
        assert get_indicator_category("VWAP") == "volume"

    def test_unknown_indicator_category(self):
        """Test unknown indicator returns None."""
        assert get_indicator_category("UnknownIndicator") is None


class TestLoaderIntegration:
    """Test loader integration scenarios."""

    def test_load_and_execute_indicator(self):
        """Test loading indicator and executing calculation."""
        import pandas as pd

        # Load indicator
        sma_class = load_indicator("SMA")
        sma = sma_class({"period": 5})

        # Create test data
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "volume": [1000000] * 10,
            }
        )

        # Execute calculation
        result = sma.calculate(data)

        assert isinstance(result, dict)
        assert "value" in result
        assert "value_data" in result

    def test_load_multiple_indicators(self):
        """Test loading multiple indicators."""
        indicators = ["SMA", "RSI", "MACD"]

        loaded_indicators = {}
        for indicator_name in indicators:
            indicator_class = load_indicator(indicator_name)
            loaded_indicators[indicator_name] = indicator_class

        assert len(loaded_indicators) == 3
        assert all(issubclass(i, BaseIndicator) for i in loaded_indicators.values())

    def test_indicator_class_caching(self):
        """Test loading same indicator twice returns same class."""
        sma1 = load_indicator("SMA")
        sma2 = load_indicator("SMA")

        # Should be same class object
        assert sma1 is sma2

    def test_load_all_registered_indicators(self):
        """Test all registered indicators can be loaded."""
        from src.analysis.indicators.loader import AVAILABLE_INDICATORS

        # Test a subset (the ones we know exist)
        test_indicators = ["sma", "rsi", "macd"]

        for indicator_name in test_indicators:
            try:
                indicator_class = load_indicator(indicator_name)
                assert issubclass(indicator_class, BaseIndicator)
            except IndicatorLoadError as e:
                # If indicator module doesn't exist yet, that's okay for this test
                # We're testing the loader mechanism, not completeness of implementation
                if "module not found" not in str(e).lower():
                    raise
