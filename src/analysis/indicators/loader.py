"""
Dynamic indicator loader for TickStockAppV2.

Sprint 68: Core Analysis Migration - Indicator loading with NO FALLBACK policy
"""

import importlib
from typing import Type

from .base_indicator import BaseIndicator
from ..exceptions import IndicatorLoadError


# Indicator registry - all available indicators
# Sprint 68: SMA, RSI, MACD
# Sprint 70: EMA, ATR, Bollinger Bands, Stochastic, ADX
AVAILABLE_INDICATORS = {
    # Trend Indicators
    "sma",
    "ema",
    "macd",
    # Momentum Indicators
    "rsi",
    "stochastic",
    # Volatility Indicators
    "bollinger_bands",
    "atr",
    # Directional Indicators
    "adx",
}


def load_indicator(indicator_name: str) -> Type[BaseIndicator]:
    """
    Dynamically load indicator class by name.

    NO FALLBACK POLICY: If indicator not found, raise error immediately.
    This ensures we catch configuration errors early rather than silently
    using incorrect or stub implementations.

    Args:
        indicator_name: Indicator name (e.g., 'SMA', 'RSI', 'MACD')

    Returns:
        Indicator class (not instance)

    Raises:
        IndicatorLoadError: If indicator cannot be loaded

    Examples:
        >>> sma_class = load_indicator('SMA')
        >>> sma = sma_class({'period': 20})
        >>> result = sma.calculate(data)
    """
    try:
        # Normalize indicator name to lowercase for module lookup
        indicator_module_name = indicator_name.lower()

        # Check if indicator is registered
        if indicator_module_name not in AVAILABLE_INDICATORS:
            raise IndicatorLoadError(
                f"Unknown indicator: '{indicator_name}'. "
                f"Indicator must be registered in AVAILABLE_INDICATORS. "
                f"Available indicators: {sorted(AVAILABLE_INDICATORS)}",
                module_name=indicator_module_name,
            )

        # Construct module path
        module_path = f"src.analysis.indicators.{indicator_module_name}"

        # Import module
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise IndicatorLoadError(
                f"Indicator module not found: '{indicator_name}' "
                f"(searched: {module_path}). "
                f"Ensure indicator is registered in indicator_definitions table "
                f"and implementation exists.",
                module_name=module_path,
            ) from e

        # Get class (convert indicator_name to ClassName convention)
        class_name = _to_class_name(indicator_name)

        try:
            indicator_class = getattr(module, class_name)
        except AttributeError as e:
            raise IndicatorLoadError(
                f"Indicator class '{class_name}' not found in module '{module_path}'. "
                f"Ensure class name matches indicator name convention.",
                module_name=module_path,
                class_name=class_name,
            ) from e

        # Validate it's a BaseIndicator subclass
        if not issubclass(indicator_class, BaseIndicator):
            raise IndicatorLoadError(
                f"Indicator '{class_name}' must inherit from BaseIndicator. "
                f"Found: {indicator_class.__bases__}",
                class_name=class_name,
            )

        return indicator_class

    except IndicatorLoadError:
        # Re-raise indicator load errors as-is
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise IndicatorLoadError(
            f"Unexpected error loading indicator '{indicator_name}': {e}",
            module_name=indicator_name,
        ) from e


def _to_class_name(indicator_name: str) -> str:
    """
    Convert indicator_name to ClassName convention.

    Examples:
        sma -> SMA
        macd -> MACD
        bollinger_bands -> BollingerBands
        williams_r -> WilliamsR

    Args:
        indicator_name: Indicator name (may be lowercase or mixed case)

    Returns:
        Class name in appropriate format
    """
    # Handle special cases (acronyms that should stay uppercase)
    upper_indicators = {"sma", "ema", "rsi", "macd", "atr", "obv", "vwap", "adx", "roc"}
    indicator_lower = indicator_name.lower()

    if indicator_lower in upper_indicators:
        return indicator_lower.upper()

    # For others, capitalize words
    words = indicator_name.lower().split("_")
    return "".join(word.capitalize() for word in words)


def get_available_indicators() -> dict[str, list[str]]:
    """
    Get list of all available indicators organized by category.

    Sprint 68: SMA, RSI, MACD
    Sprint 70: EMA, ATR, Bollinger Bands, Stochastic, ADX

    Returns:
        Dictionary mapping indicator category to list of indicator names

    Examples:
        >>> indicators = get_available_indicators()
        >>> indicators['trend']
        ['sma', 'ema', 'macd']
    """
    return {
        "trend": ["sma", "ema", "macd"],
        "momentum": ["rsi", "stochastic"],
        "volatility": ["bollinger_bands", "atr"],
        "directional": ["adx"],
    }


def is_indicator_available(indicator_name: str) -> bool:
    """
    Check if indicator is available for loading.

    Args:
        indicator_name: Indicator name to check

    Returns:
        True if indicator is registered, False otherwise

    Examples:
        >>> is_indicator_available('SMA')
        True
        >>> is_indicator_available('UnknownIndicator')
        False
    """
    return indicator_name.lower() in AVAILABLE_INDICATORS


def get_indicator_category(indicator_name: str) -> str | None:
    """
    Get category for a specific indicator.

    Args:
        indicator_name: Indicator name

    Returns:
        Category name or None if not found

    Examples:
        >>> get_indicator_category('SMA')
        'trend'
        >>> get_indicator_category('RSI')
        'momentum'
    """
    categories = get_available_indicators()
    indicator_lower = indicator_name.lower()

    for category, indicators in categories.items():
        if indicator_lower in indicators:
            return category

    return None


class IndicatorLoader:
    """
    Class-based indicator loader for dependency injection and API usage.

    Sprint 71: REST API Endpoints
    Provides class-based interface to indicator loading functions for easier
    integration with services and mocking in tests.
    """

    def __init__(self):
        """Initialize indicator loader with caching."""
        self._indicator_cache: dict[str, Type[BaseIndicator]] = {}

    def get_indicator(self, indicator_name: str) -> BaseIndicator:
        """
        Load and instantiate an indicator by name.

        Args:
            indicator_name: Indicator name (e.g., 'SMA', 'RSI')

        Returns:
            Indicator instance (ready to call calculate())

        Raises:
            IndicatorLoadError: If indicator cannot be loaded
        """
        # Check cache first
        indicator_key = indicator_name.lower()
        if indicator_key not in self._indicator_cache:
            # Load and cache the class
            self._indicator_cache[indicator_key] = load_indicator(indicator_name)

        # Return instance of the cached class
        indicator_class = self._indicator_cache[indicator_key]
        return indicator_class()

    def get_available_indicators(self) -> dict[str, dict[str, str]]:
        """
        Get all available indicators with metadata.

        Returns:
            Dictionary mapping indicator names to metadata:
            {
                'sma': {'category': 'trend', 'name': 'Simple Moving Average'},
                'rsi': {'category': 'momentum', 'name': 'Relative Strength Index'},
                ...
            }
        """
        result = {}
        categories = get_available_indicators()

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
        return is_indicator_available(indicator_name)

    def get_category(self, indicator_name: str) -> str | None:
        """
        Get category for a specific indicator.

        Args:
            indicator_name: Indicator name

        Returns:
            Category name or None if not found
        """
        return get_indicator_category(indicator_name)

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
