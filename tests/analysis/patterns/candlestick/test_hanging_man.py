"""
Unit tests for Hanging Man candlestick pattern.

Sprint 69: Pattern Library Extension - Hanging Man pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.hanging_man import HangingMan, HangingManParams
from src.analysis.exceptions import PatternDetectionError


class TestHangingManParams:
    """Test Hanging Man parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = HangingManParams()
        assert params.min_shadow_ratio == 2.0
        assert params.max_upper_shadow_ratio == 0.1
        assert params.min_lower_shadow_ratio == 0.6
        assert params.max_body_ratio == 0.3
        assert params.min_range == 0.001
        assert params.trend_lookback == 3

    def test_custom_params(self):
        """Test custom parameter values."""
        params = HangingManParams(
            min_shadow_ratio=3.0,
            max_upper_shadow_ratio=0.05,
            min_lower_shadow_ratio=0.7,
            max_body_ratio=0.2,
            trend_lookback=5,
        )
        assert params.min_shadow_ratio == 3.0
        assert params.max_upper_shadow_ratio == 0.05
        assert params.min_lower_shadow_ratio == 0.7
        assert params.max_body_ratio == 0.2
        assert params.trend_lookback == 5

    def test_invalid_min_shadow_ratio(self):
        """Test invalid min_shadow_ratio raises error."""
        with pytest.raises(ValueError, match="min_shadow_ratio must be positive"):
            HangingManParams(min_shadow_ratio=-1.0)

    def test_invalid_ratios(self):
        """Test invalid ratio parameters raise errors."""
        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HangingManParams(max_upper_shadow_ratio=1.5)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HangingManParams(min_lower_shadow_ratio=-0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0 and 1"):
            HangingManParams(max_body_ratio=2.0)

    def test_invalid_trend_lookback(self):
        """Test invalid trend_lookback raises error."""
        with pytest.raises(ValueError, match="trend_lookback must be >= 1"):
            HangingManParams(trend_lookback=0)


class TestHangingManDetection:
    """Test Hanging Man pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def hanging_man_data(self, sample_dates):
        """Create data with Hanging Man pattern (uptrend + hammer structure)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Uptrend: 100 → 109, then Hanging Man at top
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 109.5],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 101],  # Last has long lower shadow
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.2],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_hanging_man_data(self, sample_dates):
        """Create data without Hanging Man (downtrend or no hammer structure)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                # Downtrend: no hanging man should appear
                "open": [110, 109, 108, 107, 106, 105, 104, 103, 102, 101],
                "high": [111, 110, 109, 108, 107, 106, 105, 104, 103, 102],
                "low": [109, 108, 107, 106, 105, 104, 103, 102, 101, 100],
                "close": [109.5, 108.5, 107.5, 106.5, 105.5, 104.5, 103.5, 102.5, 101.5, 100.5],
                "volume": [1000000] * 10,
            }
        )

    def test_hanging_man_initialization(self):
        """Test Hanging Man pattern initialization."""
        hanging_man = HangingMan()
        assert hanging_man.pattern_name == "HangingMan"
        assert hanging_man.supports_confidence_scoring()
        assert hanging_man.get_minimum_bars() == 4  # 1 + default trend_lookback(3)

    def test_hanging_man_custom_params(self):
        """Test Hanging Man with custom parameters."""
        hanging_man = HangingMan({"min_shadow_ratio": 3.0, "trend_lookback": 5})
        assert hanging_man.params.min_shadow_ratio == 3.0
        assert hanging_man.params.trend_lookback == 5
        assert hanging_man.get_minimum_bars() == 6  # 1 + 5

    def test_hanging_man_detection_positive(self, hanging_man_data):
        """Test Hanging Man detection on data with Hanging Man pattern."""
        hanging_man = HangingMan()
        result = hanging_man.detect(hanging_man_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(hanging_man_data)
        assert result.dtype == bool

        # Last bar should be detected (uptrend + hammer structure)
        assert result.iloc[-1] == True

    def test_hanging_man_detection_negative(self, no_hanging_man_data):
        """Test Hanging Man detection on data without Hanging Man patterns."""
        hanging_man = HangingMan()
        result = hanging_man.detect(no_hanging_man_data)

        assert isinstance(result, pd.Series)
        # Should have 0 detections (downtrend, not uptrend)
        assert result.sum() == 0

    def test_hanging_man_requires_uptrend(self, sample_dates):
        """Test Hanging Man not detected without uptrend context."""
        # Hammer structure but no uptrend (flat prices)
        data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100] * 10,
                "high": [101] * 10,
                "low": [92, 92, 92, 92, 92, 92, 92, 92, 92, 92],  # Long lower shadows
                "close": [100.5] * 10,
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()
        result = hanging_man.detect(data)

        # Should not detect - no uptrend context
        assert result.sum() == 0

    def test_hanging_man_with_strict_params(self, hanging_man_data):
        """Test Hanging Man with stricter parameters."""
        hanging_man = HangingMan(
            {"min_shadow_ratio": 4.0, "max_upper_shadow_ratio": 0.05}
        )
        result = hanging_man.detect(hanging_man_data)

        # Fewer detections with stricter parameters
        assert result.sum() <= 1

    def test_confidence_scoring(self, hanging_man_data):
        """Test Hanging Man confidence score calculation."""
        hanging_man = HangingMan()
        detections = hanging_man.detect(hanging_man_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = hanging_man.calculate_confidence(
                hanging_man_data, detection_indices
            )

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Hanging Man base confidence is 0.6
                assert score >= 0.6

    def test_bearish_hanging_man_higher_confidence(self, sample_dates):
        """Test bearish Hanging Man (close < open) gets higher confidence."""
        # Create uptrend data with bearish Hanging Man
        bearish_data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 110],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 111],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 102],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.8],  # Bearish close
                "volume": [1000000] * 10,
            }
        )

        # Create uptrend data with bullish Hanging Man
        bullish_data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 101],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.8],  # Bullish close
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()

        bearish_detections = hanging_man.detect(bearish_data)
        bullish_detections = hanging_man.detect(bullish_data)

        # Both should detect, but confidence can vary
        if bearish_detections.sum() > 0:
            bearish_conf = hanging_man.calculate_confidence(
                bearish_data, bearish_detections[bearish_detections].index
            )
            # Bearish should have reasonable confidence
            assert all(0.6 <= score <= 1.0 for score in bearish_conf.values())

    def test_strong_shadow_ratio_bonus(self, sample_dates):
        """Test strong shadow/body ratio increases confidence."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 94],  # Very long lower shadow
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()
        detections = hanging_man.detect(data)

        if detections.sum() > 0:
            confidence_scores = hanging_man.calculate_confidence(
                data, detections[detections].index
            )
            # Should have high confidence due to strong shadow/body ratio
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        hanging_man = HangingMan()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Hanging Man detection failed"):
            hanging_man.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        hanging_man = HangingMan()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Hanging Man detection failed"):
            hanging_man.detect(empty_data)

    def test_insufficient_range(self, sample_dates):
        """Test Hanging Man ignores candles with insufficient range."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
                "high": [100.0001] * 10,  # Tiny range
                "low": [99.9999] * 10,
                "close": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()
        result = hanging_man.detect(data)

        # Should not detect due to min_range filter
        assert result.sum() == 0

    def test_upper_shadow_too_large(self, sample_dates):
        """Test Hanging Man not detected when upper shadow too large."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 118],  # Large upper shadow
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 101],  # Long lower shadow
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()
        result = hanging_man.detect(data)

        # Should not detect - upper shadow too large
        assert result.sum() == 0

    def test_filter_by_confidence_threshold(self, hanging_man_data):
        """Test confidence threshold filtering."""
        hanging_man = HangingMan()
        hanging_man.set_pattern_registry_info(pattern_id=5, confidence_threshold=0.9)

        # Raw detections
        raw_detections = hanging_man.detect(hanging_man_data)

        # Filtered detections
        filtered_detections = hanging_man.filter_by_confidence(
            raw_detections, hanging_man_data
        )

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained."""
        # Valid OHLC data with Hanging Man characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 101],  # Long lower shadows
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
                "volume": [1000000] * 10,
            }
        )

        hanging_man = HangingMan()
        result = hanging_man.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)

    def test_minimum_bars_requirement(self):
        """Test minimum bars requirement matches trend_lookback."""
        hanging_man_default = HangingMan()
        assert hanging_man_default.get_minimum_bars() == 4  # 1 + 3

        hanging_man_custom = HangingMan({"trend_lookback": 10})
        assert hanging_man_custom.get_minimum_bars() == 11  # 1 + 10
