"""
Dynamic pattern loader for TickStockAppV2.

Sprint 68: Core Analysis Migration - Pattern loading with NO FALLBACK policy
Sprint 74: Table-driven dynamic loading from database
"""

import importlib
from typing import Type, Dict, Any, Optional

from .base_pattern import BasePattern
from ..exceptions import PatternLoadError
from ..dynamic_loader import get_dynamic_loader


def load_pattern(pattern_name: str, timeframe: str = 'daily') -> BasePattern:
    """
    Dynamically load pattern instance by name using database configuration.

    Sprint 74: Table-driven loading from pattern_definitions table.
    NO FALLBACK POLICY: If pattern not found, raise error immediately.

    Args:
        pattern_name: Pattern name (e.g., 'doji', 'hammer', 'engulfing')
        timeframe: Timeframe to load pattern for (default: 'daily')

    Returns:
        Pattern instance (ready to call detect())

    Raises:
        PatternLoadError: If pattern cannot be loaded

    Examples:
        >>> doji = load_pattern('doji')
        >>> result = doji.detect(data)
    """
    try:
        # Get dynamic loader
        loader = get_dynamic_loader()

        # Get pattern metadata from database
        pattern_meta = loader.get_pattern(timeframe, pattern_name)

        if not pattern_meta:
            raise PatternLoadError(
                f"Pattern '{pattern_name}' not found for timeframe '{timeframe}'. "
                f"Ensure pattern is enabled in pattern_definitions table."
            )

        # Return the pattern instance
        return pattern_meta['instance']

    except PatternLoadError:
        # Re-raise pattern load errors as-is
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise PatternLoadError(
            f"Unexpected error loading pattern '{pattern_name}': {e}"
        ) from e


def get_available_patterns(timeframe: str = 'daily') -> dict[str, list[str]]:
    """
    Get list of all enabled patterns organized by category.

    Sprint 74: Queries pattern_definitions table for enabled patterns.

    Args:
        timeframe: Timeframe to get patterns for (default: 'daily')

    Returns:
        Dictionary mapping pattern category to list of pattern names

    Examples:
        >>> patterns = get_available_patterns('daily')
        >>> patterns['candlestick']
        ['doji', 'hammer', 'engulfing', 'shooting_star', 'hanging_man', 'harami', 'morning_star', 'evening_star']
    """
    # Get dynamic loader
    loader = get_dynamic_loader()

    # Load patterns for this timeframe
    patterns = loader.load_patterns_for_timeframe(timeframe)

    # Group by category
    result: Dict[str, list[str]] = {}
    for name, meta in patterns.items():
        category = meta.get('category', 'other')
        if category not in result:
            result[category] = []
        result[category].append(name)

    # Sort each category
    for category in result:
        result[category] = sorted(result[category])

    return result


def is_pattern_available(pattern_name: str, timeframe: str = 'daily') -> bool:
    """
    Check if pattern is available for loading.

    Sprint 74: Checks pattern_definitions table for enabled patterns.

    Args:
        pattern_name: Pattern name to check
        timeframe: Timeframe to check (default: 'daily')

    Returns:
        True if pattern is enabled in database, False otherwise

    Examples:
        >>> is_pattern_available('doji')
        True
        >>> is_pattern_available('unknown_pattern')
        False
    """
    try:
        loader = get_dynamic_loader()
        pattern_meta = loader.get_pattern(timeframe, pattern_name.lower())
        return pattern_meta is not None
    except Exception:
        return False
