from typing import Dict, Any, Type
from src.core.interfaces.data_provider import DataProvider
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
from src.infrastructure.data_sources.polygon.polygon_data_provider import PolygonDataProvider
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'data_provider_factory')

class DataProviderFactory:
    """Factory for creating data provider instances with a registry pattern."""
    
    _providers: Dict[str, Type[DataProvider]] = {}
    _default_provider = SimulatedDataProvider

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[DataProvider]):
        """Register a new data provider."""
        cls._providers[name] = provider_class
        logger.debug(f"DIAG-DATA-PROVIDER: Registered provider: {name}")

    @classmethod
    def get_provider(cls, config: Dict[str, Any]) -> DataProvider:
        """Get the appropriate data provider based on configuration."""
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('POLYGON_API_KEY', '')

        logger.info(f"DIAG-DATA-PROVIDER: Selecting provider - USE_SYNTHETIC_DATA={use_synthetic}, USE_POLYGON_API={use_polygon}")

        # Priority: Synthetic > Polygon > Default (Simulated)
        if use_synthetic:
            provider_name = "synthetic"
            provider_class = cls._providers.get(provider_name, SimulatedDataProvider)
            logger.info(f"DIAG-DATA-PROVIDER: Selected {provider_name} provider (synthetic enabled)")
            return provider_class(config)

        if use_polygon and polygon_api_key:
            provider_name = "polygon"
            provider_class = cls._providers.get(provider_name, PolygonDataProvider)
            try:
                provider = provider_class(config)
                if provider.is_available():
                    logger.info(f"DIAG-DATA-PROVIDER: Selected {provider_name} provider (API available)")
                    return provider
                else:
                    logger.warning(f"DIAG-DATA-PROVIDER: {provider_name} API not available")
            except Exception as e:
                logger.error(f"DIAG-DATA-PROVIDER: Failed to initialize {provider_name} provider: {str(e)}")

        # Fallback to default
        logger.info("DIAG-DATA-PROVIDER: Falling back to default SimulatedDataProvider")
        return cls._default_provider(config)

# Register default providers
DataProviderFactory.register_provider("synthetic", SimulatedDataProvider)
DataProviderFactory.register_provider("polygon", PolygonDataProvider)