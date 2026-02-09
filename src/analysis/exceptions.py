"""
Exception classes for TickStockAppV2 analysis module.

Custom exception hierarchy for pattern detection and indicator calculation errors.
Sprint 68: Core Analysis Migration
"""

from typing import Any


class AnalysisError(Exception):
    """Base exception for all analysis-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        """
        Initialize analysis error with context.

        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message)
        self.context = context or {}


class IndicatorError(AnalysisError):
    """Exception raised when indicator calculation fails."""

    def __init__(
        self,
        message: str,
        indicator_name: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        **kwargs,
    ):
        """
        Initialize indicator error with context.

        Args:
            message: Error message
            indicator_name: Name of indicator that failed
            symbol: Stock symbol being processed
            timeframe: Timeframe being processed
            **kwargs: Additional context
        """
        context = {
            "indicator_name": indicator_name,
            "symbol": symbol,
            "timeframe": timeframe,
            **kwargs,
        }
        super().__init__(message, context)


class PatternDetectionError(AnalysisError):
    """Exception raised when pattern detection fails."""

    def __init__(
        self,
        message: str,
        pattern_name: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        data_info: str | None = None,
        **kwargs,
    ):
        """
        Initialize pattern detection error with context.

        Args:
            message: Error message
            pattern_name: Name of pattern that failed
            symbol: Stock symbol being processed
            timeframe: Timeframe being processed
            data_info: Information about data being processed
            **kwargs: Additional context
        """
        context = {
            "pattern_name": pattern_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "data_info": data_info,
            **kwargs,
        }
        super().__init__(message, context)


class DataValidationError(AnalysisError):
    """Exception raised when data validation fails."""

    def __init__(
        self,
        message: str,
        missing_columns: list[str] | None = None,
        data_length: int | None = None,
        required_length: int | None = None,
        **kwargs,
    ):
        """
        Initialize data validation error with context.

        Args:
            message: Error message
            missing_columns: List of missing required columns
            data_length: Actual data length
            required_length: Required minimum data length
            **kwargs: Additional context
        """
        context = {
            "missing_columns": missing_columns,
            "data_length": data_length,
            "required_length": required_length,
            **kwargs,
        }
        super().__init__(message, context)


class DynamicLoadingError(AnalysisError):
    """Exception raised when dynamic loading fails (NO FALLBACK policy)."""

    def __init__(
        self,
        message: str,
        module_name: str | None = None,
        class_name: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        """
        Initialize dynamic loading error with context.

        Args:
            message: Error message
            module_name: Module that failed to load
            class_name: Class that failed to load
            reason: Reason for failure
            **kwargs: Additional context
        """
        context = {
            "module_name": module_name,
            "class_name": class_name,
            "reason": reason,
            **kwargs,
        }
        super().__init__(message, context)


# Alias for pattern-specific loading errors
class PatternLoadError(DynamicLoadingError):
    """Exception raised when pattern loading fails (NO FALLBACK policy)."""

    pass


# Alias for indicator-specific loading errors
class IndicatorLoadError(DynamicLoadingError):
    """Exception raised when indicator loading fails (NO FALLBACK policy)."""

    pass


class InvalidIndicatorError(AnalysisError):
    """Exception raised when an invalid/unknown indicator is requested."""

    def __init__(
        self,
        message: str,
        indicator_name: str | None = None,
        available_indicators: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize invalid indicator error with context.

        Args:
            message: Error message
            indicator_name: Name of invalid indicator
            available_indicators: List of available indicators
            **kwargs: Additional context
        """
        context = {
            "indicator_name": indicator_name,
            "available_indicators": available_indicators,
            **kwargs,
        }
        super().__init__(message, context)


class InvalidPatternError(AnalysisError):
    """Exception raised when an invalid/unknown pattern is requested."""

    def __init__(
        self,
        message: str,
        pattern_name: str | None = None,
        available_patterns: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize invalid pattern error with context.

        Args:
            message: Error message
            pattern_name: Name of invalid pattern
            available_patterns: List of available patterns
            **kwargs: Additional context
        """
        context = {
            "pattern_name": pattern_name,
            "available_patterns": available_patterns,
            **kwargs,
        }
        super().__init__(message, context)
