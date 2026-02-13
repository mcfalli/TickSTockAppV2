"""
Dynamic indicator loader for TickStockAppV2.

Sprint 68: Core Analysis Migration - Indicator loading with NO FALLBACK policy
Sprint 74: Table-driven dynamic loading from database
"""

import importlib
from typing import Type, Dict, Any, Optional

from .base_indicator import BaseIndicator
from ..exceptions import IndicatorLoadError
from ..dynamic_loader import get_dynamic_loader


def load_indicator(indicator_name: str, timeframe: str = 'daily') -> BaseIndicator:
    """
    Dynamically load indicator instance by name using database configuration.

    Sprint 74: Table-driven loading from indicator_definitions table.
    NO FALLBACK POLICY: If indicator not found, raise error immediately.

    Args:
        indicator_name: Indicator name (e.g., 'sma', 'rsi', 'macd')
        timeframe: Timeframe to load indicator for (default: 'daily')

    Returns:
        Indicator instance (ready to call calculate())

    Raises:
        IndicatorLoadError: If indicator cannot be loaded

    Examples:
        >>> sma = load_indicator('sma')
        >>> result = sma.calculate(data)
    """
    try:
        # Get dynamic loader
        loader = get_dynamic_loader()

        # Get indicator metadata from database
        indicator_meta = loader.get_indicator(timeframe, indicator_name)

        if not indicator_meta:
            raise IndicatorLoadError(
                f"Indicator '{indicator_name}' not found for timeframe '{timeframe}'. "
                f"Ensure indicator is enabled in indicator_definitions table.",
                module_name=indicator_name,
            )

        # Return the indicator instance
        return indicator_meta['instance']

    except IndicatorLoadError:
        # Re-raise indicator load errors as-is
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise IndicatorLoadError(
            f"Unexpected error loading indicator '{indicator_name}': {e}",
            module_name=indicator_name,
        ) from e


def get_available_indicators(timeframe: str = 'daily') -> dict[str, list[str]]:
    """
    Get list of all enabled indicators organized by category.

    Sprint 74: Queries indicator_definitions table for enabled indicators.

    Args:
        timeframe: Timeframe to get indicators for (default: 'daily')

    Returns:
        Dictionary mapping indicator category to list of indicator names

    Examples:
        >>> indicators = get_available_indicators('daily')
        >>> indicators['trend']
        ['sma', 'ema', 'macd']
    """
    # Get dynamic loader
    loader = get_dynamic_loader()

    # Load indicators for this timeframe
    indicators = loader.load_indicators_for_timeframe(timeframe)

    # Group by category
    result: Dict[str, list[str]] = {}
    for name, meta in indicators.items():
        category = meta.get('category', 'other')
        if category not in result:
            result[category] = []
        result[category].append(name)

    # Sort each category
    for category in result:
        result[category] = sorted(result[category])

    return result


def is_indicator_available(indicator_name: str, timeframe: str = 'daily') -> bool:
    """
    Check if indicator is available for loading.

    Sprint 74: Checks indicator_definitions table for enabled indicators.

    Args:
        indicator_name: Indicator name to check
        timeframe: Timeframe to check (default: 'daily')

    Returns:
        True if indicator is enabled in database, False otherwise

    Examples:
        >>> is_indicator_available('sma')
        True
        >>> is_indicator_available('unknown_indicator')
        False
    """
    try:
        loader = get_dynamic_loader()
        indicator_meta = loader.get_indicator(timeframe, indicator_name.lower())
        return indicator_meta is not None
    except Exception:
        return False


def get_indicator_category(indicator_name: str, timeframe: str = 'daily') -> str | None:
    """
    Get category for a specific indicator.

    Sprint 74: Queries indicator_definitions table for category.

    Args:
        indicator_name: Indicator name
        timeframe: Timeframe (default: 'daily')

    Returns:
        Category name or None if not found

    Examples:
        >>> get_indicator_category('sma')
        'trend'
        >>> get_indicator_category('rsi')
        'momentum'
    """
    try:
        loader = get_dynamic_loader()
        indicator_meta = loader.get_indicator(timeframe, indicator_name.lower())
        return indicator_meta.get('category') if indicator_meta else None
    except Exception:
        return None


class IndicatorLoader:
    """
    Class-based indicator loader for dependency injection and API usage.

    Sprint 71: REST API Endpoints
    Sprint 74: Table-driven dynamic loading from database

    Provides class-based interface to indicator loading functions for easier
    integration with services and mocking in tests.
    """

    def __init__(self, timeframe: str = 'daily'):
        """
        Initialize indicator loader.

        Args:
            timeframe: Timeframe to load indicators for (default: 'daily')
        """
        self.timeframe = timeframe
        self._loader = get_dynamic_loader()

    def get_indicator(self, indicator_name: str) -> BaseIndicator:
        """
        Load and instantiate an indicator by name.

        Sprint 74: Uses database-driven dynamic loading.

        Args:
            indicator_name: Indicator name (e.g., 'sma', 'rsi')

        Returns:
            Indicator instance (ready to call calculate())

        Raises:
            IndicatorLoadError: If indicator cannot be loaded
        """
        return load_indicator(indicator_name, self.timeframe)

    def get_available_indicators(self) -> dict[str, dict[str, str]]:
        """
        Get all available indicators with metadata.

        Sprint 74: Queries indicator_definitions table.

        Returns:
            Dictionary mapping indicator names to metadata:
            {
                'sma': {'category': 'trend', 'name': 'Simple Moving Average'},
                'rsi': {'category': 'momentum', 'name': 'Relative Strength Index'},
                ...
            }
        """
        result = {}
        categories = get_available_indicators(self.timeframe)

        # Build flat dictionary with metadata
        for category, indicators in categories.items():
            for indicator_name in indicators:
                result[indicator_name] = {
                    'category': category,
                    'name': self._get_indicator_display_name(indicator_name),
                }

        return result

    def is_available(self, indicator_name: str) -> bool:
        """
        Check if indicator is available.

        Args:
            indicator_name: Indicator name

        Returns:
            True if available, False otherwise
        """
        return is_indicator_available(indicator_name, self.timeframe)

    def get_category(self, indicator_name: str) -> str | None:
        """
        Get category for a specific indicator.

        Args:
            indicator_name: Indicator name

        Returns:
            Category name or None if not found
        """
        return get_indicator_category(indicator_name, self.timeframe)

    def get_indicator_metadata(self, indicator_name: str) -> dict:
        """
        Get indicator with full metadata including min_bars_required.

        Sprint 74: Returns metadata from dynamic loader for validation.

        Args:
            indicator_name: Indicator name

        Returns:
            Indicator metadata dict with 'instance' and other fields

        Raises:
            IndicatorLoadError: If indicator cannot be loaded
        """
        loader = get_dynamic_loader()
        indicator_meta = loader.get_indicator(self.timeframe, indicator_name)

        if not indicator_meta:
            raise IndicatorLoadError(
                f"Indicator '{indicator_name}' not found for timeframe '{self.timeframe}'",
                module_name=indicator_name,
            )

        return indicator_meta

    def _get_indicator_display_name(self, indicator_name: str) -> str:
        """
        Convert indicator name to display name.

        Args:
            indicator_name: Indicator name

        Returns:
            Human-readable display name
        """
        # Map of indicator names to display names
        display_names = {
            'sma': 'Simple Moving Average',
            'ema': 'Exponential Moving Average',
            'macd': 'MACD',
            'rsi': 'Relative Strength Index',
            'stochastic': 'Stochastic Oscillator',
            'momentum': 'Momentum',
            'roc': 'Rate of Change',
            'williams_r': "Williams %R",
            'bollinger_bands': 'Bollinger Bands',
            'atr': 'Average True Range',
            'obv': 'On-Balance Volume',
            'volume_sma': 'Volume SMA',
            'relative_volume': 'Relative Volume',
            'vwap': 'Volume Weighted Average Price',
            'adx': 'Average Directional Index',
        }

        return display_names.get(indicator_name.lower(), indicator_name.title())
