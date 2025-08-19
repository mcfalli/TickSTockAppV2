from typing import Dict, Any, Type, List
from src.core.interfaces.data_provider import DataProvider
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider
from src.infrastructure.data_sources.polygon import PolygonDataProvider
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
        # Check for multi-frequency configuration first
        if config.get('ENABLE_MULTI_FREQUENCY', False):
            return cls._get_multi_frequency_provider(config)
        
        # Legacy single-frequency configuration
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
    
    @classmethod
    def _get_multi_frequency_provider(cls, config: Dict[str, Any]) -> DataProvider:
        """Get provider for multi-frequency configuration."""
        active_providers = config.get('ACTIVE_DATA_PROVIDERS', ['simulated'])
        polygon_api_key = config.get('POLYGON_API_KEY', '')
        
        logger.info(
            f"DIAG-DATA-PROVIDER: Multi-frequency mode enabled with providers: {active_providers}"
        )
        
        # Priority order: polygon (if available) > synthetic > simulated
        if 'polygon' in active_providers and polygon_api_key:
            try:
                provider = PolygonDataProvider(config)
                if provider.is_available():
                    logger.info("DIAG-DATA-PROVIDER: Selected Polygon provider for multi-frequency")
                    return provider
            except Exception as e:
                logger.warning(f"DIAG-DATA-PROVIDER: Polygon provider failed, falling back: {e}")
        
        if 'synthetic' in active_providers or 'simulated' in active_providers:
            logger.info("DIAG-DATA-PROVIDER: Selected SimulatedDataProvider for multi-frequency")
            return SimulatedDataProvider(config)
        
        # Ultimate fallback
        logger.warning("DIAG-DATA-PROVIDER: No valid multi-frequency providers, using default")
        return SimulatedDataProvider(config)

    @classmethod
    def get_providers_for_frequency(cls, config: Dict[str, Any], frequency: str) -> List[DataProvider]:
        """Get all providers configured for a specific frequency."""
        providers = []
        
        # Load WebSocket subscriptions configuration
        from src.core.services.config_manager import get_config
        config_manager_instance = get_config()
        
        if hasattr(config_manager_instance, 'get_websocket_subscriptions'):
            subscriptions_config = config_manager_instance.get_websocket_subscriptions()
            subscriptions = subscriptions_config.get('subscriptions', {})
            
            if frequency in subscriptions:
                freq_config = subscriptions[frequency]
                if freq_config.get('enabled', False):
                    provider_name = freq_config.get('provider')
                    provider_class = cls._providers.get(provider_name)
                    
                    if provider_class:
                        try:
                            # Create provider with frequency-specific config
                            provider_config = dict(config)
                            provider_config.update(freq_config)
                            
                            # Enable appropriate frequency flags for multi-frequency providers
                            if provider_class == SimulatedDataProvider:
                                provider_config['ENABLE_MULTI_FREQUENCY'] = True
                                if frequency == 'per_second':
                                    provider_config['WEBSOCKET_PER_SECOND_ENABLED'] = True
                                elif frequency == 'per_minute':
                                    provider_config['WEBSOCKET_PER_MINUTE_ENABLED'] = True
                                elif frequency == 'fair_value':
                                    provider_config['WEBSOCKET_FAIR_VALUE_ENABLED'] = True
                            
                            provider = provider_class(provider_config)
                            providers.append(provider)
                            
                            logger.info(f"DIAG-DATA-PROVIDER: Created {provider_name} provider for {frequency} frequency")
                            
                        except Exception as e:
                            logger.error(f"DIAG-DATA-PROVIDER: Failed to create {provider_name} provider for {frequency}: {e}")
        
        return providers
    
    @classmethod
    def create_multi_frequency_provider(cls, config: Dict[str, Any], frequencies: List[str]) -> DataProvider:
        """Create a provider configured for multiple specific frequencies."""
        provider_config = dict(config)
        provider_config['ENABLE_MULTI_FREQUENCY'] = True
        
        # Enable frequency flags based on requested frequencies
        frequency_flags = {
            'per_second': 'WEBSOCKET_PER_SECOND_ENABLED',
            'per_minute': 'WEBSOCKET_PER_MINUTE_ENABLED', 
            'fair_value': 'WEBSOCKET_FAIR_VALUE_ENABLED'
        }
        
        for frequency in frequencies:
            if frequency in frequency_flags:
                provider_config[frequency_flags[frequency]] = True
        
        # Use the standard provider selection logic
        provider = cls._get_multi_frequency_provider(provider_config)
        
        logger.info(
            f"DIAG-DATA-PROVIDER: Created multi-frequency provider for {frequencies} "
            f"using {type(provider).__name__}"
        )
        
        return provider
    
    @classmethod 
    def validate_provider_configuration(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate provider configuration and return validation results."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'available_providers': []
        }
        
        active_providers = config.get('ACTIVE_DATA_PROVIDERS', [])
        polygon_api_key = config.get('POLYGON_API_KEY', '')
        
        for provider_name in active_providers:
            if provider_name not in cls._providers:
                validation_result['errors'].append(f"Unknown provider: {provider_name}")
                validation_result['valid'] = False
                continue
            
            # Provider-specific validation
            if provider_name == 'polygon':
                if not polygon_api_key:
                    validation_result['errors'].append("POLYGON_API_KEY required for polygon provider")
                    validation_result['valid'] = False
                else:
                    validation_result['available_providers'].append(provider_name)
            else:
                validation_result['available_providers'].append(provider_name)
        
        # Warn if no providers available
        if not validation_result['available_providers']:
            validation_result['warnings'].append("No valid providers configured, will use default SimulatedDataProvider")
            validation_result['available_providers'].append('simulated')
        
        return validation_result

# Register default providers
DataProviderFactory.register_provider("synthetic", SimulatedDataProvider)
DataProviderFactory.register_provider("polygon", PolygonDataProvider) 
DataProviderFactory.register_provider("simulated", SimulatedDataProvider)  # Alias for backward compatibility

# Register multi-frequency alias
DataProviderFactory.register_provider("multi_frequency_synthetic", SimulatedDataProvider)