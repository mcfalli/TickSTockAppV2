"""
Dynamic Pattern and Indicator Loader using importlib.

Sprint 74: Port from TickStockPL
This module implements dynamic loading of pattern and indicator classes
from the database using Python's importlib for reflection-based instantiation.

NO FALLBACK PROCESSING - If a class is missing, the system will fail.
"""

import importlib
import json
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from src.core.services.config_manager import get_config
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)


class DynamicPatternIndicatorLoader:
    """
    Dynamically loads pattern and indicator classes based on database configuration.

    This loader queries the database for enabled patterns/indicators by timeframe,
    uses importlib to dynamically import the required modules and classes,
    and instantiates them with their configured parameters.

    NO FALLBACK: If a class cannot be loaded, an exception is raised.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the dynamic loader.

        Args:
            config: Configuration dict. If None, uses get_config().
        """
        self.config = config or get_config()
        self.db = TickStockDatabase(self.config)

        # Cache for loaded classes by timeframe
        self._pattern_cache: Dict[str, Dict[str, Any]] = {}
        self._indicator_cache: Dict[str, Dict[str, Any]] = {}

        # Track initialization status
        self._initialized_timeframes = set()

        logger.info("DynamicPatternIndicatorLoader initialized")

    def load_patterns_for_timeframe(self, timeframe: str) -> Dict[str, Any]:
        """
        Load all enabled patterns for a specific timeframe.

        Args:
            timeframe: The timeframe to load patterns for (e.g., 'daily', 'hourly', 'minute')

        Returns:
            Dictionary mapping pattern names to pattern metadata:
            {
                'pattern_name': {
                    'instance': <pattern_instance>,
                    'class_name': 'DojiPattern',
                    'module': 'src.analysis.patterns.candlestick.doji',
                    'category': 'candlestick',
                    'min_bars_required': 1,
                    'confidence_threshold': 0.7
                }
            }

        Raises:
            ImportError: If a pattern class cannot be imported
            AttributeError: If a pattern class doesn't exist in its module
        """
        cache_key = f"patterns_{timeframe}"

        # Return cached patterns if already loaded
        if cache_key in self._pattern_cache:
            logger.debug(f"Using cached patterns for timeframe: {timeframe}")
            return self._pattern_cache[cache_key]

        logger.info(f"Loading patterns for timeframe: {timeframe}")
        patterns = {}

        try:
            with self.db.get_connection() as conn:
                # Query for enabled patterns applicable to this timeframe
                # Note: applicable_timeframes is a VARCHAR[] array column
                query = text("""
                    SELECT
                        name,
                        code_reference,
                        class_name,
                        category,
                        confidence_threshold,
                        risk_level,
                        min_bars_required,
                        instantiation_params
                    FROM pattern_definitions
                    WHERE enabled = true
                        AND (
                            applicable_timeframes IS NULL
                            OR :timeframe = ANY(applicable_timeframes)
                        )
                    ORDER BY display_order, name
                """)

                result = conn.execute(query, {"timeframe": timeframe})

                for row in result.mappings():
                    pattern_name = row['name']
                    code_reference = row['code_reference']
                    class_name = row['class_name']
                    params = row['instantiation_params'] or {}

                    # Skip if no class_name defined
                    if not class_name:
                        logger.warning(
                            f"Pattern {pattern_name} has no class_name defined, skipping"
                        )
                        continue

                    try:
                        # Import the module
                        module = importlib.import_module(code_reference)

                        # Get the class from the module
                        pattern_class = getattr(module, class_name)

                        # Parse instantiation parameters if they're a string
                        if isinstance(params, str):
                            params = json.loads(params) if params else {}

                        # Instantiate the pattern with parameters
                        pattern_instance = pattern_class(**params)

                        # Store pattern metadata
                        patterns[pattern_name] = {
                            'instance': pattern_instance,
                            'class_name': class_name,
                            'module': code_reference,
                            'category': row['category'],
                            'confidence_threshold': float(row['confidence_threshold']) if row['confidence_threshold'] else None,
                            'risk_level': row['risk_level'],
                            'min_bars_required': row['min_bars_required'] or 1,
                        }

                        logger.info(f"Loaded pattern: {pattern_name} ({class_name})")

                    except ImportError as e:
                        logger.error(
                            f"Failed to import module {code_reference} for pattern {pattern_name}: {e}"
                        )
                        raise ImportError(
                            f"Cannot load pattern {pattern_name}: Module {code_reference} not found"
                        ) from e

                    except AttributeError as e:
                        logger.error(
                            f"Class {class_name} not found in module {code_reference} for pattern {pattern_name}: {e}"
                        )
                        raise AttributeError(
                            f"Cannot load pattern {pattern_name}: Class {class_name} not found in {code_reference}"
                        ) from e

                    except Exception as e:
                        logger.error(f"Failed to instantiate pattern {pattern_name}: {e}")
                        raise RuntimeError(
                            f"Cannot instantiate pattern {pattern_name}: {e}"
                        ) from e

        except Exception as e:
            logger.error(f"Database error while loading patterns for timeframe {timeframe}: {e}")
            raise

        # Cache the loaded patterns
        self._pattern_cache[cache_key] = patterns

        logger.info(f"Loaded {len(patterns)} patterns for timeframe: {timeframe}")
        return patterns

    def load_indicators_for_timeframe(self, timeframe: str) -> Dict[str, Any]:
        """
        Load all enabled indicators for a specific timeframe.

        Args:
            timeframe: The timeframe to load indicators for

        Returns:
            Dictionary mapping indicator names to indicator metadata

        Raises:
            ImportError: If an indicator class cannot be imported
            AttributeError: If an indicator class doesn't exist in its module
        """
        cache_key = f"indicators_{timeframe}"

        # Return cached indicators if already loaded
        if cache_key in self._indicator_cache:
            logger.debug(f"Using cached indicators for timeframe: {timeframe}")
            return self._indicator_cache[cache_key]

        logger.info(f"Loading indicators for timeframe: {timeframe}")
        indicators = {}

        try:
            with self.db.get_connection() as conn:
                # Query for enabled indicators applicable to this timeframe
                query = text("""
                    SELECT
                        name,
                        code_reference,
                        class_name,
                        category,
                        period,
                        parameters,
                        min_bars_required,
                        instantiation_params
                    FROM indicator_definitions
                    WHERE enabled = true
                        AND (
                            applicable_timeframes IS NULL
                            OR :timeframe = ANY(applicable_timeframes)
                        )
                    ORDER BY display_order, name
                """)

                result = conn.execute(query, {"timeframe": timeframe})

                for row in result.mappings():
                    indicator_name = row['name']
                    code_reference = row['code_reference']
                    class_name = row['class_name']
                    params = row['instantiation_params'] or {}

                    # Skip if no class_name defined
                    if not class_name:
                        logger.warning(
                            f"Indicator {indicator_name} has no class_name defined, skipping"
                        )
                        continue

                    try:
                        # Import the module
                        module = importlib.import_module(code_reference)

                        # Get the class from the module
                        indicator_class = getattr(module, class_name)

                        # Parse instantiation parameters if they're a string
                        if isinstance(params, str):
                            params = json.loads(params) if params else {}

                        # Instantiate the indicator with parameters
                        indicator_instance = indicator_class(**params)

                        # Store indicator metadata
                        indicators[indicator_name] = {
                            'instance': indicator_instance,
                            'class_name': class_name,
                            'module': code_reference,
                            'category': row['category'],
                            'period': row['period'],
                            'parameters': row['parameters'],
                            'min_bars_required': row['min_bars_required'] or 1,
                        }

                        logger.info(f"Loaded indicator: {indicator_name} ({class_name})")

                    except ImportError as e:
                        logger.error(
                            f"Failed to import module {code_reference} for indicator {indicator_name}: {e}"
                        )
                        raise ImportError(
                            f"Cannot load indicator {indicator_name}: Module {code_reference} not found"
                        ) from e

                    except AttributeError as e:
                        logger.error(
                            f"Class {class_name} not found in module {code_reference} for indicator {indicator_name}: {e}"
                        )
                        raise AttributeError(
                            f"Cannot load indicator {indicator_name}: Class {class_name} not found in {code_reference}"
                        ) from e

                    except Exception as e:
                        logger.error(f"Failed to instantiate indicator {indicator_name}: {e}")
                        raise RuntimeError(
                            f"Cannot instantiate indicator {indicator_name}: {e}"
                        ) from e

        except Exception as e:
            logger.error(f"Database error while loading indicators for timeframe {timeframe}: {e}")
            raise

        # Cache the loaded indicators
        self._indicator_cache[cache_key] = indicators

        logger.info(f"Loaded {len(indicators)} indicators for timeframe: {timeframe}")
        return indicators

    def initialize_timeframe(self, timeframe: str) -> None:
        """
        Initialize all patterns and indicators for a timeframe.

        This method loads both patterns and indicators for the specified timeframe
        and marks it as initialized.

        Args:
            timeframe: The timeframe to initialize

        Raises:
            Exception: If initialization fails (NO FALLBACK)
        """
        if timeframe in self._initialized_timeframes:
            logger.debug(f"Timeframe {timeframe} already initialized")
            return

        logger.info(f"Initializing timeframe: {timeframe}")

        try:
            # Load patterns and indicators for this timeframe
            patterns = self.load_patterns_for_timeframe(timeframe)
            indicators = self.load_indicators_for_timeframe(timeframe)

            # Mark as initialized
            self._initialized_timeframes.add(timeframe)

            logger.info(
                f"Initialized timeframe {timeframe}: "
                f"{len(patterns)} patterns, {len(indicators)} indicators"
            )

        except Exception as e:
            logger.error(f"Failed to initialize timeframe {timeframe}: {e}")
            raise

    def get_pattern(self, timeframe: str, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern for a timeframe.

        Args:
            timeframe: The timeframe
            pattern_name: The pattern name

        Returns:
            Pattern metadata dict or None if not found
        """
        cache_key = f"patterns_{timeframe}"

        if cache_key not in self._pattern_cache:
            self.load_patterns_for_timeframe(timeframe)

        return self._pattern_cache[cache_key].get(pattern_name)

    def get_indicator(self, timeframe: str, indicator_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific indicator for a timeframe.

        Args:
            timeframe: The timeframe
            indicator_name: The indicator name

        Returns:
            Indicator metadata dict or None if not found
        """
        cache_key = f"indicators_{timeframe}"

        if cache_key not in self._indicator_cache:
            self.load_indicators_for_timeframe(timeframe)

        return self._indicator_cache[cache_key].get(indicator_name)

    def clear_cache(self, timeframe: Optional[str] = None) -> None:
        """
        Clear the cache for a specific timeframe or all timeframes.

        Args:
            timeframe: The timeframe to clear, or None to clear all
        """
        if timeframe:
            # Clear specific timeframe
            cache_key_patterns = f"patterns_{timeframe}"
            cache_key_indicators = f"indicators_{timeframe}"

            self._pattern_cache.pop(cache_key_patterns, None)
            self._indicator_cache.pop(cache_key_indicators, None)
            self._initialized_timeframes.discard(timeframe)

            logger.info(f"Cleared cache for timeframe: {timeframe}")
        else:
            # Clear all caches
            self._pattern_cache.clear()
            self._indicator_cache.clear()
            self._initialized_timeframes.clear()

            logger.info("Cleared all caches")

    def get_initialized_timeframes(self) -> List[str]:
        """
        Get list of initialized timeframes.

        Returns:
            List of timeframe strings that have been initialized
        """
        return list(self._initialized_timeframes)

    def get_loaded_patterns(self, timeframe: str) -> List[str]:
        """
        Get list of loaded pattern names for a timeframe.

        Args:
            timeframe: The timeframe

        Returns:
            List of pattern names
        """
        cache_key = f"patterns_{timeframe}"

        if cache_key in self._pattern_cache:
            return list(self._pattern_cache[cache_key].keys())
        return []

    def get_loaded_indicators(self, timeframe: str) -> List[str]:
        """
        Get list of loaded indicator names for a timeframe.

        Args:
            timeframe: The timeframe

        Returns:
            List of indicator names
        """
        cache_key = f"indicators_{timeframe}"

        if cache_key in self._indicator_cache:
            return list(self._indicator_cache[cache_key].keys())
        return []


# Singleton instance for module-level access
_loader_instance: Optional[DynamicPatternIndicatorLoader] = None


def get_dynamic_loader() -> DynamicPatternIndicatorLoader:
    """
    Get the singleton dynamic loader instance.

    Returns:
        DynamicPatternIndicatorLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DynamicPatternIndicatorLoader()
    return _loader_instance
