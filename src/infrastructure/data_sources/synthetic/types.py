"""
Synthetic data types and enums

Common types used across synthetic data generators.
"""

from enum import Enum
from typing import Dict, Any, Union, Protocol
from abc import ABC, abstractmethod

class DataFrequency(Enum):
    """Supported data frequencies for multi-frequency generation."""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    FAIR_VALUE = "fair_value"

class FrequencyGenerator(Protocol):
    """Protocol for frequency-specific data generators."""
    
    def generate_data(self, ticker: str, config: Dict[str, Any]) -> Union['TickData', Dict[str, Any]]:
        """Generate data for the specific frequency."""
        ...
    
    def supports_frequency(self, frequency: DataFrequency) -> bool:
        """Check if generator supports the given frequency."""
        ...