"""TickStock Domain - Simplified Architecture.

Core domain models for the simplified TickStock system.
Event models removed as part of cleanup - system now focuses on basic tick data processing.
"""

from src.core.domain.market import TickData

__all__ = [
    # Market Data
    'TickData',
]