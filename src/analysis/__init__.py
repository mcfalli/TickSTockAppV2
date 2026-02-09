"""
TickStockAppV2 Analysis Module.

Core analysis capabilities migrated from TickStockPL in Sprint 68:
- Pattern detection (20+ candlestick and technical patterns)
- Indicator calculation (15 technical indicators)
- Analysis orchestration services

Sprint 68: Core Analysis Migration
"""

from .exceptions import (
    AnalysisError,
    DataValidationError,
    DynamicLoadingError,
    IndicatorError,
    PatternDetectionError,
)

__all__ = [
    "AnalysisError",
    "IndicatorError",
    "PatternDetectionError",
    "DataValidationError",
    "DynamicLoadingError",
]
