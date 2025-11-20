"""Simplified data provider factory for TickStockPL integration.

PHASE 6 CLEANUP: Simplified to basic factory pattern with:
- Simple synthetic data provider
- Basic Massive WebSocket integration
- Direct instantiation without complex configuration logic

Removed: Multi-frequency complexity, validation layers, fallback logic.
"""
import logging
from typing import Any

from src.core.interfaces.data_provider import DataProvider
from src.infrastructure.data_sources.massive.provider import MassiveDataProvider
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

logger = logging.getLogger(__name__)

class DataProviderFactory:
    """Simplified factory for creating data provider instances."""

    @classmethod
    def get_provider(cls, config: dict[str, Any]) -> DataProvider:
        """Get data provider based on simple configuration."""
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('MASSIVE_API_KEY', '')

        logger.info(f"DATA-PROVIDER-FACTORY: USE_SYNTHETIC_DATA={use_synthetic}, USE_POLYGON_API={use_polygon}")

        # Simple priority: Massive if configured, otherwise synthetic
        if use_polygon and polygon_api_key:
            try:
                provider = MassiveDataProvider(config)
                if provider.is_available():
                    logger.info("DATA-PROVIDER-FACTORY: Using Massive provider")
                    return provider
                logger.warning("DATA-PROVIDER-FACTORY: Massive API not available, falling back to synthetic")
            except Exception as e:
                logger.error(f"DATA-PROVIDER-FACTORY: Massive initialization failed: {e}")

        # Default to synthetic
        logger.info("DATA-PROVIDER-FACTORY: Using synthetic provider")
        return SimulatedDataProvider(config)
