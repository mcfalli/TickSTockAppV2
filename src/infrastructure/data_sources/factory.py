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
        """Get the appropriate data provider based on configuration - NO FALLBACKS."""
        # PRODUCTION HARDENING: Validate configuration first
        cls._validate_provider_configuration(config)
        
        # Check for multi-frequency configuration first
        if config.get('ENABLE_MULTI_FREQUENCY', False):
            logger.info("DATA-PROVIDER-FACTORY: 🔧 Multi-frequency mode enabled")
            return cls._get_multi_frequency_provider(config)
        
        # Legacy single-frequency configuration
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('POLYGON_API_KEY', '')

        logger.info("DATA-PROVIDER-FACTORY: 🔧 Configuration validation:")
        logger.info(f"DATA-PROVIDER-FACTORY:    USE_SYNTHETIC_DATA: {'✅ ENABLED' if use_synthetic else '❌ DISABLED'}")
        logger.info(f"DATA-PROVIDER-FACTORY:    USE_POLYGON_API: {'✅ ENABLED' if use_polygon else '❌ DISABLED'}")
        logger.info(f"DATA-PROVIDER-FACTORY:    POLYGON_API_KEY: {'✅ PROVIDED' if polygon_api_key else '❌ MISSING'}")

        # REMOVED FALLBACK - Configuration must be explicit
        if use_synthetic:
            provider_name = "synthetic"
            provider_class = cls._providers.get(provider_name, SimulatedDataProvider)
            logger.info(f"DATA-PROVIDER-FACTORY: ✅ Selected {provider_name} provider (synthetic enabled)")
            return provider_class(config)

        if use_polygon and polygon_api_key:
            provider_name = "polygon"
            provider_class = cls._providers.get(provider_name, PolygonDataProvider)
            try:
                provider = provider_class(config)
                if provider.is_available():
                    logger.info(f"DATA-PROVIDER-FACTORY: ✅ Selected {provider_name} provider (API available)")
                    return provider
                else:
                    error_msg = (
                        f"🚨 DATA-PROVIDER-FACTORY: CONFIGURATION ERROR - {provider_name} API not available!\n"
                        f"   USE_POLYGON_API=true but API is not responding.\n"
                        f"   Either fix API connectivity or switch to synthetic data."
                    )
                    logger.error(error_msg)
                    raise ValueError(f"{provider_name} API not available")
            except Exception as e:
                error_msg = (
                    f"🚨 DATA-PROVIDER-FACTORY: CONFIGURATION ERROR - Failed to initialize {provider_name}!\n"
                    f"   Error: {str(e)}\n"
                    f"   Check API key and connectivity."
                )
                logger.error(error_msg)
                raise ValueError(f"Failed to initialize {provider_name} provider: {str(e)}")

        # NO FALLBACK - Fail explicitly 
        error_msg = (
            "🚨 DATA-PROVIDER-FACTORY: CONFIGURATION ERROR - No data provider configured!\n"
            "   Required: Set one of the following in configuration:\n"
            "   - USE_SYNTHETIC_DATA=true (for synthetic/simulated data)\n"
            "   - USE_POLYGON_API=true + POLYGON_API_KEY=<key> (for live data)"
        )
        logger.error(error_msg)
        raise ValueError("No data provider configured. Configuration must be explicit.")
    
    @classmethod
    def _validate_provider_configuration(cls, config: Dict[str, Any]):
        """Validate provider configuration is explicit and complete"""
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('POLYGON_API_KEY', '')
        multi_frequency = config.get('ENABLE_MULTI_FREQUENCY', False)
        
        # At least one provider must be configured
        if not use_synthetic and not use_polygon:
            error_msg = (
                "🚨 DATA-PROVIDER-FACTORY: CONFIGURATION ERROR - No data source configured!\n"
                "   At least one data source must be enabled:\n"
                "   - USE_SYNTHETIC_DATA=true\n"
                "   - USE_POLYGON_API=true"
            )
            logger.error(error_msg)
            raise ValueError("No data source configured")
        
        # If Polygon is enabled, API key is required
        if use_polygon and not polygon_api_key:
            error_msg = (
                "🚨 DATA-PROVIDER-FACTORY: CONFIGURATION ERROR - Polygon requires API key!\n"
                "   USE_POLYGON_API=true but POLYGON_API_KEY is missing.\n"
                "   Either provide API key or switch to synthetic data."
            )
            logger.error(error_msg)
            raise ValueError("Polygon API requires valid API key")
        
        logger.info("DATA-PROVIDER-FACTORY: ✅ Provider configuration validated")
    
    @classmethod
    def _get_multi_frequency_provider(cls, config: Dict[str, Any]) -> DataProvider:
        """Get provider for multi-frequency configuration - NO FALLBACKS."""
        use_synthetic = config.get('USE_SYNTHETIC_DATA', False)
        use_polygon = config.get('USE_POLYGON_API', False)
        polygon_api_key = config.get('POLYGON_API_KEY', '')
        
        logger.info("DATA-PROVIDER-FACTORY: 🔧 Multi-frequency provider selection:")
        logger.info(f"DATA-PROVIDER-FACTORY:    USE_SYNTHETIC_DATA: {'✅ ENABLED' if use_synthetic else '❌ DISABLED'}")
        logger.info(f"DATA-PROVIDER-FACTORY:    USE_POLYGON_API: {'✅ ENABLED' if use_polygon else '❌ DISABLED'}")
        
        # Priority order: polygon (if configured) > synthetic (if configured)
        if use_polygon and polygon_api_key:
            try:
                provider = PolygonDataProvider(config)
                if provider.is_available():
                    logger.info("DATA-PROVIDER-FACTORY: ✅ Selected Polygon provider for multi-frequency")
                    return provider
                else:
                    error_msg = (
                        "🚨 DATA-PROVIDER-FACTORY: MULTI-FREQUENCY ERROR - Polygon API not available!\n"
                        "   USE_POLYGON_API=true but API is not responding.\n"
                        "   Either fix API connectivity or switch to USE_SYNTHETIC_DATA=true."
                    )
                    logger.error(error_msg)
                    raise ValueError("Polygon API not available for multi-frequency")
            except Exception as e:
                error_msg = (
                    f"🚨 DATA-PROVIDER-FACTORY: MULTI-FREQUENCY ERROR - Polygon initialization failed!\n"
                    f"   Error: {str(e)}\n"
                    f"   Check API key and connectivity or switch to synthetic data."
                )
                logger.error(error_msg)
                raise ValueError(f"Polygon provider failed for multi-frequency: {str(e)}")
        
        if use_synthetic:
            logger.info("DATA-PROVIDER-FACTORY: ✅ Selected SimulatedDataProvider for multi-frequency")
            return SimulatedDataProvider(config)
        
        # NO FALLBACK - Fail explicitly
        error_msg = (
            "🚨 DATA-PROVIDER-FACTORY: MULTI-FREQUENCY ERROR - No provider configured!\n"
            "   Multi-frequency mode requires explicit data source:\n"
            "   - USE_SYNTHETIC_DATA=true (for synthetic multi-frequency data)\n"
            "   - USE_POLYGON_API=true + POLYGON_API_KEY=<key> (for live multi-frequency data)"
        )
        logger.error(error_msg)
        raise ValueError("No multi-frequency provider configured. Configuration must be explicit.")

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