"""
Unit tests for pattern dynamic loader.

Sprint 68: Core Analysis Migration - Loader tests
"""

import pytest

from src.analysis.patterns.loader import (
    load_pattern,
    is_pattern_available,
    get_available_patterns,
    _determine_pattern_type,
    _to_class_name,
)
from src.analysis.patterns.base_pattern import BasePattern
from src.analysis.exceptions import PatternLoadError


class TestLoadPattern:
    """Test pattern dynamic loading."""

    def test_load_doji_pattern(self):
        """Test loading Doji pattern."""
        pattern_class = load_pattern("Doji")

        assert pattern_class is not None
        assert issubclass(pattern_class, BasePattern)
        assert pattern_class.__name__ == "Doji"

    def test_load_hammer_pattern(self):
        """Test loading Hammer pattern."""
        pattern_class = load_pattern("Hammer")

        assert pattern_class is not None
        assert issubclass(pattern_class, BasePattern)
        assert pattern_class.__name__ == "Hammer"

    def test_load_engulfing_pattern(self):
        """Test loading Engulfing pattern."""
        pattern_class = load_pattern("Engulfing")

        assert pattern_class is not None
        assert issubclass(pattern_class, BasePattern)
        assert pattern_class.__name__ == "Engulfing"

    def test_load_pattern_case_insensitive(self):
        """Test pattern loading is case-insensitive."""
        # All these should work
        doji1 = load_pattern("Doji")
        doji2 = load_pattern("doji")
        doji3 = load_pattern("DOJI")

        assert doji1 is doji2 is doji3

    def test_load_pattern_creates_instance(self):
        """Test loaded pattern can be instantiated."""
        pattern_class = load_pattern("Doji")
        pattern = pattern_class()

        assert isinstance(pattern, BasePattern)
        assert pattern.pattern_name == "Doji"

    def test_load_nonexistent_pattern(self):
        """Test loading nonexistent pattern raises PatternLoadError."""
        with pytest.raises(PatternLoadError, match="Unknown pattern type"):
            load_pattern("NonExistentPattern")

    def test_load_unknown_pattern_type(self):
        """Test loading pattern with unknown type raises PatternLoadError."""
        # Pattern not in any registry
        with pytest.raises(PatternLoadError, match="Unknown pattern type"):
            load_pattern("UnknownTypePattern")

    def test_no_fallback_policy(self):
        """Test NO FALLBACK policy - errors not silently ignored."""
        # Should raise immediately, not fall back to stub/default
        with pytest.raises(PatternLoadError):
            load_pattern("InvalidPattern")


class TestDeterminePatternType:
    """Test pattern type determination."""

    def test_candlestick_pattern_type(self):
        """Test candlestick pattern type detection."""
        assert _determine_pattern_type("doji") == "candlestick"
        assert _determine_pattern_type("hammer") == "candlestick"
        assert _determine_pattern_type("engulfing") == "candlestick"

    def test_daily_pattern_type(self):
        """Test daily pattern type detection."""
        assert _determine_pattern_type("head_shoulders") == "daily"
        assert _determine_pattern_type("double_top") == "daily"

    def test_combo_pattern_type(self):
        """Test combo pattern type detection."""
        assert _determine_pattern_type("macd_divergence") == "combo"
        assert _determine_pattern_type("rsi_reversal") == "combo"

    def test_unknown_pattern_type_raises_error(self):
        """Test unknown pattern type raises error."""
        with pytest.raises(PatternLoadError, match="Unknown pattern type"):
            _determine_pattern_type("unknown_pattern")


class TestToClassName:
    """Test class name conversion."""

    def test_simple_name_conversion(self):
        """Test simple pattern name conversion."""
        assert _to_class_name("doji") == "Doji"
        assert _to_class_name("Doji") == "Doji"
        assert _to_class_name("DOJI") == "Doji"

    def test_underscore_name_conversion(self):
        """Test underscore pattern name conversion."""
        assert _to_class_name("head_shoulders") == "HeadShoulders"
        assert _to_class_name("macd_divergence") == "MacdDivergence"
        assert _to_class_name("double_top") == "DoubleTop"

    def test_mixed_case_conversion(self):
        """Test mixed case conversion."""
        assert _to_class_name("Rsi_Reversal") == "RsiReversal"
        assert _to_class_name("Volume_Surge_Pattern") == "VolumeSurgePattern"


class TestIsPatternAvailable:
    """Test pattern availability checking."""

    def test_available_candlestick_patterns(self):
        """Test candlestick patterns are available."""
        assert is_pattern_available("Doji") is True
        assert is_pattern_available("Hammer") is True
        assert is_pattern_available("Engulfing") is True

    def test_available_patterns_case_insensitive(self):
        """Test availability check is case-insensitive."""
        assert is_pattern_available("doji") is True
        assert is_pattern_available("HAMMER") is True
        assert is_pattern_available("Engulfing") is True

    def test_unavailable_pattern(self):
        """Test unavailable pattern returns False."""
        assert is_pattern_available("NonExistentPattern") is False
        assert is_pattern_available("InvalidPattern") is False


class TestGetAvailablePatterns:
    """Test getting available patterns list."""

    def test_get_available_patterns_structure(self):
        """Test available patterns returns correct structure."""
        patterns = get_available_patterns()

        assert isinstance(patterns, dict)
        assert "candlestick" in patterns
        assert "daily" in patterns
        assert "combo" in patterns

    def test_candlestick_patterns_included(self):
        """Test candlestick patterns are included."""
        patterns = get_available_patterns()

        candlestick = patterns["candlestick"]
        assert "doji" in candlestick
        assert "hammer" in candlestick
        assert "engulfing" in candlestick

    def test_patterns_are_sorted(self):
        """Test patterns are returned sorted."""
        patterns = get_available_patterns()

        for pattern_type, pattern_list in patterns.items():
            assert pattern_list == sorted(pattern_list)

    def test_patterns_are_lowercase(self):
        """Test pattern names are lowercase."""
        patterns = get_available_patterns()

        for pattern_type, pattern_list in patterns.items():
            for pattern_name in pattern_list:
                assert pattern_name.islower()


class TestLoaderIntegration:
    """Test loader integration scenarios."""

    def test_load_and_execute_pattern(self):
        """Test loading pattern and executing detection."""
        import pandas as pd
        from datetime import datetime

        # Load pattern
        doji_class = load_pattern("Doji")
        doji = doji_class()

        # Create test data
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        data = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100, 101, 102, 103, 104],
                "high": [102, 103, 104, 105, 106],
                "low": [98, 99, 100, 101, 102],
                "close": [100.1, 101.1, 102.1, 103, 104],  # Last bar is doji
                "volume": [1000000] * 5,
            }
        )

        # Execute detection
        result = doji.detect(data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(data)

    def test_load_multiple_patterns(self):
        """Test loading multiple patterns."""
        patterns = ["Doji", "Hammer", "Engulfing"]

        loaded_patterns = {}
        for pattern_name in patterns:
            pattern_class = load_pattern(pattern_name)
            loaded_patterns[pattern_name] = pattern_class

        assert len(loaded_patterns) == 3
        assert all(issubclass(p, BasePattern) for p in loaded_patterns.values())

    def test_pattern_class_caching(self):
        """Test loading same pattern twice returns same class."""
        doji1 = load_pattern("Doji")
        doji2 = load_pattern("Doji")

        # Should be same class object
        assert doji1 is doji2
