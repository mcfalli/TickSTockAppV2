"""
Data Providers Package

This package contains all data provider implementations for TickStock.
"""

# Import factory and adapter at package level for easy access
from src.infrastructure.data_sources.factory import DataProviderFactory
from src.infrastructure.data_sources.real_time_data_adapter import RealTimeDataAdapter, SyntheticDataAdapter

# Re-export base classes for convenience
from src.core.interfaces.data_provider import DataProvider
from src.core.interfaces.data_result import DataResult

__all__ = [
    'DataProviderFactory',
    'RealTimeDataAdapter',
    'SyntheticDataAdapter',
    'DataProvider',
    'DataResult'
]