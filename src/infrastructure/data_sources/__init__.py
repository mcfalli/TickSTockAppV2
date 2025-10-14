"""Module initialization."""

from src.core.interfaces.data_provider import DataProvider

from .factory import DataProviderFactory

__all__ = ['DataProviderFactory', 'DataProvider']
