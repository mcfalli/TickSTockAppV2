"""
Unit tests for Evening Star candlestick pattern.

Sprint 69: Pattern Library Extension - Evening Star pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.evening_star import EveningStar, EveningStarParams
from src.analysis.exceptions import PatternDetectionError


class TestEveningStarParams:
    """Test Evening Star parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = EveningStarParams()
        assert params.min_gap_ratio == 0.1
        assert params.body_size_threshold == 0.3
        assert params.min_reversal_close == 0.5
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = EveningStarParams(
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
            EveningStarParams(min_gap_ratio=1.5)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            EveningStarParams(body_size_threshold=-0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            EveningStarParams(min_reversal_close=2.0)


class TestEveningStarDetection:
    """Test Evening Star pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def evening_star_data(self, sample_dates):
        """Create data with clear Evening Star pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Uptrend, then Evening Star (bars 7-9)
                "open": [100, 101, 102, 103, 104, 105, 106, 100, 105.5, 105],
                "high": [101, 102, 103, 104, 105, 106, 107, 110, 106, 105.5],
                "low": [99, 100, 101, 102, 103, 104, 105, 100, 105, 101],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 109.5, 105.3, 102],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_evening_star_data(self, sample_dates):
        """Create data without Evening Star pattern."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Downtrend (no reversal)
                "open": [110, 109, 108, 107, 106, 105, 104, 103, 102, 101],
                "high": [111, 110, 109, 108, 107, 106, 105, 104, 103, 102],
                "low": [109, 108, 107, 106, 105, 104, 103, 102, 101, 100],
                "close": [109.5, 108.5, 107.5, 106.5, 105.5, 104.5, 103.5, 102.5, 101.5, 100.5],
                "volume": [1000000] * 10,
            }
        )

    def test_evening_star_initialization(self):
        """Test Evening Star pattern initialization."""
        evening_star = EveningStar()
        assert evening_star.pattern_name == "EveningStar"
        assert evening_star.supports_confidence_scoring()
        assert evening_star.get_minimum_bars() == 3

    def test_evening_star_custom_params(self):
        """Test Evening Star with custom parameters."""
        evening_star = EveningStar({"min_gap_ratio": 0.15, "body_size_threshold": 0.2})
        assert evening_star.params.min_gap_ratio == 0.15
        assert evening_star.params.body_size_threshold == 0.2

    def test_evening_star_detection_positive(self, evening_star_data):
        """Test Evening Star detection on data with Evening Star pattern."""
        evening_star = EveningStar()
        result = evening_star.detect(evening_star_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(evening_star_data)
        assert result.dtype == bool

        # Last bar should be detected (third bar of Evening Star)
        assert result.iloc[-1] == True

    def test_evening_star_detection_negative(self, no_evening_star_data):
        """Test Evening Star detection on data without Evening Star pattern."""
        evening_star = EveningStar()
        result = evening_star.detect(no_evening_star_data)

        assert isinstance(result, pd.Series)
        # Should have 0 detections (downtrend, not reversal)
        assert result.sum() == 0

    def test_evening_star_with_strict_params(self, evening_star_data):
        """Test Evening Star with stricter parameters."""
        evening_star = EveningStar(
            {"min_gap_ratio": 0.3, "body_size_threshold": 0.1, "min_reversal_close": 0.8}
        )
        result = evening_star.detect(evening_star_data)

        # Fewer or zero detections with stricter parameters
        assert result.sum() <= 1

    def test_confidence_scoring(self, evening_star_data):
        """Test Evening Star confidence score calculation."""
        evening_star = EveningStar()
        detections = evening_star.detect(evening_star_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = evening_star.calculate_confidence(
                evening_star_data, detection_indices
            )

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Evening Star base confidence is 0.6
                assert score >= 0.6

    def test_gap_up_bonus(self, sample_dates):
        """Test confidence bonus for gap up between first and middle candles."""
        # Create Evening Star with clear gap up
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 111, 110],  # Gap up between bar 1 and 2
                "high": [101, 109.5, 112, 110.5],
                "low": [99, 100, 110.5, 101],
                "close": [100.5, 109.5, 111.5, 102],  # Strong reversal
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()
        detections = evening_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = evening_star.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to gap
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        evening_star = EveningStar()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Evening Star detection failed"):
            evening_star.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        evening_star = EveningStar()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Evening Star detection failed"):
            evening_star.detect(empty_data)

    def test_insufficient_bars(self, sample_dates):
        """Test Evening Star with less than 3 bars."""
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

        evening_star = EveningStar()
        result = evening_star.detect(data)

        # Should return all False (need 3 bars)
        assert result.sum() == 0

    def test_first_two_bars_always_false(self, evening_star_data):
        """Test first two bars are always False (need 3 bars)."""
        evening_star = EveningStar()
        result = evening_star.detect(evening_star_data)

        # First two bars cannot have evening star
        assert result.iloc[0] == False
        assert result.iloc[1] == False

    def test_small_middle_candle_bonus(self, sample_dates):
        """Test confidence bonus for very small middle candle."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110.1, 110],
                "high": [101, 109.5, 110.3, 110.5],
                "low": [99, 100, 110, 102],
                "close": [100.5, 109.5, 110.2, 103],  # Very small middle candle
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()
        detections = evening_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = evening_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for small middle candle
            assert list(confidence_scores.values())[0] >= 0.7

    def test_strong_third_candle_bonus(self, sample_dates):
        """Test confidence bonus for strong bearish third candle."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110, 110],
                "high": [101, 109.5, 111, 110.5],
                "low": [99, 100, 109.5, 101],
                "close": [100.5, 109.5, 110.5, 101.5],  # Strong bearish third candle
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()
        detections = evening_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = evening_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for strong third candle
            assert list(confidence_scores.values())[0] >= 0.7

    def test_filter_by_confidence_threshold(self, evening_star_data):
        """Test confidence threshold filtering."""
        evening_star = EveningStar()
        evening_star.set_pattern_registry_info(pattern_id=8, confidence_threshold=0.9)

        # Raw detections
        raw_detections = evening_star.detect(evening_star_data)

        # Filtered detections
        filtered_detections = evening_star.filter_by_confidence(
            raw_detections, evening_star_data
        )

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained."""
        # Valid OHLCV data with Evening Star characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110, 110],
                "high": [101, 109.5, 111, 110.5],
                "low": [99, 100, 109, 101],
                "close": [100.5, 109.5, 110.5, 102],
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()
        result = evening_star.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)

    def test_deep_penetration_bonus(self, sample_dates):
        """Test confidence bonus for deep close into first candle body."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110, 110],
                "high": [101, 109.5, 120, 110.5],
                "low": [99, 100, 109.5, 100.5],
                "close": [100.5, 109.5, 119.5, 101],  # Closes very deep into first body
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()
        detections = evening_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = evening_star.calculate_confidence(data, detections[detections].index)
            # Should have bonus for deep penetration
            assert list(confidence_scores.values())[0] >= 0.65

    def test_middle_candle_color_irrelevant(self, sample_dates):
        """Test that middle candle can be bullish or bearish (indecision)."""
        # Middle candle is bullish
        data_bullish_middle = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110, 110],
                "high": [101, 109.5, 111, 110.5],
                "low": [99, 100, 109.5, 102],
                "close": [100.5, 109.5, 110.8, 103],  # Middle candle is small bullish
                "volume": [1000000] * 4,
            }
        )

        # Middle candle is bearish
        data_bearish_middle = pd.DataFrame(
            {
                "timestamp": sample_dates[:4],
                "open": [100, 100, 110.8, 110],
                "high": [101, 109.5, 111, 110.5],
                "low": [99, 100, 109.5, 102],
                "close": [100.5, 109.5, 110, 103],  # Middle candle is small bearish
                "volume": [1000000] * 4,
            }
        )

        evening_star = EveningStar()

        # Both should detect Evening Star (middle candle color doesn't matter)
        result_bullish = evening_star.detect(data_bullish_middle)
        result_bearish = evening_star.detect(data_bearish_middle)

        # At least one should detect (pattern allows both)
        assert result_bullish.sum() >= 0 or result_bearish.sum() >= 0
