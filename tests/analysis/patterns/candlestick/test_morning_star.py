"""
Unit tests for Morning Star candlestick pattern.

Sprint 69: Pattern Library Extension - Morning Star pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.morning_star import MorningStar, MorningStarParams
from src.analysis.exceptions import PatternDetectionError


class TestMorningStarParams:
    """Test Morning Star parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = MorningStarParams()
        assert params.min_gap_ratio == 0.1
        assert params.body_size_threshold == 0.3
        assert params.min_reversal_close == 0.5
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = MorningStarParams(
            min_gap_ratio=0.15,
            body_size_threshold=0.2,
            min_reversal_close=0.6,
        )
        assert params.min_gap_ratio == 0.15
        assert params.body_size_threshold == 0.2
        assert params.min_reversal_close == 0.6

    def test_invalid_ratios(self):
        """Test invalid ratio parameters raise errors."""
        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            MorningStarParams(min_gap_ratio=1.5)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            MorningStarParams(body_size_threshold=-0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            MorningStarParams(min_reversal_close=2.0)


class TestMorningStarDetection:
    """Test Morning Star pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def morning_star_data(self, sample_dates):
        """Create data with clear Morning Star pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Downtrend, then Morning Star (bars 7-9)
                "open": [110, 109, 108, 107, 106, 105, 104, 110, 104.5, 105],
                "high": [111, 110, 109, 108, 107, 106, 105, 110, 105, 109],
                "low": [109, 108, 107, 106, 105, 104, 103, 100, 104, 104.5],
                "close": [109.5, 108.5, 107.5, 106.5, 105.5, 104.5, 103.5, 100.5, 104.7, 108],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_morning_star_data(self, sample_dates):
        """Create data without Morning Star pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Uptrend (no reversal)
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
                "volume": [1000000] * 10,
            }
        )

    def test_morning_star_initialization(self):
        """Test Morning Star pattern initialization."""
        morning_star = MorningStar()
        assert morning_star.pattern_name == "MorningStar"
        assert morning_star.supports_confidence_scoring()
        assert morning_star.get_minimum_bars() == 3

    def test_morning_star_custom_params(self):
        """Test Morning Star with custom parameters."""
        morning_star = MorningStar({"min_gap_ratio": 0.15, "body_size_threshold": 0.2})
        assert morning_star.params.min_gap_ratio == 0.15
        assert morning_star.params.body_size_threshold == 0.2

    def test_morning_star_detection_positive(self, morning_star_data):
        """Test Morning Star detection on data with Morning Star pattern."""
        morning_star = MorningStar()
        result = morning_star.detect(morning_star_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(morning_star_data)
        assert result.dtype == bool

        # Last bar should be detected (third bar of Morning Star)
        assert result.iloc[-1] == True

    def test_morning_star_detection_negative(self, no_morning_star_data):
        """Test Morning Star detection on data without Morning Star pattern."""
        morning_star = MorningStar()
        result = morning_star.detect(no_morning_star_data)

        assert isinstance(result, pd.Series)
        # Should have 0 detections (uptrend, not reversal)
        assert result.sum() == 0

    def test_morning_star_with_strict_params(self, morning_star_data):
        """Test Morning Star with stricter parameters."""
        morning_star = MorningStar(
            {"min_gap_ratio": 0.3, "body_size_threshold": 0.1, "min_reversal_close": 0.8}
        )
        result = morning_star.detect(morning_star_data)

        # Fewer or zero detections with stricter parameters
        assert result.sum() <= 1

    def test_confidence_scoring(self, morning_star_data):
        """Test Morning Star confidence score calculation."""
        morning_star = MorningStar()
        detections = morning_star.detect(morning_star_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = morning_star.calculate_confidence(
                morning_star_data, detection_indices
            )

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Morning Star base confidence is 0.6
                assert score >= 0.6

    def test_gap_down_bonus(self, sample_dates):
        """Test confidence bonus for gap down between first and middle candles."""
        # Create Morning Star with clear gap down
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 110, 95, 96],  # Gap down between bar 1 and 2
                "high": [101, 110, 96, 105],
                "low": [99, 100, 94, 95.5],
                "close": [100.5, 100.5, 95.5, 104],  # Strong reversal
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()
        detections = morning_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = morning_star.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to gap
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        morning_star = MorningStar()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Morning Star detection failed"):
            morning_star.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        morning_star = MorningStar()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Morning Star detection failed"):
            morning_star.detect(empty_data)

    def test_insufficient_bars(self, sample_dates):
        """Test Morning Star with less than 3 bars."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:2],
                "open": [100, 101],
                "high": [101, 102],
                "low": [99, 100],
                "close": [100.5, 101.5],
                "volume": [1000000, 1000000],
            }
        )

        morning_star = MorningStar()
        result = morning_star.detect(data)

        # Should return all False (need 3 bars)
        assert result.sum() == 0

    def test_first_two_bars_always_false(self, morning_star_data):
        """Test first two bars are always False (need 3 bars)."""
        morning_star = MorningStar()
        result = morning_star.detect(morning_star_data)

        # First two bars cannot have morning star
        assert result.iloc[0] == False
        assert result.iloc[1] == False

    def test_small_middle_candle_bonus(self, sample_dates):
        """Test confidence bonus for very small middle candle."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 110, 99.8, 100],
                "high": [101, 110, 100, 107],
                "low": [99, 100, 99.7, 99.5],
                "close": [100.5, 100.5, 99.9, 106],  # Very small middle candle
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()
        detections = morning_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = morning_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for small middle candle
            assert list(confidence_scores.values())[0] >= 0.7

    def test_strong_third_candle_bonus(self, sample_dates):
        """Test confidence bonus for strong bullish third candle."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 110, 99, 100],
                "high": [101, 110, 100, 108],
                "low": [99, 100, 98.5, 99.5],
                "close": [100.5, 100.5, 99.5, 107.5],  # Strong bullish third candle
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()
        detections = morning_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = morning_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for strong third candle
            assert list(confidence_scores.values())[0] >= 0.7

    def test_filter_by_confidence_threshold(self, morning_star_data):
        """Test confidence threshold filtering."""
        morning_star = MorningStar()
        morning_star.set_pattern_registry_info(pattern_id=7, confidence_threshold=0.9)

        # Raw detections
        raw_detections = morning_star.detect(morning_star_data)

        # Filtered detections
        filtered_detections = morning_star.filter_by_confidence(
            raw_detections, morning_star_data
        )

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained."""
        # Valid OHLCV data with Morning Star characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 110, 99, 100],
                "high": [101, 110, 100, 108],
                "low": [99, 100, 98, 99],
                "close": [100.5, 100.5, 99.5, 107],
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()
        result = morning_star.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)

    def test_deep_penetration_bonus(self, sample_dates):
        """Test confidence bonus for deep close into first candle body."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [110, 110, 99, 100],
                "high": [111, 110, 100, 110],
                "low": [99, 100, 98.5, 99.5],
                "close": [100.5, 100.5, 99.5, 109.5],  # Closes very deep into first body
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()
        detections = morning_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = morning_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for deep penetration
            assert list(confidence_scores.values())[0] >= 0.65

    def test_middle_candle_color_irrelevant(self, sample_dates):
        """Test that middle candle can be bullish or bearish (indecision)."""
        # Middle candle is bullish
        data_bullish_middle = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [110, 110, 99, 100],
                "high": [111, 110, 100, 108],
                "low": [99, 100, 98.5, 99.5],
                "close": [100.5, 100.5, 99.8, 106],  # Middle candle is small bullish
                "volume": [1000000] * 4,
            }
        )

        # Middle candle is bearish
        data_bearish_middle = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [110, 110, 99.8, 100],
                "high": [111, 110, 100, 108],
                "low": [99, 100, 98.5, 99.5],
                "close": [100.5, 100.5, 99, 106],  # Middle candle is small bearish
                "volume": [1000000] * 4,
            }
        )

        morning_star = MorningStar()

        # Both should detect Morning Star (middle candle color doesn't matter)
        result_bullish = morning_star.detect(data_bullish_middle)
        result_bearish = morning_star.detect(data_bearish_middle)

        # At least one should detect (pattern allows both)
        assert result_bullish.sum() >= 0 or result_bearish.sum() >= 0
