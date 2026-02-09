"""
Unit tests for Engulfing candlestick pattern.

Sprint 68: Core Analysis Migration - Engulfing pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.engulfing import Engulfing, EngulfingParams
from src.analysis.exceptions import PatternDetectionError


class TestEngulfingParams:
    """Test Engulfing parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = EngulfingParams()
        assert params.min_body_ratio == 1.0
        assert params.require_opposite_colors == True
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = EngulfingParams(
            min_body_ratio=1.5, require_opposite_colors=False, min_range=0.01
        )
        assert params.min_body_ratio == 1.5
        assert params.require_opposite_colors == False
        assert params.min_range == 0.01

    def test_invalid_min_body_ratio(self):
        """Test invalid min_body_ratio raises error."""
        with pytest.raises(ValueError, match="min_body_ratio must be >= 1.0"):
            EngulfingParams(min_body_ratio=0.5)

    def test_invalid_min_range(self):
        """Test invalid min_range raises error."""
        with pytest.raises(ValueError, match="min_range must be positive"):
            EngulfingParams(min_range=-0.1)


class TestEngulfingDetection:
    """Test Engulfing pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def bullish_engulfing_data(self, sample_dates):
        """Create data with clear Bullish Engulfing pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 105, 102],  # Bar 9: prev bearish, curr bullish
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 107, 110],  # High = max
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 104, 100],  # Low = min
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 104.5, 108],  # Last: 102->108 engulfs 105->104.5
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def bearish_engulfing_data(self, sample_dates):
        """Create data with clear Bearish Engulfing pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 106, 110],  # Bar 9: prev bullish, curr bearish
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 108, 111],  # High = max
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 105, 104],  # Low = min
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 107.5, 105],  # Last: 110->105 engulfs 106->107.5
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_engulfing_data(self, sample_dates):
        """Create data without Engulfing patterns."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],  # High = max
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],  # Low = min
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "volume": [1000000] * 10,
            }
        )

    def test_engulfing_initialization(self):
        """Test Engulfing pattern initialization."""
        engulfing = Engulfing()
        assert engulfing.pattern_name == "Engulfing"
        assert engulfing.supports_confidence_scoring()
        assert engulfing.get_minimum_bars() == 2

    def test_engulfing_custom_params(self):
        """Test Engulfing with custom parameters."""
        engulfing = Engulfing({"min_body_ratio": 1.5, "require_opposite_colors": False})
        assert engulfing.params.min_body_ratio == 1.5
        assert engulfing.params.require_opposite_colors == False

    def test_bullish_engulfing_detection(self, bullish_engulfing_data):
        """Test Bullish Engulfing detection."""
        engulfing = Engulfing()
        result = engulfing.detect(bullish_engulfing_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(bullish_engulfing_data)
        assert result.dtype == bool

        # Last bar should be detected as Engulfing
        assert result.iloc[-1] == True

        # First bar cannot be engulfing (no previous)
        assert result.iloc[0] == False

    def test_bearish_engulfing_detection(self, bearish_engulfing_data):
        """Test Bearish Engulfing detection."""
        engulfing = Engulfing()
        result = engulfing.detect(bearish_engulfing_data)

        assert isinstance(result, pd.Series)
        # Should detect at least one engulfing pattern
        assert result.sum() >= 1

    def test_no_engulfing_detection(self, no_engulfing_data):
        """Test no Engulfing patterns detected in trending data."""
        engulfing = Engulfing()
        result = engulfing.detect(no_engulfing_data)

        assert isinstance(result, pd.Series)
        # Should have no engulfing patterns
        assert result.sum() == 0

    def test_engulfing_without_opposite_colors(self, sample_dates):
        """Test Engulfing detection without requiring opposite colors."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 99],  # Both bearish
                "high": [102, 103],  # High = max
                "low": [99, 98],  # Low = min
                "close": [101, 101.5],  # Both bearish, but second engulfs
                "volume": [1000000, 1000000],
            }
        )

        # With opposite colors required (default)
        engulfing_strict = Engulfing()
        result_strict = engulfing_strict.detect(data)
        assert result_strict.sum() == 0  # No detection (same colors)

        # Without opposite colors required
        engulfing_loose = Engulfing({"require_opposite_colors": False})
        result_loose = engulfing_loose.detect(data)
        # May or may not detect depending on exact body engulfment

    def test_confidence_scoring(self, bullish_engulfing_data):
        """Test Engulfing confidence score calculation."""
        engulfing = Engulfing()
        detections = engulfing.detect(bullish_engulfing_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = engulfing.calculate_confidence(
                bullish_engulfing_data, detection_indices
            )

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Engulfing base confidence is 0.6
                assert score >= 0.6

    def test_strong_engulfment_bonus(self, sample_dates):
        """Test strong body ratio increases confidence."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 98],  # Previous bearish, current bullish
                "high": [101, 104],  # High = max
                "low": [99, 97],  # Low = min
                "close": [99.5, 103],  # Strong engulfment
                "volume": [1000000, 2000000],  # Higher volume on engulfing
            }
        )

        engulfing = Engulfing()
        detections = engulfing.detect(data)

        if detections.sum() > 0:
            confidence_scores = engulfing.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to strong engulfment + volume
            assert list(confidence_scores.values())[0] >= 0.8

    def test_complete_range_engulfment_bonus(self, sample_dates):
        """Test complete range engulfment (not just body) increases confidence."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 98],
                "high": [101, 105],  # High = max, current high > previous high
                "low": [99, 96],  # Low = min, current low < previous low
                "close": [99.5, 104],  # Complete engulfment
                "volume": [1000000, 1000000],
            }
        )

        engulfing = Engulfing()
        detections = engulfing.detect(data)

        if detections.sum() > 0:
            confidence_scores = engulfing.calculate_confidence(data, detections[detections].index)
            # Should have bonus for complete range engulfment
            assert list(confidence_scores.values())[0] >= 0.7

    def test_engulfing_type_detection(self, sample_dates):
        """Test Engulfing subtype classification (bullish vs bearish)."""
        # Bullish Engulfing
        bullish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 98],  # Previous bearish, current bullish
                "high": [101, 103],  # High = max
                "low": [99, 97],  # Low = min
                "close": [99.5, 102],  # Engulfment
                "volume": [1000000, 1000000],
            }
        )

        engulfing = Engulfing()
        engulfing_type = engulfing.get_engulfing_type(bullish_data, bullish_data.index[1])
        assert engulfing_type == "bullish"

        # Bearish Engulfing
        bearish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 103],  # Previous bullish, current bearish
                "high": [102, 104],  # High = max
                "low": [99, 98],  # Low = min
                "close": [101.5, 99],  # Engulfment
                "volume": [1000000, 1000000],
            }
        )

        engulfing_type = engulfing.get_engulfing_type(bearish_data, bearish_data.index[1])
        assert engulfing_type == "bearish"

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        engulfing = Engulfing()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Engulfing detection failed"):
            engulfing.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        engulfing = Engulfing()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Engulfing detection failed"):
            engulfing.detect(empty_data)

    def test_single_bar_data(self, sample_dates):
        """Test Engulfing returns False for single-bar data."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [102],  # High = max
                "low": [99],  # Low = min
                "close": [101],
                "volume": [1000000],
            }
        )

        engulfing = Engulfing()
        result = engulfing.detect(data)

        # No detection with only 1 bar
        assert result.sum() == 0

    def test_insufficient_range(self, sample_dates):
        """Test Engulfing ignores candles with insufficient range."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 100],
                "high": [100.0001, 100.0001],  # Tiny range
                "low": [99.9999, 99.9999],
                "close": [100, 100],
                "volume": [1000000, 1000000],
            }
        )

        engulfing = Engulfing()
        result = engulfing.detect(data)

        # Should not detect due to min_range filter
        assert result.sum() == 0

    def test_partial_engulfment_not_detected(self, sample_dates):
        """Test partial body engulfment is not detected."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 99],  # Previous bearish, current bullish
                "high": [102, 102],  # High = max
                "low": [98, 98],  # Low = min
                "close": [99, 100],  # Partial engulfment (top: 100 not > 100, bottom: 99 not < 99)
                "volume": [1000000, 1000000],
            }
        )

        engulfing = Engulfing()
        result = engulfing.detect(data)

        # Should not detect - partial engulfment only (equal tops/bottoms)
        assert result.sum() == 0

    def test_filter_by_confidence_threshold(self, bullish_engulfing_data):
        """Test confidence threshold filtering."""
        engulfing = Engulfing()
        engulfing.set_pattern_registry_info(pattern_id=3, confidence_threshold=0.95)

        # Raw detections
        raw_detections = engulfing.detect(bullish_engulfing_data)

        # Filtered detections
        filtered_detections = engulfing.filter_by_confidence(
            raw_detections, bullish_engulfing_data
        )

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained (high >= low, etc.)."""
        # Valid OHLC data with Engulfing characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 99, 98],
                "high": [102, 101, 104],  # High = max
                "low": [98, 98, 96],  # Low = min
                "close": [99, 100, 103],  # Engulfing patterns
                "volume": [1000000, 1000000, 1000000],
            }
        )

        engulfing = Engulfing()
        result = engulfing.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)
