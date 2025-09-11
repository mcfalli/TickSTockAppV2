"""Simplified data provider factory for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to basic factory pattern with:
- Simple synthetic data provider
- Basic Polygon WebSocket integration
- Direct instantiation without complex configuration logic

Removed: Multi-frequency complexity, validation layers, fallback logic.
"""
from typing import Dict, Any
from src.core.interfaces.data_provider import DataProvider
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
from src.infrastructure.data_sources.polygon.provider import PolygonDataProvider
import logging

logger = logging.getLogger(__name__)

class DataProviderFactory:
    """Simplified factory for creating data provider instances."""
    
    @classmethod
    def get_provider(cls, config: Dict[str, Any]) -> DataProvider:
        """Get data provider based on simple configuration."""
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('POLYGON_API_KEY', '')

        logger.info(f"DATA-PROVIDER-FACTORY: USE_SYNTHETIC_DATA={use_synthetic}, USE_POLYGON_API={use_polygon}")

        # Simple priority: Polygon if configured, otherwise synthetic
        if use_polygon and polygon_api_key:
            try:
                provider = PolygonDataProvider(config)
                if provider.is_available():
                    logger.info("DATA-PROVIDER-FACTORY: Using Polygon provider")
                    return provider
                else:
                    logger.warning("DATA-PROVIDER-FACTORY: Polygon API not available, falling back to synthetic")
            except Exception as e:
                logger.error(f"DATA-PROVIDER-FACTORY: Polygon initialization failed: {e}")
        
        # Default to synthetic
        logger.info("DATA-PROVIDER-FACTORY: Using synthetic provider")
        return SimulatedDataProvider(config)