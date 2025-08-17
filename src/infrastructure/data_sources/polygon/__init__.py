# data_providers/polygon/__init__.py
"""
Polygon Data Provider Implementation

Provides real-time market data from Polygon.io API.
"""

from src.infrastructure.data_sources.polygon.api import PolygonAPI
from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider

__all__ = ['PolygonAPI', 'PolygonDataProvider']