"""
TickStockAppV2 Pattern Detection Module.

Sprint 68: Core Analysis Migration - Pattern implementations
"""

from .base_pattern import BasePattern, PatternParams
from .loader import load_pattern, is_pattern_available, get_available_patterns

__all__ = [
    "BasePattern",
    "PatternParams",
    "load_pattern",
    "is_pattern_available",
    "get_available_patterns",
]
