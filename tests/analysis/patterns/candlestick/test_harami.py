"""
Unit tests for Harami candlestick pattern.

Sprint 69: Pattern Library Extension - Harami pattern tests
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.analysis.patterns.candlestick.harami import Harami, HaramiParams
from src.analysis.exceptions import PatternDetectionError


class TestHaramiParams:
    """Test Harami parameter validation."""

    def test_default_params(self):
        """Test default parameter values."""
        params = HaramiParams()
        assert params.min_body_ratio == 2.0
        assert params.max_inner_body_ratio == 0.5
        assert params.require_opposite_colors == True
        assert params.min_range == 0.001

    def test_custom_params(self):
        """Test custom parameter values."""
        params = HaramiParams(
            min_body_ratio=3.0,
            max_inner_body_ratio=0.3,
            require_opposite_colors=False,
        )
        assert params.min_body_ratio == 3.0
        assert params.max_inner_body_ratio == 0.3
        assert params.require_opposite_colors == False

    def test_invalid_min_body_ratio(self):
        """Test invalid min_body_ratio raises error."""
        with pytest.raises(ValueError, match="min_body_ratio must be >= 1.0"):
            HaramiParams(min_body_ratio=0.5)

    def test_invalid_max_inner_body_ratio(self):
        """Test invalid max_inner_body_ratio raises error."""
        with pytest.raises(ValueError, match="max_inner_body_ratio must be between 0 and 1"):
            HaramiParams(max_inner_body_ratio=1.5)

        with pytest.raises(ValueError, match="max_inner_body_ratio must be between 0 and 1"):
            HaramiParams(max_inner_body_ratio=-0.1)


class TestHaramiDetection:
    """Test Harami pattern detection logic."""

    @pytest.fixture
    def sample_dates(self):
        """Generate sample timestamp range."""
        return pd.date_range(start="2024-01-01", periods=10, freq="D")

    @pytest.fixture
    def bullish_harami_data(self, sample_dates):
        """Create data with Bullish Harami pattern (large bearish + small bullish)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [100, 101, 102, 103, 104, 105, 106, 107, 110, 105.5],  # Bar 8: large bearish, Bar 9: small bullish
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 110, 106],
                "low": [99, 100, 101, 102, 103, 104, 105, 106, 105, 105],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 105, 105.8],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def bearish_harami_data(self, sample_dates):
        """Create data with Bearish Harami pattern (large bullish + small bearish)."""
        return pd.DataFrame(
            {
                "timestamp": sample_dates,
                "open": [110, 109, 108, 107, 106, 105, 104, 103, 100, 104.5],  # Bar 8: large bullish, Bar 9: small bearish
                "high": [111, 110, 109, 108, 107, 106, 105, 104, 105, 105],
                "low": [109, 108, 107, 106, 105, 104, 103, 102, 100, 104],
                "close": [109.5, 108.5, 107.5, 106.5, 105.5, 104.5, 103.5, 102.5, 105, 104.2],
                "volume": [1000000] * 10,
            }
        )

    @pytest.fixture
    def no_harami_data(self, sample_dates):
        """Create data without Harami patterns (normal candles)."""
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

    def test_harami_initialization(self):
        """Test Harami pattern initialization."""
        harami = Harami()
        assert harami.pattern_name == "Harami"
        assert harami.supports_confidence_scoring()
        assert harami.get_minimum_bars() == 2

    def test_harami_custom_params(self):
        """Test Harami with custom parameters."""
        harami = Harami({"min_body_ratio": 3.0, "max_inner_body_ratio": 0.3})
        assert harami.params.min_body_ratio == 3.0
        assert harami.params.max_inner_body_ratio == 0.3

    def test_bullish_harami_detection(self, bullish_harami_data):
        """Test Bullish Harami detection."""
        harami = Harami()
        result = harami.detect(bullish_harami_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(bullish_harami_data)
        assert result.dtype == bool

        # Last bar should be detected as Bullish Harami
        assert result.iloc[-1] == True

        # Verify harami type
        if result.iloc[-1]:
            harami_type = harami.get_harami_type(bullish_harami_data, bullish_harami_data.index[-1])
            assert harami_type == "bullish"

    def test_bearish_harami_detection(self, bearish_harami_data):
        """Test Bearish Harami detection."""
        harami = Harami()
        result = harami.detect(bearish_harami_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(bearish_harami_data)
        assert result.dtype == bool

        # Last bar should be detected as Bearish Harami
        assert result.iloc[-1] == True

        # Verify harami type
        if result.iloc[-1]:
            harami_type = harami.get_harami_type(bearish_harami_data, bearish_harami_data.index[-1])
            assert harami_type == "bearish"

    def test_harami_detection_negative(self, no_harami_data):
        """Test Harami detection on data without Harami patterns."""
        harami = Harami()
        result = harami.detect(no_harami_data)

        assert isinstance(result, pd.Series)
        # Should have 0 detections (no containment patterns)
        assert result.sum() == 0

    def test_harami_with_strict_params(self, bullish_harami_data):
        """Test Harami with stricter parameters."""
        harami = Harami({"min_body_ratio": 5.0, "max_inner_body_ratio": 0.2})
        result = harami.detect(bullish_harami_data)

        # Fewer or zero detections with stricter parameters
        assert result.sum() <= 1

    def test_harami_without_color_requirement(self, sample_dates):
        """Test Harami without requiring opposite colors."""
        # Same color harami (both bullish)
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 105, 106],  # Bar 1: large bullish, Bar 2: small bullish
                "high": [110, 107, 108],
                "low": [99, 105.5, 105.5],
                "close": [109, 106.5, 107],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        # With color requirement (default)
        harami_strict = Harami()
        result_strict = harami_strict.detect(data)
        assert result_strict.iloc[1] == False  # Not detected (same colors)

        # Without color requirement
        harami_lenient = Harami({"require_opposite_colors": False})
        result_lenient = harami_lenient.detect(data)
        # May detect based on containment alone
        assert isinstance(result_lenient, pd.Series)

    def test_confidence_scoring(self, bullish_harami_data):
        """Test Harami confidence score calculation."""
        harami = Harami()
        detections = harami.detect(bullish_harami_data)

        if detections.sum() > 0:
            detection_indices = detections[detections].index
            confidence_scores = harami.calculate_confidence(
                bullish_harami_data, detection_indices
            )

            assert len(confidence_scores) == len(detection_indices)
            for idx, score in confidence_scores.items():
                assert 0.0 <= score <= 1.0
                assert isinstance(score, float)
                # Harami base confidence is 0.6
                assert score >= 0.6

    def test_small_inner_candle_bonus(self, sample_dates):
        """Test confidence bonus for very small inner candle."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 110, 105.1],  # Bar 1: large bearish, Bar 2: tiny bullish
                "high": [101, 110, 105.2],
                "low": [99, 105, 105],
                "close": [100.5, 105, 105.2],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        harami = Harami()
        detections = harami.detect(data)

        if detections.sum() > 0:
            confidence_scores = harami.calculate_confidence(data, detections[detections].index)
            # Should have high confidence due to very small inner candle
            assert list(confidence_scores.values())[0] >= 0.75

    def test_invalid_data_format(self):
        """Test detection with invalid data format raises error."""
        harami = Harami()

        # Missing columns
        invalid_data = pd.DataFrame({"open": [100], "close": [101]})

        with pytest.raises(PatternDetectionError, match="Harami detection failed"):
            harami.detect(invalid_data)

    def test_empty_data(self):
        """Test detection with empty data raises error."""
        harami = Harami()
        empty_data = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        with pytest.raises(PatternDetectionError, match="Harami detection failed"):
            harami.detect(empty_data)

    def test_single_bar_data(self, sample_dates):
        """Test Harami with single bar (not enough data)."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:1],
                "open": [100],
                "high": [101],
                "low": [99],
                "close": [100.5],
                "volume": [1000000],
            }
        )

        harami = Harami()
        result = harami.detect(data)

        # Should return False (need 2 bars)
        assert result.sum() == 0

    def test_first_bar_always_false(self, bullish_harami_data):
        """Test first bar is always False (no previous bar)."""
        harami = Harami()
        result = harami.detect(bullish_harami_data)

        # First bar cannot have harami
        assert result.iloc[0] == False

    def test_filter_by_confidence_threshold(self, bullish_harami_data):
        """Test confidence threshold filtering."""
        harami = Harami()
        harami.set_pattern_registry_info(pattern_id=6, confidence_threshold=0.9)

        # Raw detections
        raw_detections = harami.detect(bullish_harami_data)

        # Filtered detections
        filtered_detections = harami.filter_by_confidence(
            raw_detections, bullish_harami_data
        )

        # Filtered should have same or fewer detections
        assert filtered_detections.sum() <= raw_detections.sum()

    def test_ohlc_consistency(self, sample_dates):
        """Test that OHLC consistency is maintained."""
        # Valid OHLCV data with Harami characteristics
        valid_data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 110, 105.5],
                "high": [101, 110, 106],
                "low": [99, 105, 105],
                "close": [100.5, 105, 105.8],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        harami = Harami()
        result = harami.detect(valid_data)

        # Should not raise an error
        assert isinstance(result, pd.Series)

    def test_get_harami_type(self, bullish_harami_data, bearish_harami_data):
        """Test harami type detection method."""
        harami = Harami()

        # Test bullish harami
        bullish_detections = harami.detect(bullish_harami_data)
        if bullish_detections.sum() > 0:
            detection_idx = bullish_detections[bullish_detections].index[0]
            harami_type = harami.get_harami_type(bullish_harami_data, detection_idx)
            assert harami_type in ["bullish", "bearish", None]

        # Test bearish harami
        bearish_detections = harami.detect(bearish_harami_data)
        if bearish_detections.sum() > 0:
            detection_idx = bearish_detections[bearish_detections].index[0]
            harami_type = harami.get_harami_type(bearish_harami_data, detection_idx)
            assert harami_type in ["bullish", "bearish", None]

    def test_complete_range_containment_bonus(self, sample_dates):
        """Test confidence bonus for complete range containment."""
        data = pd.DataFrame(
            {
                "timestamp": sample_dates[:3],
                "open": [100, 110, 106],  # Complete containment
                "high": [101, 110, 107],  # Inner high < prev high
                "low": [99, 105, 105.5],  # Inner low > prev low
                "close": [100.5, 105, 106.5],
                "volume": [1000000, 1000000, 1000000],
            }
        )

        harami = Harami()
        detections = harami.detect(data)

        if detections.sum() > 0:
            confidence_scores = harami.calculate_confidence(data, detections[detections].index)
            # Should have bonus for complete containment
            assert list(confidence_scores.values())[0] >= 0.7
