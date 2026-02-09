"""
End-to-end integration tests for complete analysis system.

Sprint 68: Core Analysis Migration - Integration tests
Tests the complete workflow: data -> indicators -> patterns -> results
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from src.core.services.analysis_service import AnalysisService
from src.core.services.indicator_service import IndicatorService
from src.core.services.pattern_service import PatternService
from src.analysis.exceptions import AnalysisError


class TestAnalysisServiceInit:
    """Test AnalysisService initialization."""

    def test_service_initialization(self):
        """Test service initializes with sub-services."""
        service = AnalysisService()

        assert service is not None
        assert isinstance(service.indicator_service, IndicatorService)
        assert isinstance(service.pattern_service, PatternService)

    def test_service_with_custom_config(self):
        """Test service initialization with custom config."""
        config = {"test": "config"}
        service = AnalysisService(db_config=config)

        assert service._db_config == config


class TestCompleteAnalysisWorkflow:
    """Test complete analysis workflow end-to-end."""

    @pytest.fixture
    def sample_data(self):
        """Create realistic OHLCV data for testing."""
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")

        # Create trending data with some volatility
        base_price = 100
        prices = []
        for i in range(50):
            price = base_price + i * 0.5 + (i % 5) * 2  # Uptrend with noise
            prices.append(price)

        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [p - 0.5 for p in prices],
                "high": [p + 2 for p in prices],
                "low": [p - 2 for p in prices],
                "close": prices,
                "volume": [1000000 + i * 10000 for i in range(50)],
            }
        )

        return data

    def test_analyze_symbol_with_defaults(self, sample_data):
        """Test complete symbol analysis with default indicators/patterns."""
        service = AnalysisService()

        result = service.analyze_symbol("AAPL", sample_data)

        # Verify structure
        assert "symbol" in result
        assert "timeframe" in result
        assert "indicators" in result
        assert "patterns" in result
        assert "metadata" in result
        assert "timestamp" in result

        # Verify symbol
        assert result["symbol"] == "AAPL"

        # Verify indicators calculated
        assert len(result["indicators"]) > 0
        assert "SMA" in result["indicators"]
        assert "RSI" in result["indicators"]
        assert "MACD" in result["indicators"]

        # Verify patterns detected
        assert len(result["patterns"]) > 0
        assert "Doji" in result["patterns"]

        # Verify metadata
        assert result["metadata"]["data_points"] == 50
        assert result["metadata"]["indicators_calculated"] >= 3

    def test_analyze_symbol_with_custom_indicators(self, sample_data):
        """Test analysis with custom indicator selection."""
        service = AnalysisService()

        result = service.analyze_symbol(
            "AAPL", sample_data, indicators=["SMA", "RSI"], patterns=["Doji"]
        )

        # Should only have requested indicators
        assert "SMA" in result["indicators"]
        assert "RSI" in result["indicators"]
        assert "MACD" not in result["indicators"]

        # Should only have requested patterns
        assert "Doji" in result["patterns"]
        assert "Hammer" not in result["patterns"]

    def test_indicators_available_for_patterns(self, sample_data):
        """Test that indicators are available when patterns need them."""
        service = AnalysisService()

        # Calculate indicators first
        result = service.analyze_symbol("AAPL", sample_data)

        # Indicators should be calculated before patterns
        assert len(result["indicators"]) > 0
        assert len(result["patterns"]) > 0

        # Verify indicator results are valid
        for indicator_name, indicator_result in result["indicators"].items():
            assert "value" in indicator_result
            assert "value_data" in indicator_result

    def test_pattern_detections_are_series(self, sample_data):
        """Test that pattern results are pandas Series."""
        service = AnalysisService()

        result = service.analyze_symbol("AAPL", sample_data)

        # Pattern results should be Series
        for pattern_name, detections in result["patterns"].items():
            assert isinstance(detections, pd.Series)
            assert detections.dtype == bool
            assert len(detections) == len(sample_data)


class TestIndicatorPatternCorrelation:
    """Test correlation between indicators and patterns."""

    @pytest.fixture
    def sample_data(self):
        """Create OHLCV data."""
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

    def test_get_indicator_with_pattern(self, sample_data):
        """Test getting indicator values at pattern detection points."""
        service = AnalysisService()

        result = service.get_indicator_with_pattern(
            "AAPL", sample_data, "RSI", "Doji"
        )

        # Verify structure
        assert "symbol" in result
        assert "indicator" in result
        assert "pattern" in result
        assert "indicator_result" in result
        assert "pattern_detections" in result
        assert "detection_count" in result

        # Verify data
        assert result["symbol"] == "AAPL"
        assert result["indicator"] == "RSI"
        assert result["pattern"] == "Doji"
        assert isinstance(result["pattern_detections"], pd.Series)


class TestDataValidation:
    """Test data validation functionality."""

    def test_validate_valid_data(self):
        """Test validation with valid data."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        valid_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [102] * 30,
                "low": [98] * 30,
                "close": [101] * 30,
                "volume": [1000000] * 30,
            }
        )

        is_valid, errors = service.validate_analysis_data(valid_data)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_empty_data(self):
        """Test validation with empty data."""
        service = AnalysisService()
        empty_data = pd.DataFrame()

        is_valid, errors = service.validate_analysis_data(empty_data)

        assert is_valid is False
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_validate_missing_columns(self):
        """Test validation with missing columns."""
        service = AnalysisService()

        invalid_data = pd.DataFrame(
            {"open": [100], "close": [101], "volume": [1000000]}
        )

        is_valid, errors = service.validate_analysis_data(invalid_data)

        assert is_valid is False
        assert any("missing columns" in e.lower() for e in errors)

    def test_validate_insufficient_data(self):
        """Test validation with insufficient data points."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        insufficient_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 10,
                "high": [102] * 10,
                "low": [98] * 10,
                "close": [101] * 10,
                "volume": [1000000] * 10,
            }
        )

        is_valid, errors = service.validate_analysis_data(insufficient_data)

        assert is_valid is False
        assert any("insufficient data" in e.lower() for e in errors)

    def test_validate_ohlc_inconsistency(self):
        """Test validation with OHLC inconsistency."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        inconsistent_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [98] * 30,  # High < Low (inconsistent!)
                "low": [102] * 30,
                "close": [101] * 30,
                "volume": [1000000] * 30,
            }
        )

        is_valid, errors = service.validate_analysis_data(inconsistent_data)

        assert is_valid is False
        assert any("inconsistency" in e.lower() for e in errors)


class TestServiceCoordination:
    """Test coordination between indicator and pattern services."""

    @pytest.fixture
    def sample_data(self):
        """Create OHLCV data."""
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

    def test_indicator_service_accessible(self, sample_data):
        """Test indicator service is accessible from analysis service."""
        service = AnalysisService()

        # Calculate indicator directly through indicator service
        result = service.indicator_service.calculate_indicator("SMA", sample_data)

        assert result is not None
        assert "value" in result

    def test_pattern_service_accessible(self, sample_data):
        """Test pattern service is accessible from analysis service."""
        service = AnalysisService()

        # Detect pattern directly through pattern service
        result = service.pattern_service.detect_pattern("Doji", sample_data)

        assert result is not None
        assert isinstance(result, pd.Series)

    def test_services_share_cache(self, sample_data):
        """Test that services maintain their own caches."""
        service = AnalysisService()

        # Use indicator service
        service.indicator_service.calculate_indicator("SMA", sample_data)
        assert "SMA" in service.indicator_service._indicator_cache

        # Use pattern service
        service.pattern_service.detect_pattern("Doji", sample_data)
        assert "Doji" in service.pattern_service._pattern_cache


class TestAnalysisMetadata:
    """Test analysis metadata generation."""

    @pytest.fixture
    def sample_data(self):
        """Create OHLCV data."""
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

    def test_metadata_includes_counts(self, sample_data):
        """Test metadata includes correct counts."""
        service = AnalysisService()

        result = service.analyze_symbol("AAPL", sample_data)

        metadata = result["metadata"]
        assert "data_points" in metadata
        assert "indicators_calculated" in metadata
        assert "patterns_detected" in metadata
        assert "total_detections" in metadata

        assert metadata["data_points"] == 30
        assert metadata["indicators_calculated"] >= 3
        assert metadata["patterns_detected"] >= 3

    def test_timestamp_is_recent(self, sample_data):
        """Test timestamp is recent."""
        service = AnalysisService()

        result = service.analyze_symbol("AAPL", sample_data)

        timestamp = result["timestamp"]
        assert isinstance(timestamp, datetime)

        # Should be within last minute
        age = datetime.utcnow() - timestamp
        assert age.total_seconds() < 60


class TestErrorHandling:
    """Test error handling in analysis service."""

    def test_analyze_with_invalid_data(self):
        """Test analysis with invalid data."""
        service = AnalysisService()

        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        # Should raise AnalysisError
        with pytest.raises(AnalysisError):
            service.analyze_symbol("AAPL", invalid_data)

    def test_analyze_with_empty_data(self):
        """Test analysis with empty data."""
        service = AnalysisService()

        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Should raise AnalysisError
        with pytest.raises(AnalysisError):
            service.analyze_symbol("AAPL", empty_data)
