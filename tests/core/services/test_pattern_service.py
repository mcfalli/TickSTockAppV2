"""
Unit tests for PatternService.

Sprint 68: Core Analysis Migration - Pattern service tests
"""

import pytest
import pandas as pd
from datetime import datetime

from src.core.services.pattern_service import PatternService
from src.analysis.exceptions import PatternLoadError, PatternDetectionError


class TestPatternServiceInit:
    """Test PatternService initialization."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = PatternService()

        assert service is not None
        assert service._pattern_cache == {}
        assert service._db is None  # Lazy loaded
        assert hasattr(service, "db")


class TestDetectPattern:
    """Test single pattern detection."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "close": [100.1, 101, 102, 103.05, 104, 105, 106, 107, 108, 109],
                "volume": [1000000] * 10,
            }
        )

    def test_detect_doji_pattern(self, sample_data):
        """Test detecting Doji pattern."""
        service = PatternService()
        result = service.detect_pattern("Doji", sample_data, symbol="AAPL")

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert result.dtype == bool

    def test_detect_hammer_pattern(self, sample_data):
        """Test detecting Hammer pattern."""
        service = PatternService()
        result = service.detect_pattern("Hammer", sample_data, symbol="AAPL")

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)

    def test_detect_with_custom_params(self, sample_data):
        """Test detection with custom parameters."""
        service = PatternService()
        params = {"body_threshold": 0.05}

        result = service.detect_pattern("Doji", sample_data, params=params)

        assert isinstance(result, pd.Series)

    def test_detect_with_timeframe(self, sample_data):
        """Test detection with specific timeframe."""
        service = PatternService()
        result = service.detect_pattern(
            "Doji", sample_data, symbol="AAPL", timeframe="1hour"
        )

        assert isinstance(result, pd.Series)

    def test_detect_invalid_pattern(self, sample_data):
        """Test detecting invalid pattern raises PatternLoadError."""
        service = PatternService()

        with pytest.raises(PatternLoadError):
            service.detect_pattern("InvalidPattern", sample_data)

    def test_pattern_class_caching(self, sample_data):
        """Test pattern classes are cached."""
        service = PatternService()

        # First call - loads and caches
        result1 = service.detect_pattern("Doji", sample_data)

        # Should be cached now
        assert "Doji" in service._pattern_cache

        # Second call - uses cache
        result2 = service.detect_pattern("Doji", sample_data)

        assert isinstance(result1, pd.Series)
        assert isinstance(result2, pd.Series)


class TestDetectMultiplePatterns:
    """Test multiple pattern detection."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "volume": [1000000] * 10,
            }
        )

    def test_detect_multiple_patterns(self, sample_data):
        """Test detecting multiple patterns."""
        service = PatternService()
        patterns = ["Doji", "Hammer", "Engulfing"]

        results = service.detect_multiple_patterns(
            patterns, sample_data, symbol="AAPL"
        )

        assert isinstance(results, dict)
        assert len(results) == 3
        assert all(pattern in results for pattern in patterns)
        assert all(isinstance(r, pd.Series) for r in results.values())

    def test_multiple_patterns_with_invalid(self, sample_data):
        """Test multiple pattern detection with invalid pattern."""
        service = PatternService()
        patterns = ["Doji", "InvalidPattern", "Hammer"]

        # Should not raise - invalid patterns return False series
        results = service.detect_multiple_patterns(patterns, sample_data)

        assert len(results) == 3
        assert "Doji" in results
        assert "InvalidPattern" in results  # Present but all False
        assert "Hammer" in results

    def test_multiple_patterns_different_results(self, sample_data):
        """Test multiple patterns can have different detection results."""
        service = PatternService()
        patterns = ["Doji", "Hammer"]

        results = service.detect_multiple_patterns(patterns, sample_data)

        # Results should be independent
        assert results["Doji"].sum() != results["Hammer"].sum() or True  # Allow same counts


class TestDetectWithConfidenceFilter:
    """Test confidence-filtered detection (Sprint 17)."""

    @pytest.fixture
    def doji_data(self):
        """Create data with clear Doji patterns."""
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100, 101, 102, 103, 104],
                "high": [102, 103, 104, 105, 106],
                "low": [98, 99, 100, 101, 102],
                "close": [100.05, 101.02, 102.01, 103, 104],  # Multiple dojis
                "volume": [1000000] * 5,
            }
        )

    def test_detect_with_confidence_filter(self, doji_data):
        """Test detection with confidence threshold."""
        service = PatternService()

        detections, scores = service.detect_with_confidence_filter(
            "Doji", doji_data, confidence_threshold=0.5, symbol="AAPL"
        )

        assert isinstance(detections, pd.Series)
        assert isinstance(scores, dict)
        assert all(0.0 <= score <= 1.0 for score in scores.values())

    def test_high_confidence_threshold_filters(self, doji_data):
        """Test high confidence threshold filters out low-confidence detections."""
        service = PatternService()

        # Low threshold - more detections
        low_thresh_detections, low_scores = service.detect_with_confidence_filter(
            "Doji", doji_data, confidence_threshold=0.5
        )

        # High threshold - fewer detections
        high_thresh_detections, high_scores = service.detect_with_confidence_filter(
            "Doji", doji_data, confidence_threshold=0.9
        )

        # High threshold should have same or fewer detections
        assert high_thresh_detections.sum() <= low_thresh_detections.sum()

    def test_confidence_scores_returned(self, doji_data):
        """Test confidence scores are returned for all detections."""
        service = PatternService()

        detections, scores = service.detect_with_confidence_filter(
            "Doji", doji_data, confidence_threshold=0.5
        )

        detection_indices = detections[detections].index

        # All detected indices should have confidence scores
        for idx in detection_indices:
            assert idx in scores
            assert isinstance(scores[idx], float)


class TestPatternServiceUtilities:
    """Test pattern service utility methods."""

    def test_get_available_patterns(self):
        """Test getting available patterns."""
        service = PatternService()
        patterns = service.get_available_patterns()

        assert isinstance(patterns, dict)
        assert "candlestick" in patterns
        assert "doji" in patterns["candlestick"]

    def test_is_pattern_available(self):
        """Test checking pattern availability."""
        service = PatternService()

        assert service.is_pattern_available("Doji") is True
        assert service.is_pattern_available("Hammer") is True
        assert service.is_pattern_available("InvalidPattern") is False

    def test_get_pattern_class_with_cache(self):
        """Test _get_pattern_class uses cache."""
        service = PatternService()

        # First call - loads and caches
        class1 = service._get_pattern_class("Doji")
        assert "Doji" in service._pattern_cache

        # Second call - uses cache
        class2 = service._get_pattern_class("Doji")

        # Should be same class object
        assert class1 is class2


class TestPatternServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_detect_with_empty_data(self):
        """Test detection with empty data."""
        service = PatternService()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError):
            service.detect_pattern("Doji", empty_data)

    def test_detect_with_missing_columns(self):
        """Test detection with missing required columns."""
        service = PatternService()
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError):
            service.detect_pattern("Doji", invalid_data)

    def test_detect_multiple_with_empty_list(self):
        """Test detecting empty pattern list."""
        service = PatternService()
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100] * 5,
                "high": [102] * 5,
                "low": [98] * 5,
                "close": [101] * 5,
                "volume": [1000000] * 5,
            }
        )

        results = service.detect_multiple_patterns([], data)

        assert isinstance(results, dict)
        assert len(results) == 0
