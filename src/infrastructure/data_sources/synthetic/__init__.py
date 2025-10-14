# data_providers/simulated/__init__.py
"""
Simulated Data Provider Implementation

Provides synthetic market data for testing and development.
"""

from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

__all__ = [
    'SimulatedDataProvider',
]
