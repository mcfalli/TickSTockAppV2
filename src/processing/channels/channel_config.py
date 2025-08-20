"""
Channel configuration management system.

Provides comprehensive configuration support for multi-channel processing
with validation, file persistence, and integration with existing ConfigManager.

Sprint 105: Core Channel Infrastructure Implementation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
import json
import os
from pathlib import Path
# Try to import jsonschema for validation, make it optional
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    jsonschema = None
    HAS_JSONSCHEMA = False
from abc import ABC, abstractmethod

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'channel_config')


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class BatchingStrategy(Enum):
    """Batching strategies for channel processing"""
    IMMEDIATE = "immediate"      # Process immediately (for tick data)
    TIME_BASED = "time_based"    # Batch for X milliseconds
    SIZE_BASED = "size_based"    # Batch until X items
    HYBRID = "hybrid"            # Combine time and size limits


@dataclass
class BatchingConfig:
    """
    Batching configuration for channels.
    Controls how data is batched before processing.
    """
    strategy: BatchingStrategy
    max_batch_size: int = 1
    max_wait_time_ms: int = 100
    overflow_action: str = "drop_oldest"  # or "reject_new"
    
    def __post_init__(self):
        """Validate batching configuration on creation"""
        self.validate()
    
    def validate(self):
        """Validate batching configuration"""
        if self.max_batch_size < 1:
            raise ConfigValidationError("max_batch_size must be >= 1")
        if self.max_wait_time_ms < 0:
            raise ConfigValidationError("max_wait_time_ms must be >= 0")
        if self.overflow_action not in ["drop_oldest", "reject_new"]:
            raise ConfigValidationError("overflow_action must be 'drop_oldest' or 'reject_new'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strategy': self.strategy.value,
            'max_batch_size': self.max_batch_size,
            'max_wait_time_ms': self.max_wait_time_ms,
            'overflow_action': self.overflow_action
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchingConfig':
        """Create from dictionary"""
        return cls(
            strategy=BatchingStrategy(data['strategy']),
            max_batch_size=data.get('max_batch_size', 1),
            max_wait_time_ms=data.get('max_wait_time_ms', 100),
            overflow_action=data.get('overflow_action', 'drop_oldest')
        )


@dataclass
class ChannelConfig(ABC):
    """
    Base configuration class for all channels.
    Provides common configuration options and validation framework.
    """
    # Basic channel identification
    name: str
    enabled: bool = True
    priority: int = 1  # 1=highest
    
    # Processing configuration
    max_concurrent_processing: int = 1
    processing_timeout_ms: int = 1000
    
    # Queue configuration
    max_queue_size: int = 1000
    
    # Batching configuration
    batching: BatchingConfig = field(default_factory=lambda: BatchingConfig(BatchingStrategy.IMMEDIATE))
    
    # Circuit breaker configuration
    circuit_breaker_threshold: int = 5  # consecutive errors before opening
    circuit_breaker_timeout: int = 60   # seconds before auto-close
    
    # Monitoring
    metrics_enabled: bool = True
    health_check_interval: int = 30  # seconds
    
    # Error handling
    error_threshold: float = 0.1  # 10% error rate threshold
    retry_attempts: int = 3
    retry_delay_ms: int = 1000
    
    # Channel-specific parameters (subclasses can extend)
    detection_parameters: Dict[str, Any] = field(default_factory=dict)
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration on creation"""
        self.validate()
    
    def validate(self):
        """Validate base configuration"""
        if self.priority < 1:
            raise ConfigValidationError("priority must be >= 1")
        if self.max_concurrent_processing < 1:
            raise ConfigValidationError("max_concurrent_processing must be >= 1")
        if self.processing_timeout_ms < 100:
            raise ConfigValidationError("processing_timeout_ms must be >= 100ms")
        if not (0.0 <= self.error_threshold <= 1.0):
            raise ConfigValidationError("error_threshold must be between 0.0 and 1.0")
        if self.max_queue_size < 1:
            raise ConfigValidationError("max_queue_size must be >= 1")
        if self.circuit_breaker_threshold < 1:
            raise ConfigValidationError("circuit_breaker_threshold must be >= 1")
        if self.retry_attempts < 0:
            raise ConfigValidationError("retry_attempts must be >= 0")
        
        # Validate batching configuration
        self.batching.validate()
        
        # Channel-specific validation
        self._validate_channel_specific()
    
    @abstractmethod
    def _validate_channel_specific(self):
        """Validate channel-specific configuration (implemented by subclasses)"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'priority': self.priority,
            'max_concurrent_processing': self.max_concurrent_processing,
            'processing_timeout_ms': self.processing_timeout_ms,
            'max_queue_size': self.max_queue_size,
            'batching': self.batching.to_dict(),
            'circuit_breaker': {
                'threshold': self.circuit_breaker_threshold,
                'timeout': self.circuit_breaker_timeout
            },
            'monitoring': {
                'metrics_enabled': self.metrics_enabled,
                'health_check_interval': self.health_check_interval
            },
            'error_handling': {
                'error_threshold': self.error_threshold,
                'retry_attempts': self.retry_attempts,
                'retry_delay_ms': self.retry_delay_ms
            },
            'detection_parameters': self.detection_parameters,
            'custom_parameters': self.custom_parameters
        }


@dataclass
class TickChannelConfig(ChannelConfig):
    """Configuration specific to Tick data channels"""
    
    # Real-time processing specific settings
    enable_event_detection: bool = True
    universe_filter: Optional[List[str]] = None  # Ticker symbols to process
    
    # Event detection settings (integrated with existing ConfigManager)
    highlow_detection: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'min_price_change': 0.01,
        'min_percent_change': 0.1,
        'cooldown_seconds': 1,
        'market_aware': True,
        'extended_hours_multiplier': 2.0,
        'opening_multiplier': 1.5
    })
    
    trend_detection: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'direction_threshold': 0.025,
        'strength_threshold': 0.05,
        'global_sensitivity': 1.5,
        'min_data_points': 8,
        'warmup_period_seconds': 90,
        'retracement_threshold': 0.25
    })
    
    surge_detection: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'threshold_multiplier': 0.4,
        'volume_threshold': 3.0,
        'global_sensitivity': 0.4,
        'min_data_points': 8,
        'interval_seconds': 20,
        'price_threshold_percent': 4.0
    })
    
    def __post_init__(self):
        # Tick channels should use immediate processing
        self.batching = BatchingConfig(
            strategy=BatchingStrategy.IMMEDIATE,
            max_batch_size=1,
            max_wait_time_ms=0
        )
        
        # Set high priority for tick channels
        self.priority = 1
        
        # Merge detection parameters
        self.detection_parameters.update({
            'highlow': self.highlow_detection,
            'trend': self.trend_detection,
            'surge': self.surge_detection
        })
        
        # Call parent post_init
        super().__post_init__()
    
    def _validate_channel_specific(self):
        """Validate tick-specific configuration"""
        if self.batching.strategy != BatchingStrategy.IMMEDIATE:
            raise ConfigValidationError("Tick channels must use IMMEDIATE batching strategy")
        
        # Validate detection parameters exist
        required_sections = ['highlow', 'trend', 'surge']
        for section in required_sections:
            if section not in self.detection_parameters:
                raise ConfigValidationError(f"Missing detection parameters section: {section}")
        
        # Validate universe filter if specified
        if self.universe_filter is not None and not isinstance(self.universe_filter, list):
            raise ConfigValidationError("universe_filter must be a list of ticker symbols")


@dataclass
class OHLCVChannelConfig(ChannelConfig):
    """Configuration specific to OHLCV bar data channels"""
    
    # Bar processing specific settings
    supported_timeframes: List[str] = field(default_factory=lambda: ['1m', '5m', '15m', '1h'])
    enable_gap_detection: bool = True
    enable_volume_analysis: bool = True
    
    # OHLCV specific detection parameters
    bar_analysis: Dict[str, Any] = field(default_factory=lambda: {
        'significant_move_threshold': 2.0,  # 2% price move
        'volume_spike_multiplier': 5.0,     # 5x average volume
        'gap_threshold_percent': 1.0,       # 1% gap threshold
        'consolidation_detection': True
    })
    
    aggregation_rules: Dict[str, Any] = field(default_factory=lambda: {
        'min_volume': 1000,
        'exclude_extended_hours': False,
        'adjust_for_splits': True,
        'adjust_for_dividends': False
    })
    
    def __post_init__(self):
        # OHLCV channels typically use size-based batching
        self.batching = BatchingConfig(
            strategy=BatchingStrategy.SIZE_BASED,
            max_batch_size=100,
            max_wait_time_ms=1000
        )
        
        # Set medium priority
        self.priority = 2
        
        self.detection_parameters.update({
            'bar_analysis': self.bar_analysis,
            'aggregation_rules': self.aggregation_rules
        })
        
        super().__post_init__()
    
    def _validate_channel_specific(self):
        """Validate OHLCV-specific configuration"""
        if not self.supported_timeframes:
            raise ConfigValidationError("supported_timeframes cannot be empty")
        
        valid_timeframes = ['1s', '5s', '15s', '30s', '1m', '5m', '15m', '30m', '1h', '4h', '1d']
        for tf in self.supported_timeframes:
            if tf not in valid_timeframes:
                raise ConfigValidationError(f"Invalid timeframe: {tf}")


@dataclass
class FMVChannelConfig(ChannelConfig):
    """Configuration specific to Fair Market Value channels"""
    
    # FMV processing specific settings
    valuation_models: List[str] = field(default_factory=lambda: ['dcf', 'comparable', 'option_based'])
    enable_deviation_alerts: bool = True
    update_frequency_seconds: int = 30
    
    # FMV specific parameters
    valuation_parameters: Dict[str, Any] = field(default_factory=lambda: {
        'deviation_threshold_percent': 5.0,  # 5% deviation alert
        'confidence_threshold': 0.7,         # 70% confidence minimum
        'max_staleness_minutes': 15,         # Max age for input data
        'correlation_threshold': 0.8         # Market correlation requirement
    })
    
    risk_parameters: Dict[str, Any] = field(default_factory=lambda: {
        'volatility_adjustment': True,
        'liquidity_adjustment': True,
        'market_stress_multiplier': 1.5,
        'sector_correlation_weight': 0.3
    })
    
    def __post_init__(self):
        # FMV channels use hybrid batching (time + size)
        self.batching = BatchingConfig(
            strategy=BatchingStrategy.HYBRID,
            max_batch_size=50,
            max_wait_time_ms=5000  # 5 seconds max wait
        )
        
        # Set lower priority
        self.priority = 3
        
        self.detection_parameters.update({
            'valuation': self.valuation_parameters,
            'risk': self.risk_parameters
        })
        
        super().__post_init__()
    
    def _validate_channel_specific(self):
        """Validate FMV-specific configuration"""
        if self.update_frequency_seconds < 1:
            raise ConfigValidationError("update_frequency_seconds must be >= 1")
        
        if not self.valuation_models:
            raise ConfigValidationError("valuation_models cannot be empty")
        
        valid_models = ['dcf', 'comparable', 'option_based', 'capm', 'wacc']
        for model in self.valuation_models:
            if model not in valid_models:
                raise ConfigValidationError(f"Invalid valuation model: {model}")


class ChannelConfigurationManager:
    """
    Manages configuration for all channel types with validation,
    file persistence, and integration with existing ConfigManager.
    """
    
    def __init__(self, config_dir: Optional[Path] = None, global_config_manager=None):
        self.config_dir = config_dir or Path("config/channels")
        self.global_config = global_config_manager
        self.configurations: Dict[str, ChannelConfig] = {}
        self.config_schemas = self._load_schemas()
        self._change_callbacks: List[Callable[[str, ChannelConfig], None]] = []
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized ChannelConfigurationManager with config dir: {self.config_dir}")
    
    def _load_schemas(self) -> Dict[str, Dict]:
        """Load JSON schemas for configuration validation"""
        return {
            'tick': {
                'type': 'object',
                'required': ['name', 'enabled', 'priority'],
                'properties': {
                    'name': {'type': 'string'},
                    'enabled': {'type': 'boolean'},
                    'priority': {'type': 'integer', 'minimum': 1},
                    'enable_event_detection': {'type': 'boolean'},
                    'highlow_detection': {'type': 'object'},
                    'trend_detection': {'type': 'object'},
                    'surge_detection': {'type': 'object'},
                    'universe_filter': {
                        'type': ['array', 'null'],
                        'items': {'type': 'string'}
                    }
                }
            },
            'ohlcv': {
                'type': 'object', 
                'required': ['name', 'enabled', 'priority'],
                'properties': {
                    'name': {'type': 'string'},
                    'enabled': {'type': 'boolean'},
                    'priority': {'type': 'integer', 'minimum': 1},
                    'supported_timeframes': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'bar_analysis': {'type': 'object'},
                    'aggregation_rules': {'type': 'object'}
                }
            },
            'fmv': {
                'type': 'object',
                'required': ['name', 'enabled', 'priority'],
                'properties': {
                    'name': {'type': 'string'},
                    'enabled': {'type': 'boolean'}, 
                    'priority': {'type': 'integer', 'minimum': 1},
                    'valuation_models': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'valuation_parameters': {'type': 'object'},
                    'risk_parameters': {'type': 'object'}
                }
            }
        }
    
    def create_channel_config(self, channel_type: str, **kwargs) -> ChannelConfig:
        """Create channel configuration of appropriate type"""
        from .base_channel import ChannelType  # Import here to avoid circular dependency
        
        if channel_type == ChannelType.TICK.value:
            return TickChannelConfig(**kwargs)
        elif channel_type == ChannelType.OHLCV.value:
            return OHLCVChannelConfig(**kwargs)
        elif channel_type == ChannelType.FMV.value:
            return FMVChannelConfig(**kwargs)
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")
    
    def load_configuration(self, config_name: str, channel_type: str) -> ChannelConfig:
        """Load configuration from file or create default"""
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            # Create default configuration
            default_config = self.create_channel_config(channel_type, name=config_name)
            
            # Integrate with global config if available
            if self.global_config:
                self._integrate_global_config(default_config, channel_type)
            
            self.save_configuration(config_name, default_config)
            return default_config
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Validate against schema (if jsonschema is available)
            if HAS_JSONSCHEMA and channel_type in self.config_schemas:
                jsonschema.validate(config_data, self.config_schemas[channel_type])
            
            # Handle nested objects
            if 'batching' in config_data and isinstance(config_data['batching'], dict):
                config_data['batching'] = BatchingConfig.from_dict(config_data['batching'])
            
            # Create configuration object
            config = self.create_channel_config(channel_type, **config_data)
            
            # Integrate with global config if available
            if self.global_config:
                self._integrate_global_config(config, channel_type)
            
            config.validate()
            self.configurations[config_name] = config
            
            logger.info(f"Loaded configuration for {channel_type} channel: {config_name}")
            return config
            
        except (json.JSONDecodeError, ConfigValidationError) as e:
            raise ConfigValidationError(f"Invalid configuration file {config_file}: {e}")
        except Exception as e:
            if HAS_JSONSCHEMA and 'ValidationError' in str(type(e)):
                raise ConfigValidationError(f"Schema validation failed for {config_file}: {e}")
            else:
                raise ConfigValidationError(f"Invalid configuration file {config_file}: {e}")
    
    def _integrate_global_config(self, config: ChannelConfig, channel_type: str):
        """Integrate configuration with existing global ConfigManager"""
        if not self.global_config or channel_type != 'tick':
            return
        
        try:
            # Pull detection parameters from global config (Sprint 103 integration)
            if isinstance(config, TickChannelConfig):
                # HighLow detection parameters
                config.highlow_detection.update({
                    'min_price_change': self.global_config.config.get('HIGHLOW_MIN_PRICE_CHANGE', 0.01),
                    'min_percent_change': self.global_config.config.get('HIGHLOW_MIN_PERCENT_CHANGE', 0.1),
                    'cooldown_seconds': self.global_config.config.get('HIGHLOW_COOLDOWN_SECONDS', 1),
                    'market_aware': self.global_config.config.get('HIGHLOW_MARKET_AWARE', True),
                    'extended_hours_multiplier': self.global_config.config.get('HIGHLOW_EXTENDED_HOURS_MULTIPLIER', 2.0),
                    'opening_multiplier': self.global_config.config.get('HIGHLOW_OPENING_MULTIPLIER', 1.5)
                })
                
                # Trend detection parameters (midday settings as default)
                config.trend_detection.update({
                    'direction_threshold': self.global_config.config.get('TREND_DIRECTION_THRESHOLD_MIDDAY', 0.025),
                    'strength_threshold': self.global_config.config.get('TREND_STRENGTH_THRESHOLD_MIDDAY', 0.05),
                    'global_sensitivity': self.global_config.config.get('TREND_GLOBAL_SENSITIVITY_MIDDAY', 1.5),
                    'min_data_points': self.global_config.config.get('TREND_MIN_DATA_POINTS_PER_WINDOW_MIDDAY', 8),
                    'warmup_period_seconds': self.global_config.config.get('TREND_WARMUP_PERIOD_SECONDS_MIDDAY', 90),
                    'retracement_threshold': self.global_config.config.get('TREND_RETRACEMENT_THRESHOLD_MIDDAY', 0.25)
                })
                
                # Surge detection parameters (midday settings as default)
                config.surge_detection.update({
                    'threshold_multiplier': self.global_config.config.get('SURGE_THRESHOLD_MULTIPLIER_MIDDAY', 0.4),
                    'volume_threshold': self.global_config.config.get('SURGE_VOLUME_THRESHOLD_MIDDAY', 3.0),
                    'global_sensitivity': self.global_config.config.get('SURGE_GLOBAL_SENSITIVITY_MIDDAY', 0.4),
                    'min_data_points': self.global_config.config.get('SURGE_MIN_DATA_POINTS_MIDDAY', 8),
                    'interval_seconds': self.global_config.config.get('SURGE_INTERVAL_SECONDS_MIDDAY', 20),
                    'price_threshold_percent': self.global_config.config.get('SURGE_PRICE_THRESHOLD_PERCENT_MIDDAY', 4.0)
                })
                
                # Update detection parameters
                config.detection_parameters.update({
                    'highlow': config.highlow_detection,
                    'trend': config.trend_detection,
                    'surge': config.surge_detection
                })
                
                logger.info(f"Integrated global config parameters for tick channel: {config.name}")
                
        except Exception as e:
            logger.warning(f"Failed to integrate global config: {e}")
    
    def save_configuration(self, config_name: str, config: ChannelConfig):
        """Save configuration to file"""
        config_file = self.config_dir / f"{config_name}.json"
        
        try:
            config.validate()
            
            config_dict = config.to_dict()
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            self.configurations[config_name] = config
            
            # Notify change callbacks
            for callback in self._change_callbacks:
                try:
                    callback(config_name, config)
                except Exception as e:
                    logger.error(f"Configuration change callback error: {e}", exc_info=True)
            
            logger.info(f"Saved configuration: {config_name}")
            
        except ConfigValidationError as e:
            raise ConfigValidationError(f"Cannot save invalid configuration: {e}")
    
    def update_configuration(self, config_name: str, updates: Dict[str, Any]) -> ChannelConfig:
        """Update existing configuration with new values"""
        if config_name not in self.configurations:
            raise ValueError(f"Configuration '{config_name}' not found")
        
        current_config = self.configurations[config_name]
        
        # Create updated configuration dictionary
        config_dict = current_config.to_dict()
        self._deep_update(config_dict, updates)
        
        # Determine channel type from current config
        if isinstance(current_config, TickChannelConfig):
            channel_type = 'tick'
        elif isinstance(current_config, OHLCVChannelConfig):
            channel_type = 'ohlcv'
        elif isinstance(current_config, FMVChannelConfig):
            channel_type = 'fmv'
        else:
            raise ValueError(f"Unknown configuration type: {type(current_config)}")
        
        # Create new configuration object
        updated_config = self.create_channel_config(channel_type, **config_dict)
        updated_config.validate()
        
        # Save the updated configuration
        self.save_configuration(config_name, updated_config)
        
        return updated_config
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Recursively update nested dictionary"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get_configuration(self, config_name: str) -> Optional[ChannelConfig]:
        """Get loaded configuration by name"""
        return self.configurations.get(config_name)
    
    def list_configurations(self) -> List[str]:
        """List all available configuration names"""
        config_files = self.config_dir.glob("*.json")
        return [f.stem for f in config_files]
    
    def register_change_callback(self, callback: Callable[[str, ChannelConfig], None]):
        """Register callback for configuration changes"""
        self._change_callbacks.append(callback)
    
    def validate_all_configurations(self) -> Dict[str, List[str]]:
        """Validate all loaded configurations and return any errors"""
        errors = {}
        
        for name, config in self.configurations.items():
            try:
                config.validate()
            except ConfigValidationError as e:
                errors[name] = [str(e)]
        
        return errors
    
    def load_from_environment(self, config_name: str, channel_type: str) -> ChannelConfig:
        """Load configuration with environment variable overrides"""
        
        # Load base configuration
        config = self.load_configuration(config_name, channel_type)
        
        # Apply environment overrides
        env_overrides = self._get_environment_overrides(channel_type)
        if env_overrides:
            config = self.update_configuration(config_name, env_overrides)
        
        return config
    
    def _get_environment_overrides(self, channel_type: str) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Common overrides for all channel types
        common_overrides = {
            'CHANNEL_METRICS_ENABLED': 'metrics_enabled',
            'CHANNEL_ERROR_THRESHOLD': 'error_threshold',
            'CHANNEL_MAX_QUEUE_SIZE': 'max_queue_size',
            'CHANNEL_PROCESSING_TIMEOUT_MS': 'processing_timeout_ms'
        }
        
        for env_var, config_path in common_overrides.items():
            if env_value := os.getenv(env_var):
                self._set_nested_config_value(overrides, config_path, env_value)
        
        # Channel-specific overrides
        if channel_type == 'tick':
            tick_overrides = {
                'TICK_CHANNEL_ENABLED': 'enabled',
                'HIGHLOW_DETECTION_ENABLED': 'highlow_detection.enabled',
                'TREND_DETECTION_ENABLED': 'trend_detection.enabled',
                'SURGE_DETECTION_ENABLED': 'surge_detection.enabled'
            }
            
            for env_var, config_path in tick_overrides.items():
                if env_value := os.getenv(env_var):
                    self._set_nested_config_value(overrides, config_path, env_value)
        
        return overrides
    
    def _set_nested_config_value(self, config_dict: Dict[str, Any], path: str, value: str):
        """Set nested configuration value from dotted path"""
        keys = path.split('.')
        current = config_dict
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set final value with type conversion
        final_key = keys[-1]
        
        # Convert string values to appropriate types
        if value.lower() in ('true', 'false'):
            current[final_key] = value.lower() == 'true'
        elif value.isdigit():
            current[final_key] = int(value)
        elif self._is_float(value):
            current[final_key] = float(value)
        else:
            current[final_key] = value
    
    def _is_float(self, value: str) -> bool:
        """Check if string represents a float"""
        try:
            float(value)
            return True
        except ValueError:
            return False