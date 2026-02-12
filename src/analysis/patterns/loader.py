"""
Dynamic pattern loader for TickStockAppV2.

Sprint 68: Core Analysis Migration - Pattern loading with NO FALLBACK policy
"""

import importlib
from typing import Type

from .base_pattern import BasePattern
from ..exceptions import PatternLoadError


# Pattern type mappings (subdirectory organization)
# Sprint 68: Doji, Hammer, Engulfing
# Sprint 69: Shooting Star, Hanging Man, Harami, Morning Star, Evening Star
CANDLESTICK_PATTERNS = {
    "doji",
    "hammer",
    "engulfing",
    "shooting_star",
    "hanging_man",
    "harami",
    "morning_star",
    "evening_star",
}

# Future patterns - not yet implemented
DAILY_PATTERNS = set()

COMBO_PATTERNS = set()


def load_pattern(pattern_name: str) -> Type[BasePattern]:
    """
    Dynamically load pattern class by name.

    NO FALLBACK POLICY: If pattern not found, raise error immediately.
    This ensures we catch configuration errors early rather than silently
    using incorrect or stub implementations.

    Args:
        pattern_name: Pattern name (e.g., 'Doji', 'Hammer', 'Engulfing')

    Returns:
        Pattern class (not instance)

    Raises:
        PatternLoadError: If pattern cannot be loaded

    Examples:
        >>> doji_class = load_pattern('Doji')
        >>> doji = doji_class()
        >>> result = doji.detect(data)
    """
    try:
        # Normalize pattern name to lowercase for module lookup
        pattern_module_name = pattern_name.lower()

        # Determine pattern type (candlestick, daily, combo)
        pattern_type = _determine_pattern_type(pattern_module_name)

        # Construct module path
        module_path = f"src.analysis.patterns.{pattern_type}.{pattern_module_name}"

        # Import module
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise PatternLoadError(
                f"Pattern module not found: '{pattern_name}' "
                f"(searched: {module_path}). "
                f"Ensure pattern is registered in pattern_definitions table "
                f"and implementation exists."
            ) from e

        # Get class (convert pattern_name to ClassName convention)
        class_name = _to_class_name(pattern_name)

        try:
            pattern_class = getattr(module, class_name)
        except AttributeError as e:
            raise PatternLoadError(
                f"Pattern class '{class_name}' not found in module '{module_path}'. "
                f"Ensure class name matches pattern name convention."
            ) from e

        # Validate it's a BasePattern subclass
        if not issubclass(pattern_class, BasePattern):
            raise PatternLoadError(
                f"Pattern '{class_name}' must inherit from BasePattern. "
                f"Found: {pattern_class.__bases__}"
            )

        return pattern_class

    except PatternLoadError:
        # Re-raise pattern load errors as-is
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise PatternLoadError(
            f"Unexpected error loading pattern '{pattern_name}': {e}"
        ) from e


def _determine_pattern_type(pattern_name: str) -> str:
    """
    Determine pattern subdirectory based on pattern name.

    Args:
        pattern_name: Lowercase pattern name

    Returns:
        Pattern type: 'candlestick', 'daily', or 'combo'

    Raises:
        PatternLoadError: If pattern type cannot be determined
    """
    if pattern_name in CANDLESTICK_PATTERNS:
        return "candlestick"
    elif pattern_name in DAILY_PATTERNS:
        return "daily"
    elif pattern_name in COMBO_PATTERNS:
        return "combo"
    else:
        # Unknown pattern - provide helpful error
        raise PatternLoadError(
            f"Unknown pattern type for '{pattern_name}'. "
            f"Pattern must be registered in one of: "
            f"CANDLESTICK_PATTERNS, DAILY_PATTERNS, or COMBO_PATTERNS. "
            f"Add pattern to appropriate set in loader.py"
        )


def _to_class_name(pattern_name: str) -> str:
    """
    Convert pattern_name to ClassName convention.

    Examples:
        doji -> Doji
        head_shoulders -> HeadShoulders
        macd_divergence -> MacdDivergence

    Args:
        pattern_name: Pattern name (may be lowercase or mixed case)

    Returns:
        Class name in PascalCase
    """
    # Split on underscores and capitalize each word
    words = pattern_name.lower().split("_")
    return "".join(word.capitalize() for word in words)


def get_available_patterns() -> dict[str, list[str]]:
    """
    Get list of all available patterns organized by type.

    Returns:
        Dictionary mapping pattern type to list of pattern names

    Examples:
        >>> patterns = get_available_patterns()
        >>> patterns['candlestick']
        ['doji', 'hammer', 'engulfing']
    """
    return {
        "candlestick": sorted(CANDLESTICK_PATTERNS),
        "daily": sorted(DAILY_PATTERNS),
        "combo": sorted(COMBO_PATTERNS),
    }


def is_pattern_available(pattern_name: str) -> bool:
    """
    Check if pattern is available for loading.

    Args:
        pattern_name: Pattern name to check

    Returns:
        True if pattern is registered, False otherwise

    Examples:
        >>> is_pattern_available('Doji')
        True
        >>> is_pattern_available('UnknownPattern')
        False
    """
    pattern_lower = pattern_name.lower()
    return (
        pattern_lower in CANDLESTICK_PATTERNS
        or pattern_lower in DAILY_PATTERNS
        or pattern_lower in COMBO_PATTERNS
    )
