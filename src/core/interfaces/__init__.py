# data_providers/base/__init__.py
"""
Base Data Provider Classes

Core abstractions for all data providers.
"""

from src.core.interfaces.data_provider import DataProvider
from src.core.interfaces.data_result import DataResult

__all__ = ['DataProvider', 'DataResult']