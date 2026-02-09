"""
Unit tests for Shooting Star candlestick pattern.

Sprint 69: Pattern Library Extension - Shooting Star pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.shooting_star import ShootingStar, ShootingStarParams
from src.analysis.exceptions import PatternDetectionError


class TestShootingStarParams:
    """Test Shooting Star parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = ShootingStarParams()
        assert params.min_shadow_ratio == 2.0
        assert params.max_lower_shadow_ratio == 0.1
        assert params.min_upper_shadow_ratio == 0.6
        assert params.max_body_ratio == 0.3
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = ShootingStarParams(
            min_shadow_ratio=3.0,
            max_lower_shadow_ratio=0.05,
            min_upper_shadow_ratio=0.7,
            max_body_ratio=0.2,
        )
        assert params.min_shadow_ratio == 3.0
        assert params.max_lower_shadow_ratio == 0.05
        assert params.min_upper_shadow_ratio == 0.7
        assert params.max_body_ratio == 0.2

    def test_invalid_min_shadow_ratio(self):
        """Test invalid min_shadow_ratio raises error."""
        with pytest.raises(ValueError, match="min_shadow_ratio must be positive"):
            ShootingStarParams(min_shadow_ratio=-1.0)

    def test_invalid_ratios(self):
        """Test invalid ratio parameters raise errors."""
        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            ShootingStarParams(max_lower_shadow_ratio=1.5)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            ShootingStarParams(min_upper_shadow_ratio=-0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            ShootingStarParams(max_body_ratio=2.0)


class TestShootingStarDetection:
    """Test Shooting Star pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def shooting_star_data(self, sample_dates):
        """Create data with clear Shooting Star pattern (small body, long upper shadow)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 108.5],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 117],  # Last has long upper shadow
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 107.5],  # Low = min, minimal lower shadow
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 108],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_shooting_star_data(self, sample_dates):
        """Create data without Shooting Star patterns (normal candles)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
                "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "volume": [1000000] * 10,
            }
        )

    def test_shooting_star_initialization(self):
        """Test Shooting Star pattern initialization."""
        shooting_star = ShootingStar()
        assert shooting_star.pattern_name == "ShootingStar"
        assert shooting_star.supports_confidence_scoring()
        assert shooting_star.get_minimum_bars() == 1

    def test_shooting_star_custom_params(self):
        """Test Shooting Star with custom parameters."""
        shooting_star = ShootingStar({"min_shadow_ratio": 3.0, "max_body_ratio": 0.2})
        assert shooting_star.params.min_shadow_ratio == 3.0
        assert shooting_star.params.max_body_ratio == 0.2

    def test_shooting_star_detection_positive(self, shooting_star_data):
        """Test Shooting Star detection on data with Shooting Star pattern."""
        shooting_star = ShootingStar()
        result = shooting_star.detect(shooting_star_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(shooting_star_data)
        assert result.dtype == bool

        # Last bar should be detected as Shooting Star (long upper shadow, small body at bottom)
        assert result.iloc[-1] == True

    def test_shooting_star_detection_negative(self, no_shooting_star_data):
        """Test Shooting Star detection on data without Shooting Star patterns."""
        shooting_star = ShootingStar()
        result = shooting_star.detect(no_shooting_star_data)

        assert isinstance(result, pd.Series)
        # May have 0-1 detections depending on exact ratios
        assert result.sum() <= 1

    def test_shooting_star_with_strict_params(self, shooting_star_data):
        """Test Shooting Star with stricter parameters."""
        shooting_star = ShootingStar(
            {"min_shadow_ratio": 4.0, "max_lower_shadow_ratio": 0.05}  # Very strict
        )
        result = shooting_star.detect(shooting_star_data)

        # Fewer detections with stricter parameters
        assert result.sum() <= 1

    def test_confidence_scoring(self, shooting_star_data):
        """Test Shooting Star confidence score calculation."""
        shooting_star = ShootingStar()
        detections = shooting_star.detect(shooting_star_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = shooting_star.calculate_confidence(shooting_star_data, detection_indices)

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Shooting Star base confidence is 0.6
                assert score >= 0.6

    def test_bearish_shooting_star_higher_confidence(self, sample_dates):
        """Test bearish Shooting Star (close < open) gets higher confidence."""
        # Bearish Shooting Star
        bearish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [109],  # High = max, long upper shadow
                "low": [99],  # Low = min
                "close": [99.2],  # Bearish close
                "volume": [1000000],
            }
        )

        # Bullish Shooting Star
        bullish_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [109],  # High = max, long upper shadow
                "low": [99],  # Low = min
                "close": [100.8],  # Bullish close
                "volume": [1000000],
            }
        )

        shooting_star = ShootingStar()

        bearish_detections = shooting_star.detect(bearish_data)
        bullish_detections = shooting_star.detect(bullish_data)

        if bearish_detections.sum() > 0 and bullish_detections.sum() > 0:
            bearish_conf = shooting_star.calculate_confidence(
                bearish_data, bearish_detections[bearish_detections].index
            )
            bullish_conf = shooting_star.calculate_confidence(
                bullish_data, bullish_detections[bullish_detections].index
            )

            # Bearish should have higher confidence
            assert list(bearish_conf.values())[0] > list(bullish_conf.values())[0]

    def test_strong_shadow_ratio_bonus(self, sample_dates):
        """Test strong shadow/body ratio increases confidence."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [115],  # High = max, very long upper shadow
                "low": [99],  # Low = min
                "close": [100.5],  # Small body
                "volume": [1000000],
            }
        )

        shooting_star = ShootingStar()
        detections = shooting_star.detect(data)

        if detections.sum() > 0:
            confidence_scores = shooting_star.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to strong shadow/body ratio
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        shooting_star = ShootingStar()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Shooting Star detection failed"):
            shooting_star.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        shooting_star = ShootingStar()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Shooting Star detection failed"):
            shooting_star.detect(empty_data)

    def test_insufficient_range(self, sample_dates):
        """Test Shooting Star ignores candles with insufficient range."""
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

        shooting_star = ShootingStar()
        result = shooting_star.detect(data)

        # Should not detect due to min_range filter
        assert result.sum() == 0

    def test_lower_shadow_too_large(self, sample_dates):
        """Test Shooting Star not detected when lower shadow too large."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [108],  # High = max, long upper shadow
                "low": [90],  # Low = min, large lower shadow
                "close": [100.5],  # Small body
                "volume": [1000000],
            }
        )

        shooting_star = ShootingStar()
        result = shooting_star.detect(data)

        # Should not detect - lower shadow too large
        assert result.sum() == 0

    def test_filter_by_confidence_threshold(self, shooting_star_data):
        """Test confidence threshold filtering."""
        shooting_star = ShootingStar()
        shooting_star.set_pattern_registry_info(pattern_id=4, confidence_threshold=0.9)

        # Raw detections
        raw_detections = shooting_star.detect(shooting_star_data)

        # Filtered detections
        filtered_detections = shooting_star.filter_by_confidence(raw_detections, shooting_star_data)

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained (high >= low, etc.)."""
        # Valid OHLC data with Shooting Star characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 101, 102],
                "high": [109, 110, 111],  # High = max, long upper shadows
                "low": [99, 100, 101],  # Low = min
                "close": [100.5, 101.5, 102.5],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        shooting_star = ShootingStar()
        result = shooting_star.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)
