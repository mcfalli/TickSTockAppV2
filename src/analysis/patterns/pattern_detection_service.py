"""
Pattern Detection Service for TickStockAppV2.

Sprint 71: REST API Endpoints
Class-based service for pattern detection with caching and API integration.
"""

from typing import Any

import pandas as pd

from .loader import load_pattern, get_available_patterns, is_pattern_available
from .base_pattern import BasePattern
from ..exceptions import InvalidPatternError, PatternDetectionError


class PatternDetectionService:
    """
    Service for pattern detection across all pattern types.

    Sprint 71: REST API Endpoints
    Provides class-based interface to pattern detection for easier integration
    with services and mocking in tests.
    """

    def __init__(self):
        """Initialize pattern detection service with caching."""
        self._pattern_cache: dict[str, BasePattern] = {}

    def detect_pattern(
        self,
        pattern_name: str,
        data: pd.DataFrame,
        timeframe: str = "daily",
    ) -> dict[str, pd.Series]:
        """
        Detect a specific pattern in price data.

        Args:
            pattern_name: Name of pattern to detect (e.g., 'doji', 'hammer')
            data: OHLCV DataFrame
            timeframe: Timeframe for analysis

        Returns:
            Dictionary with detection results:
            {
                'detected': pd.Series[bool],  # True where pattern detected
                'confidence': pd.Series[float],  # Confidence scores (0.0-1.0)
            }

        Raises:
            InvalidPatternError: If pattern doesn't exist
            PatternDetectionError: If detection fails
        """
        # Check if pattern exists
        if not is_pattern_available(pattern_name):
            available = self.get_available_patterns()
            all_patterns = []
            for patterns_list in available.values():
                all_patterns.extend(patterns_list)

            raise InvalidPatternError(
                f"Pattern '{pattern_name}' not found. "
                f"Available patterns: {', '.join(sorted(all_patterns))}",
                pattern_name=pattern_name,
                available_patterns=all_patterns,
            )

        try:
            # Get pattern instance (cached)
            pattern = self._get_pattern_instance(pattern_name)

            # Detect pattern (patterns work on any timeframe data)
            detected_series = pattern.detect(data)

            # Wrap result in expected dict format
            # Patterns return pd.Series[bool], we need {'detected': Series, 'confidence': Series}
            import pandas as pd
            result = {
                'detected': detected_series,
                'confidence': pd.Series(1.0, index=detected_series.index)  # Default confidence
            }

            return result

        except InvalidPatternError:
            raise

        except Exception as e:
            raise PatternDetectionError(
                f"Pattern detection failed for '{pattern_name}': {str(e)}",
                pattern_name=pattern_name,
                symbol=None,
                timeframe=timeframe,
                data_info=f"{len(data)} rows",
            ) from e

    def get_available_patterns(self) -> dict[str, list[str]]:
        """
        Get all available patterns organized by type.

        Returns:
            Dictionary mapping pattern type to list of pattern names:
            {
                'candlestick': ['doji', 'hammer', 'engulfing', ...],
                'daily': ['head_shoulders', 'double_top', ...],
                'combo': ['breakout_volume', 'macd_divergence', ...]
            }
        """
        return get_available_patterns()

    def is_available(self, pattern_name: str) -> bool:
        """
        Check if pattern is available.

        Args:
            pattern_name: Pattern name

        Returns:
            True if available, False otherwise
        """
        return is_pattern_available(pattern_name)

    def _get_pattern_instance(self, pattern_name: str) -> BasePattern:
        """
        Get or create cached pattern instance.

        Args:
            pattern_name: Pattern name

        Returns:
            Pattern instance

        Raises:
            PatternLoadError: If pattern cannot be loaded
        """
        pattern_key = pattern_name.lower()

        if pattern_key not in self._pattern_cache:
            # Load pattern class
            pattern_class = load_pattern(pattern_name)

            # Instantiate and cache
            self._pattern_cache[pattern_key] = pattern_class()

        return self._pattern_cache[pattern_key]
