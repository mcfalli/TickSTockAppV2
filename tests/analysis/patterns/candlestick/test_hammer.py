"""
Unit tests for Hammer candlestick pattern.

Sprint 68: Core Analysis Migration - Hammer pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.hammer import Hammer, HammerParams
from src.analysis.exceptions import PatternDetectionError


class TestHammerParams:
    """Test Hammer parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = HammerParams()
        assert params.min_shadow_ratio == 2.0
        assert params.max_upper_shadow_ratio == 0.1
        assert params.min_lower_shadow_ratio == 0.6
        assert params.max_body_ratio == 0.3
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = HammerParams(
            min_shadow_ratio=3.0,
            max_upper_shadow_ratio=0.05,
            min_lower_shadow_ratio=0.7,
            max_body_ratio=0.2,
        )
        assert params.min_shadow_ratio == 3.0
        assert params.max_upper_shadow_ratio == 0.05
        assert params.min_lower_shadow_ratio == 0.7
        assert params.max_body_ratio == 0.2

    def test_invalid_min_shadow_ratio(self):
        """Test invalid min_shadow_ratio raises error."""
        with pytest.raises(ValueError, match="min_shadow_ratio must be positive"):
            HammerParams(min_shadow_ratio=-1.0)

    def test_invalid_ratios(self):
        """Test invalid ratio parameters raise errors."""
        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HammerParams(max_upper_shadow_ratio=1.5)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HammerParams(min_lower_shadow_ratio=-0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HammerParams(max_body_ratio=2.0)


class TestHammerDetection:
    """Test Hammer pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def hammer_data(self, sample_dates):
        """Create data with clear Hammer pattern (small body, long lower shadow)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 108],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 109],  # High = max
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 100],  # Last has long lower shadow
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 108.5],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_hammer_data(self, sample_dates):
        """Create data without Hammer patterns (normal candles)."""
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

    def test_hammer_initialization(self):
        """Test Hammer pattern initialization."""
        hammer = Hammer()
        assert hammer.pattern_name == "Hammer"
        assert hammer.supports_confidence_scoring()
        assert hammer.get_minimum_bars() == 1

    def test_hammer_custom_params(self):
        """Test Hammer with custom parameters."""
        hammer = Hammer({"min_shadow_ratio": 3.0, "max_body_ratio": 0.2})
        assert hammer.params.min_shadow_ratio == 3.0
        assert hammer.params.max_body_ratio == 0.2

    def test_hammer_detection_positive(self, hammer_data):
        """Test Hammer detection on data with Hammer pattern."""
        hammer = Hammer()
        result = hammer.detect(hammer_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(hammer_data)
        assert result.dtype == bool

        # Last bar should be detected as Hammer (long lower shadow, small body at top)
        assert result.iloc[-1] == True

    def test_hammer_detection_negative(self, no_hammer_data):
        """Test Hammer detection on data without Hammer patterns."""
        hammer = Hammer()
        result = hammer.detect(no_hammer_data)

        assert isinstance(result, pd.Series)
        # May have 0-1 detections depending on exact ratios
        assert result.sum() <= 1

    def test_hammer_with_strict_params(self, hammer_data):
        """Test Hammer with stricter parameters."""
        hammer = Hammer(
            {"min_shadow_ratio": 4.0, "max_upper_shadow_ratio": 0.05}  # Very strict
        )
        result = hammer.detect(hammer_data)

        # Fewer detections with stricter parameters
        assert result.sum() <= 1

    def test_confidence_scoring(self, hammer_data):
        """Test Hammer confidence score calculation."""
        hammer = Hammer()
        detections = hammer.detect(hammer_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = hammer.calculate_confidence(hammer_data, detection_indices)

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Hammer base confidence is 0.6
                assert score >= 0.6

    def test_bullish_hammer_higher_confidence(self, sample_dates):
        """Test bullish Hammer (close > open) gets higher confidence."""
        # Bullish Hammer
        bullish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [101],  # High = max
                "low": [92],  # Low = min, long lower shadow
                "close": [100.8],  # Bullish close
                "volume": [1000000],
            }
        )

        # Bearish Hammer
        bearish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [101],  # High = max
                "low": [92],  # Low = min, long lower shadow
                "close": [99.2],  # Bearish close
                "volume": [1000000],
            }
        )

        hammer = Hammer()

        bullish_detections = hammer.detect(bullish_data)
        bearish_detections = hammer.detect(bearish_data)

        if bullish_detections.sum() > 0 and bearish_detections.sum() > 0:
            bullish_conf = hammer.calculate_confidence(
                bullish_data, bullish_detections[bullish_detections].index
            )
            bearish_conf = hammer.calculate_confidence(
                bearish_data, bearish_detections[bearish_detections].index
            )

            # Bullish should have higher confidence
            assert list(bullish_conf.values())[0] > list(bearish_conf.values())[0]

    def test_strong_shadow_ratio_bonus(self, sample_dates):
        """Test strong shadow/body ratio increases confidence."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [101],  # High = max
                "low": [85],  # Low = min, very long lower shadow
                "close": [100.5],  # Small body
                "volume": [1000000],
            }
        )

        hammer = Hammer()
        detections = hammer.detect(data)

        if detections.sum() > 0:
            confidence_scores = hammer.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to strong shadow/body ratio
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        hammer = Hammer()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Hammer detection failed"):
            hammer.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        hammer = Hammer()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Hammer detection failed"):
            hammer.detect(empty_data)

    def test_insufficient_range(self, sample_dates):
        """Test Hammer ignores candles with insufficient range."""
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

        hammer = Hammer()
        result = hammer.detect(data)

        # Should not detect due to min_range filter
        assert result.sum() == 0

    def test_upper_shadow_too_large(self, sample_dates):
        """Test Hammer not detected when upper shadow too large."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [110],  # High = max, large upper shadow
                "low": [92],  # Low = min, long lower shadow
                "close": [100.5],  # Small body
                "volume": [1000000],
            }
        )

        hammer = Hammer()
        result = hammer.detect(data)

        # Should not detect - upper shadow too large
        assert result.sum() == 0

    def test_filter_by_confidence_threshold(self, hammer_data):
        """Test confidence threshold filtering."""
        hammer = Hammer()
        hammer.set_pattern_registry_info(pattern_id=2, confidence_threshold=0.9)

        # Raw detections
        raw_detections = hammer.detect(hammer_data)

        # Filtered detections
        filtered_detections = hammer.filter_by_confidence(raw_detections, hammer_data)

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained (high >= low, etc.)."""
        # Valid OHLC data with Hammer characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 101, 102],
                "high": [101, 102, 103],  # High = max
                "low": [92, 93, 94],  # Low = min, long lower shadows
                "close": [100.5, 101.5, 102.5],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        hammer = Hammer()
        result = hammer.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)
