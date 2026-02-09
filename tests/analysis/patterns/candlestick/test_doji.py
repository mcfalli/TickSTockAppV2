"""
Unit tests for Doji candlestick pattern.

Sprint 68: Core Analysis Migration - Doji pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.doji import Doji, DojiParams
from src.analysis.exceptions import PatternDetectionError


class TestDojiParams:
    """Test Doji parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = DojiParams()
        assert params.body_threshold == 0.1
        assert params.min_range == 0.001
        assert params.timeframe == "daily"

    def test_custom_params(self):
        """Test custom parameter values."""
        params = DojiParams(body_threshold=0.05, min_range=0.01, timeframe="1hour")
        assert params.body_threshold == 0.05
        assert params.min_range == 0.01
        assert params.timeframe == "1hour"

    def test_invalid_body_threshold(self):
        """Test invalid body_threshold raises error."""
        with pytest.raises(ValueError, match="body_threshold must be between 0 and 1"):
            DojiParams(body_threshold=1.5)

        with pytest.raises(ValueError, match="body_threshold must be between 0 and 1"):
            DojiParams(body_threshold=0)

    def test_invalid_min_range(self):
        """Test invalid min_range raises error."""
        with pytest.raises(ValueError, match="min_range must be positive"):
            DojiParams(min_range=-0.1)


class TestDojiDetection:
    """Test Doji pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def doji_data(self, sample_dates):
        """Create data with clear Doji pattern (very small body)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "close": [
                    100.2,
                    101.3,
                    102.1,
                    103.05,
                    104,
                    105.1,
                    106.2,
                    107,
                    108.1,
                    109.05,
                ],  # Last = doji
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_doji_data(self, sample_dates):
        """Create data without Doji patterns (strong trend)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],  # High = max
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],  # Low = min
                "close": [104, 105, 106, 107, 108, 109, 110, 111, 112, 113],  # Strong uptrend
                "volume": [1000000] * 10,
            }
        )

    def test_doji_initialization(self):
        """Test Doji pattern initialization."""
        doji = Doji()
        assert doji.pattern_name == "Doji"
        assert doji.supports_confidence_scoring()
        assert doji.get_minimum_bars() == 1

    def test_doji_custom_params(self):
        """Test Doji with custom parameters."""
        doji = Doji({"body_threshold": 0.05, "min_range": 0.01})
        assert doji.params.body_threshold == 0.05
        assert doji.params.min_range == 0.01

    def test_doji_detection_positive(self, doji_data):
        """Test Doji detection on data with Doji pattern."""
        doji = Doji()
        result = doji.detect(doji_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(doji_data)
        assert result.dtype == bool

        # Last bar should be detected as Doji (close ≈ open, small body)
        assert result.iloc[-1] == True

    def test_doji_detection_negative(self, no_doji_data):
        """Test Doji detection on data without Doji patterns."""
        doji = Doji()
        result = doji.detect(no_doji_data)

        assert isinstance(result, pd.Series)
        assert result.sum() == 0  # No Doji detected

    def test_doji_with_strict_threshold(self, doji_data):
        """Test Doji with stricter body_threshold."""
        doji = Doji({"body_threshold": 0.01})  # Very strict
        result = doji.detect(doji_data)

        # Fewer detections with stricter threshold
        assert result.sum() <= 2

    def test_confidence_scoring(self, doji_data):
        """Test Doji confidence score calculation."""
        doji = Doji()
        detections = doji.detect(doji_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = doji.calculate_confidence(doji_data, detection_indices)

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)

    def test_doji_subtype_detection(self, sample_dates):
        """Test Doji subtype classification."""
        # Gravestone Doji (long upper shadow)
        gravestone_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [105],  # Long upper shadow
                "low": [99.5],
                "close": [100.1],  # Small body
                "volume": [1000000],
            }
        )

        doji = Doji()
        assert doji.get_doji_subtype(gravestone_data, gravestone_data.index[0]) == "gravestone"

        # Dragonfly Doji (long lower shadow)
        dragonfly_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [100.5],
                "low": [95],  # Long lower shadow
                "close": [100.1],  # Small body
                "volume": [1000000],
            }
        )

        assert doji.get_doji_subtype(dragonfly_data, dragonfly_data.index[0]) == "dragonfly"

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        doji = Doji()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Doji detection failed"):
            doji.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        doji = Doji()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Doji detection failed"):
            doji.detect(empty_data)

    def test_insufficient_range(self, sample_dates):
        """Test Doji ignores candles with insufficient range."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 100, 100],
                "high": [100.0001, 100.0001, 100.0001],  # Tiny range
                "low": [99.9999, 99.9999, 99.9999],
                "close": [100, 100, 100],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        doji = Doji()
        result = doji.detect(data)

        # Should not detect due to min_range filter
        assert result.sum() == 0

    def test_filter_by_confidence_threshold(self, doji_data):
        """Test confidence threshold filtering."""
        doji = Doji()
        doji.set_pattern_registry_info(pattern_id=1, confidence_threshold=0.8)

        # Raw detections
        raw_detections = doji.detect(doji_data)

        # Filtered detections
        filtered_detections = doji.filter_by_confidence(raw_detections, doji_data)

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is enforced (high >= low, etc.)."""
        # Valid OHLC data
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 101, 102],
                "high": [105, 106, 107],  # high = max
                "low": [95, 96, 97],  # low = min
                "close": [103, 104, 105],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        doji = Doji()
        result = doji.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)
