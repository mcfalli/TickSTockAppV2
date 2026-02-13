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
            # Get pattern instance and metadata (cached)
            pattern_meta = self._get_pattern_metadata(pattern_name, timeframe)
            pattern = pattern_meta['instance']

            # Sprint 74: Validate min_bars_required
            min_bars = pattern_meta.get('min_bars_required', 1)
            if len(data) < min_bars:
                raise PatternDetectionError(
                    f"Insufficient data for pattern '{pattern_name}': "
                    f"have {len(data)} bars, need {min_bars}",
                    pattern_name=pattern_name,
                    symbol=None,
                    timeframe=timeframe,
                )

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

    def _get_pattern_metadata(self, pattern_name: str, timeframe: str = 'daily') -> dict:
        """
        Get or create cached pattern with full metadata.

        Sprint 74: Loads pattern from dynamic loader (database-driven).

        Args:
            pattern_name: Pattern name
            timeframe: Timeframe to load pattern for

        Returns:
            Pattern metadata dict with 'instance' and other fields

        Raises:
            PatternLoadError: If pattern cannot be loaded
        """
        # Cache key includes timeframe to support multi-timeframe patterns
        pattern_key = f"{pattern_name.lower()}_{timeframe}"

        if pattern_key not in self._pattern_cache:
            # Sprint 74: Get pattern metadata from dynamic loader
            from ..dynamic_loader import get_dynamic_loader
            loader = get_dynamic_loader()
            pattern_meta = loader.get_pattern(timeframe, pattern_name)

            if not pattern_meta:
                from ..exceptions import PatternLoadError
                raise PatternLoadError(
                    f"Pattern '{pattern_name}' not found for timeframe '{timeframe}'"
                )

            self._pattern_cache[pattern_key] = pattern_meta

        return self._pattern_cache[pattern_key]
