"""
Shared frequency type definitions for multi-frequency processing
"""

from enum import Enum


class FrequencyType(Enum):
    """Enum for different data frequency types supported by Massive"""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    FAIR_MARKET_VALUE = "fmv"
