"""
Unit tests for AnalysisService.

Sprint 68: Core Analysis Migration - Analysis service tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.core.services.analysis_service import AnalysisService
from src.analysis.exceptions import AnalysisError


class TestAnalysisServiceUtilities:
    """Test utility methods of AnalysisService."""

    def test_get_default_indicators(self):
        """Test getting default indicator set."""
        service = AnalysisService()
        indicators = service._get_default_indicators()

        assert isinstance(indicators, list)
        assert len(indicators) > 0
        assert "SMA" in indicators
        assert "RSI" in indicators
        assert "MACD" in indicators

    def test_get_default_patterns(self):
        """Test getting default pattern set."""
        service = AnalysisService()
        patterns = service._get_default_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert "Doji" in patterns
        assert "Hammer" in patterns
        assert "Engulfing" in patterns

    def test_get_all_available_indicators(self):
        """Test getting all available indicators."""
        service = AnalysisService()
        indicators = service._get_all_available_indicators()

        assert isinstance(indicators, list)
        assert len(indicators) >= 3  # At least SMA, RSI, MACD

    def test_get_all_available_patterns(self):
        """Test getting all available patterns."""
        service = AnalysisService()
        patterns = service._get_all_available_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) >= 3  # At least Doji, Hammer, Engulfing

    def test_generate_universe_summary_empty(self):
        """Test summary generation with empty results."""
        service = AnalysisService()
        summary = service._generate_universe_summary({})

        assert summary["total_indicator_calculations"] == 0
        assert summary["total_pattern_detections"] == 0
        assert len(summary["indicators_calculated"]) == 0
        assert len(summary["patterns_detected"]) == 0

    def test_generate_universe_summary_with_data(self):
        """Test summary generation with actual results."""
        service = AnalysisService()

        # Mock results
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        mock_results = {
            "AAPL": {
                "indicators": {"SMA": {"value": 100}, "RSI": {"value": 50}},
                "patterns": {
                    "Doji": pd.Series([True, False, True, False] + [False] * 6, index=dates)
                },
            },
            "MSFT": {
                "indicators": {"SMA": {"value": 200}},
                "patterns": {
                    "Hammer": pd.Series([False, True, False, True] + [False] * 6, index=dates)
                },
            },
        }

        summary = service._generate_universe_summary(mock_results)

        assert summary["total_indicator_calculations"] == 3  # 2 + 1
        assert summary["total_pattern_detections"] == 4  # 2 + 2
        assert "Doji" in summary["patterns_detected"]
        assert "Hammer" in summary["patterns_detected"]


class TestAnalyzeSymbol:
    """Test single symbol analysis."""

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

    def test_analyze_symbol_structure(self, sample_data):
        """Test analyze_symbol returns correct structure."""
        service = AnalysisService()
        result = service.analyze_symbol("AAPL", sample_data)

        # Check all required keys
        assert "symbol" in result
        assert "timeframe" in result
        assert "indicators" in result
        assert "patterns" in result
        assert "metadata" in result
        assert "timestamp" in result

    def test_analyze_symbol_with_timeframe(self, sample_data):
        """Test analysis with custom timeframe."""
        service = AnalysisService()
        result = service.analyze_symbol("AAPL", sample_data, timeframe="1hour")

        assert result["timeframe"] == "1hour"

    def test_analyze_symbol_with_custom_indicators(self, sample_data):
        """Test analysis with custom indicator list."""
        service = AnalysisService()
        result = service.analyze_symbol(
            "AAPL", sample_data, indicators=["SMA"], patterns=[]
        )

        assert "SMA" in result["indicators"]
        # Should not have other indicators
        assert len(result["indicators"]) == 1

    def test_analyze_symbol_with_custom_patterns(self, sample_data):
        """Test analysis with custom pattern list."""
        service = AnalysisService()
        result = service.analyze_symbol(
            "AAPL", sample_data, indicators=[], patterns=["Doji"]
        )

        assert "Doji" in result["patterns"]
        # Should not have other patterns
        assert len(result["patterns"]) == 1

    def test_analyze_symbol_calculate_all(self, sample_data):
        """Test analysis with calculate_all flag."""
        service = AnalysisService()
        result = service.analyze_symbol("AAPL", sample_data, calculate_all=True)

        # Should have more than default indicators/patterns
        assert len(result["indicators"]) >= 3
        assert len(result["patterns"]) >= 3

    def test_metadata_accuracy(self, sample_data):
        """Test metadata reflects actual results."""
        service = AnalysisService()
        result = service.analyze_symbol(
            "AAPL", sample_data, indicators=["SMA", "RSI"], patterns=["Doji"]
        )

        metadata = result["metadata"]
        assert metadata["data_points"] == 30
        assert metadata["indicators_calculated"] == 2
        assert metadata["patterns_detected"] == 1


class TestGetIndicatorWithPattern:
    """Test indicator-pattern correlation functionality."""

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

    def test_indicator_with_pattern_structure(self, sample_data):
        """Test result structure of get_indicator_with_pattern."""
        service = AnalysisService()
        result = service.get_indicator_with_pattern(
            "AAPL", sample_data, "RSI", "Doji"
        )

        assert "symbol" in result
        assert "indicator" in result
        assert "pattern" in result
        assert "indicator_result" in result
        assert "pattern_detections" in result
        assert "detection_count" in result
        assert "detection_indices" in result

    def test_indicator_with_pattern_values(self, sample_data):
        """Test result values are correct."""
        service = AnalysisService()
        result = service.get_indicator_with_pattern(
            "AAPL", sample_data, "SMA", "Hammer"
        )

        assert result["symbol"] == "AAPL"
        assert result["indicator"] == "SMA"
        assert result["pattern"] == "Hammer"
        assert isinstance(result["indicator_result"], dict)
        assert isinstance(result["pattern_detections"], pd.Series)
        assert isinstance(result["detection_count"], (int, np.integer))

    def test_detection_indices_are_valid(self, sample_data):
        """Test detection indices are valid timestamps."""
        service = AnalysisService()
        result = service.get_indicator_with_pattern(
            "AAPL", sample_data, "RSI", "Doji"
        )

        detection_indices = result["detection_indices"]
        assert isinstance(detection_indices, list)

        # All indices should be from the data
        for idx in detection_indices:
            assert idx in sample_data["timestamp"].values


class TestValidateAnalysisData:
    """Test data validation functionality."""

    def test_valid_data_passes(self):
        """Test that valid data passes validation."""
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
        assert errors == []

    def test_empty_data_fails(self):
        """Test that empty data fails validation."""
        service = AnalysisService()
        empty_data = pd.DataFrame()

        is_valid, errors = service.validate_analysis_data(empty_data)

        assert is_valid is False
        assert len(errors) > 0

    def test_missing_columns_fails(self):
        """Test that missing columns fails validation."""
        service = AnalysisService()

        incomplete_data = pd.DataFrame({"open": [100], "close": [101]})

        is_valid, errors = service.validate_analysis_data(incomplete_data)

        assert is_valid is False
        assert len(errors) > 0

    def test_insufficient_rows_fails(self):
        """Test that insufficient data points fails validation."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        small_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 10,
                "high": [102] * 10,
                "low": [98] * 10,
                "close": [101] * 10,
                "volume": [1000000] * 10,
            }
        )

        is_valid, errors = service.validate_analysis_data(small_data)

        assert is_valid is False
        assert any("insufficient" in e.lower() for e in errors)

    def test_nan_values_fail(self):
        """Test that NaN values fail validation."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        nan_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [102] * 30,
                "low": [98] * 30,
                "close": [101] * 28 + [None, None],  # NaN values
                "volume": [1000000] * 30,
            }
        )

        is_valid, errors = service.validate_analysis_data(nan_data)

        assert is_valid is False
        assert any("nan" in e.lower() for e in errors)

    def test_ohlc_inconsistency_fails(self):
        """Test that OHLC inconsistency fails validation."""
        service = AnalysisService()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        bad_data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 30,
                "high": [98] * 30,  # High < Low (wrong!)
                "low": [102] * 30,
                "close": [101] * 30,
                "volume": [1000000] * 30,
            }
        )

        is_valid, errors = service.validate_analysis_data(bad_data)

        assert is_valid is False
        assert any("inconsistency" in e.lower() for e in errors)
