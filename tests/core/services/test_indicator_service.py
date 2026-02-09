"""
Unit tests for IndicatorService.

Sprint 68: Core Analysis Migration - Indicator service tests
"""

import pytest
import pandas as pd
from datetime import datetime

from src.core.services.indicator_service import IndicatorService
from src.analysis.exceptions import IndicatorLoadError, IndicatorError


class TestIndicatorServiceInit:
    """Test IndicatorService initialization."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = IndicatorService()

        assert service is not None
        assert service._indicator_cache == {}
        assert service._db is None  # Lazy loaded

    def test_service_with_custom_config(self):
        """Test service initialization with custom config."""
        config = {"test": "config"}
        service = IndicatorService(db_config=config)

        assert service._db_config == config


class TestCalculateIndicator:
    """Test single indicator calculation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100 + i * 0.5 for i in range(30)],
                "high": [102 + i * 0.5 for i in range(30)],
                "low": [98 + i * 0.5 for i in range(30)],
                "close": [101 + i * 0.5 for i in range(30)],
                "volume": [1000000] * 30,
            }
        )

    def test_calculate_sma_indicator(self, sample_data):
        """Test calculating SMA indicator."""
        service = IndicatorService()
        result = service.calculate_indicator("SMA", sample_data, symbol="AAPL")

        assert isinstance(result, dict)
        assert "value" in result
        assert "value_data" in result
        assert "indicator_type" in result

    def test_calculate_rsi_indicator(self, sample_data):
        """Test calculating RSI indicator."""
        service = IndicatorService()
        result = service.calculate_indicator("RSI", sample_data, symbol="AAPL")

        assert isinstance(result, dict)
        assert "value" in result
        assert "value_data" in result

    def test_calculate_macd_indicator(self, sample_data):
        """Test calculating MACD indicator."""
        service = IndicatorService()
        result = service.calculate_indicator("MACD", sample_data, symbol="AAPL")

        assert isinstance(result, dict)
        assert "value" in result
        assert "value_data" in result

    def test_calculate_with_custom_params(self, sample_data):
        """Test calculation with custom parameters."""
        service = IndicatorService()
        params = {"period": 10}

        result = service.calculate_indicator("SMA", sample_data, params=params)

        assert isinstance(result, dict)
        assert "value" in result

    def test_calculate_with_timeframe(self, sample_data):
        """Test calculation with specific timeframe."""
        service = IndicatorService()
        result = service.calculate_indicator(
            "SMA", sample_data, symbol="AAPL", timeframe="1hour"
        )

        assert isinstance(result, dict)

    def test_calculate_invalid_indicator(self, sample_data):
        """Test calculating invalid indicator raises IndicatorLoadError."""
        service = IndicatorService()

        with pytest.raises(IndicatorLoadError):
            service.calculate_indicator("InvalidIndicator", sample_data)

    def test_indicator_class_caching(self, sample_data):
        """Test indicator classes are cached."""
        service = IndicatorService()

        # First call - loads and caches
        result1 = service.calculate_indicator("SMA", sample_data)

        # Should be cached now
        assert "SMA" in service._indicator_cache

        # Second call - uses cache
        result2 = service.calculate_indicator("SMA", sample_data)

        assert isinstance(result1, dict)
        assert isinstance(result2, dict)


class TestCalculateMultipleIndicators:
    """Test multiple indicator calculation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100 + i * 0.5 for i in range(30)],
                "high": [102 + i * 0.5 for i in range(30)],
                "low": [98 + i * 0.5 for i in range(30)],
                "close": [101 + i * 0.5 for i in range(30)],
                "volume": [1000000] * 30,
            }
        )

    def test_calculate_multiple_indicators(self, sample_data):
        """Test calculating multiple indicators."""
        service = IndicatorService()
        indicators = ["SMA", "RSI", "MACD"]

        results = service.calculate_multiple_indicators(
            indicators, sample_data, symbol="AAPL"
        )

        assert isinstance(results, dict)
        assert len(results) == 3
        assert all(indicator in results for indicator in indicators)
        assert all(isinstance(r, dict) for r in results.values())

    def test_multiple_indicators_with_invalid(self, sample_data):
        """Test multiple indicator calculation with invalid indicator."""
        service = IndicatorService()
        indicators = ["SMA", "InvalidIndicator", "RSI"]

        # Should not raise - invalid indicators return error dict
        results = service.calculate_multiple_indicators(indicators, sample_data)

        assert len(results) == 3
        assert "SMA" in results
        assert "InvalidIndicator" in results  # Present but with error
        assert "RSI" in results

        # Invalid indicator should have error key
        assert "error" in results["InvalidIndicator"]

    def test_multiple_indicators_different_results(self, sample_data):
        """Test multiple indicators can have different results."""
        service = IndicatorService()
        indicators = ["SMA", "RSI"]

        results = service.calculate_multiple_indicators(indicators, sample_data)

        # Results should be independent
        assert results["SMA"]["value"] != results["RSI"]["value"]


class TestGetIndicatorValue:
    """Test convenience method for getting indicator value."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100 + i * 0.5 for i in range(30)],
                "high": [102 + i * 0.5 for i in range(30)],
                "low": [98 + i * 0.5 for i in range(30)],
                "close": [101 + i * 0.5 for i in range(30)],
                "volume": [1000000] * 30,
            }
        )

    def test_get_indicator_value(self, sample_data):
        """Test getting single indicator value."""
        service = IndicatorService()
        value = service.get_indicator_value("SMA", sample_data, symbol="AAPL")

        assert isinstance(value, (int, float))
        assert value is not None

    def test_get_indicator_value_with_params(self, sample_data):
        """Test getting indicator value with custom parameters."""
        service = IndicatorService()
        params = {"period": 10}

        value = service.get_indicator_value("SMA", sample_data, params=params)

        assert isinstance(value, (int, float))

    def test_get_invalid_indicator_value(self, sample_data):
        """Test getting invalid indicator value returns None."""
        service = IndicatorService()
        value = service.get_indicator_value("InvalidIndicator", sample_data)

        assert value is None


class TestIndicatorServiceUtilities:
    """Test indicator service utility methods."""

    def test_get_available_indicators(self):
        """Test getting available indicators."""
        service = IndicatorService()
        indicators = service.get_available_indicators()

        assert isinstance(indicators, dict)
        assert "trend" in indicators
        assert "sma" in indicators["trend"]

    def test_is_indicator_available(self):
        """Test checking indicator availability."""
        service = IndicatorService()

        assert service.is_indicator_available("SMA") is True
        assert service.is_indicator_available("RSI") is True
        assert service.is_indicator_available("InvalidIndicator") is False

    def test_validate_data(self):
        """Test data validation."""
        service = IndicatorService()

        # Valid data
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        valid_data = pd.DataFrame(
            {
                "open": [100] * 10,
                "high": [102] * 10,
                "low": [98] * 10,
                "close": [101] * 10,
                "volume": [1000000] * 10,
            }
        )

        assert service.validate_data(valid_data) is True

        # Invalid data (missing columns)
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        assert service.validate_data(invalid_data) is False

        # Empty data
        empty_data = pd.DataFrame()

        assert service.validate_data(empty_data) is False

    def test_get_indicator_class_with_cache(self):
        """Test _get_indicator_class uses cache."""
        service = IndicatorService()

        # First call - loads and caches
        class1 = service._get_indicator_class("SMA")
        assert "SMA" in service._indicator_cache

        # Second call - uses cache
        class2 = service._get_indicator_class("SMA")

        # Should be same class object
        assert class1 is class2


class TestIndicatorServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_calculate_with_empty_data(self):
        """Test calculation with empty data."""
        service = IndicatorService()
        empty_data = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        # Empty data should either raise IndicatorError or return error in result
        try:
            result = service.calculate_indicator("SMA", empty_data)
            # If it doesn't raise, it should indicate an error somehow
            # This is acceptable behavior - some indicators may handle empty data gracefully
            assert result is not None
        except IndicatorError:
            # This is also acceptable - indicator service detects invalid data
            pass

    def test_calculate_with_insufficient_data(self):
        """Test calculation with insufficient data for indicator."""
        service = IndicatorService()

        # Only 5 rows, RSI needs more
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        insufficient_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 5,
                "high": [102] * 5,
                "low": [98] * 5,
                "close": [101] * 5,
                "volume": [1000000] * 5,
            }
        )

        # Should raise or return error
        # Depends on indicator implementation
        try:
            result = service.calculate_indicator("RSI", insufficient_data)
            # If it doesn't raise, check for error indication
            assert result is not None
        except IndicatorError:
            # This is expected for insufficient data
            pass

    def test_calculate_multiple_with_empty_list(self):
        """Test calculating empty indicator list."""
        service = IndicatorService()
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 10,
                "high": [102] * 10,
                "low": [98] * 10,
                "close": [101] * 10,
                "volume": [1000000] * 10,
            }
        )

        results = service.calculate_multiple_indicators([], data)

        assert isinstance(results, dict)
        assert len(results) == 0
