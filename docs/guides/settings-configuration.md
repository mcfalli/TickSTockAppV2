# TickStock Settings & Configuration System

Last edited: August 19, 2025 at 3:45 PM
Sprint: 101 - WebSocket Multi-Frequency

## Overview

This document defines the configuration system design for supporting multiple data frequencies in TickStock. The system builds upon the existing ConfigManager infrastructure while adding support for per-frequency settings, multiple concurrent data providers, and flexible subscription management.

## Current Configuration Architecture Analysis

### Existing ConfigManager Structure

```python
class ConfigManager:
    """Centralized configuration management with validation."""
    
    DEFAULTS = {
        'USE_POLYGON_API': False,
        'POLYGON_API_KEY': '',
        'POLYGON_WEBSOCKET_RECONNECT_DELAY': 5,
        'POLYGON_WEBSOCKET_MAX_RECONNECT_DELAY': 60,
        'USE_SYNTHETIC_DATA': False,
        'SIMULATOR_UNIVERSE': 'MARKET_CAP_LARGE_UNIVERSE',
        'SYNTHETIC_DATA_RATE': 0.1,
        'SYNTHETIC_ACTIVITY_LEVEL': 'medium',
        # ... extensive configuration options
    }
    
    CONFIG_TYPES = {
        'USE_POLYGON_API': bool,
        'POLYGON_API_KEY': str,
        'USE_SYNTHETIC_DATA': bool,
        # ... type validation
    }
```

**Current Configuration Features:**
- **Centralized defaults**: Single source of truth for configuration values
- **Type validation**: Automatic type conversion and validation
- **Environment loading**: .env file and environment variable support
- **Boolean parsing**: Flexible boolean value interpretation
- **List/dict parsing**: Complex data type support from environment strings
- **Configuration validation**: Cross-dependency validation and warnings

### Current Data Source Configuration

```python
# Current single-frequency configuration
'USE_POLYGON_API': False,           # Enable Polygon.io WebSocket
'USE_SYNTHETIC_DATA': False,        # Enable synthetic data generation
'SIMULATOR_UNIVERSE': 'MARKET_CAP_LARGE_UNIVERSE',  # Universe selection
'SYNTHETIC_DATA_RATE': 0.1,         # Events per ticker per update
'SYNTHETIC_ACTIVITY_LEVEL': 'medium', # Activity level for all tickers
```

**Current Limitations:**
- **Single frequency**: All subscriptions at same frequency (per-second default)
- **Binary provider selection**: Either Polygon OR synthetic, not both
- **Uniform configuration**: Same settings applied to all tickers
- **Static subscriptions**: Cannot change subscriptions at runtime

## Multi-Frequency Configuration Design

### New Environment Variables

#### High-Level Data Source Control
```bash
# Data source mode selection
DATA_SOURCE_MODE=production          # production, test, hybrid
ACTIVE_DATA_PROVIDERS=polygon,synthetic  # Comma-separated list of active providers

# Multi-frequency enablement
ENABLE_MULTI_FREQUENCY=true         # Enable multi-frequency processing
WEBSOCKET_SUBSCRIPTIONS_FILE=config/websocket_subscriptions.json
PROCESSING_CONFIG_FILE=config/processing_config.json
```

#### WebSocket Connection Configuration  
```bash
# Connection pool settings
WEBSOCKET_CONNECTION_POOL_SIZE=3    # Max concurrent WebSocket connections
WEBSOCKET_CONNECTION_TIMEOUT=15     # Connection timeout (seconds)
WEBSOCKET_SUBSCRIPTION_BATCH_SIZE=50 # Tickers per subscription request
WEBSOCKET_HEALTH_CHECK_INTERVAL=30  # Health check frequency (seconds)

# Per-frequency connection settings
WEBSOCKET_PER_SECOND_ENABLED=true   # Enable per-second connections
WEBSOCKET_PER_MINUTE_ENABLED=true   # Enable per-minute connections
WEBSOCKET_FAIR_VALUE_ENABLED=false  # Enable fair market value connections
```

#### Backward Compatibility Preservation
```bash
# Legacy variables - still supported
USE_POLYGON_API=true                # Maps to ACTIVE_DATA_PROVIDERS=polygon
USE_SYNTHETIC_DATA=false            # Maps to ACTIVE_DATA_PROVIDERS=synthetic  
POLYGON_API_KEY=your_key_here       # Still required for Polygon.io access
```

### JSON-Based WEBSOCKET_SUBSCRIPTIONS Configuration

#### Configuration File Structure
```json
{
  "version": "1.0",
  "default_provider": "polygon",
  "subscriptions": {
    "per_second": {
      "enabled": true,
      "provider": "polygon",
      "connection_id": "polygon_per_second",
      "subscription_format": "A.{ticker}",
      "tickers": [
        "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"
      ],
      "max_tickers": 1000,
      "priority": 1,
      "fallback_provider": "synthetic"
    },
    "per_minute": {
      "enabled": true,
      "provider": "polygon", 
      "connection_id": "polygon_per_minute",
      "subscription_format": "AM.{ticker}",
      "tickers": [
        "SPY", "QQQ", "IWM", "VTI", "BRK.B", "JPM", "BAC"
      ],
      "max_tickers": 2000,
      "priority": 2,
      "fallback_provider": "synthetic"
    },
    "fair_market_value": {
      "enabled": false,
      "provider": "polygon",
      "connection_id": "polygon_fair_value", 
      "subscription_format": "FMV.{ticker}",
      "tickers": [
        "BRK.A", "SPX", "NDX"
      ],
      "max_tickers": 100,
      "priority": 3,
      "fallback_provider": null
    },
    "synthetic_simulation": {
      "enabled": true,
      "provider": "synthetic",
      "connection_id": "synthetic_primary",
      "tickers": [
        "DEMO1", "DEMO2", "DEMO3", "TEST_TICKER"
      ],
      "activity_level": "high",
      "universe": "market_leaders:top_50",
      "rate": 0.5,
      "priority": 10
    }
  },
  "routing_rules": {
    "high_priority_tickers": {
      "tickers": ["AAPL", "TSLA", "NVDA"],
      "force_frequency": "per_second",
      "force_provider": "polygon"
    },
    "index_tickers": {
      "tickers": ["SPY", "QQQ", "IWM"],
      "preferred_frequency": "per_minute",
      "preferred_provider": "polygon"
    }
  }
}
```

#### Subscription Configuration Schema

**Per-Frequency Settings:**
- **enabled**: Boolean flag to enable/disable frequency
- **provider**: Primary data provider ("polygon", "synthetic", "simulated")
- **connection_id**: Unique identifier for connection instance
- **subscription_format**: Polygon.io subscription format string
- **tickers**: List of tickers for this frequency
- **max_tickers**: Maximum ticker limit per connection
- **priority**: Processing priority (lower = higher priority)
- **fallback_provider**: Provider to use if primary fails

**Routing Rules:**
- **ticker-specific routing**: Force specific tickers to specific frequencies
- **provider preferences**: Preferred providers per ticker group
- **priority overrides**: High-priority tickers get premium treatment

### PROCESSING_CONFIG Structure

#### Processing Behavior Configuration
```json
{
  "version": "1.0",
  "processing": {
    "batch_processing": {
      "enabled": true,
      "batch_size": 100,
      "max_batch_age_ms": 500,
      "per_frequency_batching": true
    },
    "parallel_streams": {
      "enabled": true,
      "max_concurrent_streams": 3,
      "stream_isolation": true,
      "cross_stream_deduplication": true
    },
    "event_routing": {
      "deduplicate_events": true,
      "event_priority_routing": true,
      "frequency_based_buffering": {
        "per_second": {"buffer_size": 1000, "max_age_ms": 1000},
        "per_minute": {"buffer_size": 500, "max_age_ms": 5000},
        "fair_market_value": {"buffer_size": 100, "max_age_ms": 30000}
      }
    },
    "failover": {
      "enabled": true,
      "failover_delay_ms": 5000,
      "max_failover_attempts": 3,
      "provider_health_check_interval": 30
    }
  },
  "performance": {
    "connection_pooling": {
      "max_connections_per_provider": 5,
      "connection_reuse": true,
      "idle_timeout_seconds": 300
    },
    "memory_management": {
      "max_memory_mb": 512,
      "gc_trigger_threshold": 0.8,
      "buffer_cleanup_interval": 60
    },
    "monitoring": {
      "latency_tracking": true,
      "throughput_monitoring": true,
      "error_rate_tracking": true,
      "metrics_export_interval": 30
    }
  }
}
```

**Processing Configuration Features:**
- **Batch processing**: Configurable batching per frequency
- **Parallel streams**: Multiple concurrent data streams with isolation
- **Event routing**: Intelligent routing and deduplication
- **Failover management**: Automatic provider failover with backoff
- **Performance tuning**: Connection pooling and memory management
- **Monitoring integration**: Comprehensive metrics collection

## Configuration Validation System

### Multi-Level Validation

#### Environment Variable Validation
```python
def validate_multi_frequency_config(self):
    """Validate multi-frequency configuration for consistency."""
    errors = []
    warnings = []
    
    # Validate data source mode
    valid_modes = ['production', 'test', 'hybrid']
    data_source_mode = self.config.get('DATA_SOURCE_MODE', 'production')
    if data_source_mode not in valid_modes:
        errors.append(f"Invalid DATA_SOURCE_MODE: {data_source_mode}. Must be one of {valid_modes}")
    
    # Validate active providers
    active_providers = self.config.get('ACTIVE_DATA_PROVIDERS', [])
    valid_providers = ['polygon', 'synthetic', 'simulated']
    invalid_providers = [p for p in active_providers if p not in valid_providers]
    if invalid_providers:
        errors.append(f"Invalid providers in ACTIVE_DATA_PROVIDERS: {invalid_providers}")
    
    # Polygon API key validation
    if 'polygon' in active_providers and not self.config.get('POLYGON_API_KEY'):
        errors.append("POLYGON_API_KEY required when 'polygon' is in ACTIVE_DATA_PROVIDERS")
    
    # Connection pool validation
    pool_size = self.config.get('WEBSOCKET_CONNECTION_POOL_SIZE', 3)
    if pool_size < 1 or pool_size > 10:
        warnings.append(f"WEBSOCKET_CONNECTION_POOL_SIZE ({pool_size}) outside recommended range 1-10")
    
    return errors, warnings
```

#### JSON Schema Validation
```python
def validate_websocket_subscriptions_schema(self, subscriptions_config):
    """Validate WebSocket subscriptions JSON configuration."""
    required_fields = ['version', 'subscriptions']
    errors = []
    
    # Check required top-level fields
    for field in required_fields:
        if field not in subscriptions_config:
            errors.append(f"Missing required field: {field}")
    
    # Validate subscription entries
    subscriptions = subscriptions_config.get('subscriptions', {})
    for freq_name, freq_config in subscriptions.items():
        # Required fields per subscription
        sub_required = ['enabled', 'provider', 'tickers']
        for field in sub_required:
            if field not in freq_config:
                errors.append(f"Subscription '{freq_name}' missing required field: {field}")
        
        # Provider validation
        provider = freq_config.get('provider')
        if provider not in ['polygon', 'synthetic', 'simulated']:
            errors.append(f"Subscription '{freq_name}' has invalid provider: {provider}")
        
        # Ticker validation
        tickers = freq_config.get('tickers', [])
        if not isinstance(tickers, list) or not tickers:
            errors.append(f"Subscription '{freq_name}' must have non-empty tickers list")
        
        # Max ticker validation
        max_tickers = freq_config.get('max_tickers', 1000)
        if len(tickers) > max_tickers:
            errors.append(f"Subscription '{freq_name}' has {len(tickers)} tickers, exceeds max_tickers {max_tickers}")
    
    return errors
```

### Configuration Conflict Resolution

#### Provider Priority Resolution
```python
def resolve_provider_conflicts(self, subscriptions_config):
    """Resolve conflicts when same ticker appears in multiple subscriptions."""
    ticker_assignments = {}
    conflicts = []
    
    # Build ticker assignment map with priorities
    for freq_name, freq_config in subscriptions_config.get('subscriptions', {}).items():
        if not freq_config.get('enabled', False):
            continue
            
        priority = freq_config.get('priority', 999)
        tickers = freq_config.get('tickers', [])
        
        for ticker in tickers:
            if ticker in ticker_assignments:
                # Conflict detected
                existing = ticker_assignments[ticker]
                if priority < existing['priority']:
                    # New assignment has higher priority
                    conflicts.append({
                        'ticker': ticker,
                        'old_frequency': existing['frequency'],
                        'new_frequency': freq_name,
                        'reason': 'priority_override'
                    })
                    ticker_assignments[ticker] = {
                        'frequency': freq_name,
                        'provider': freq_config['provider'],
                        'priority': priority
                    }
            else:
                ticker_assignments[ticker] = {
                    'frequency': freq_name,
                    'provider': freq_config['provider'],
                    'priority': priority
                }
    
    return ticker_assignments, conflicts
```

## Enhanced ConfigManager Implementation

### Extended ConfigManager Class

```python
class ConfigManager:
    """Enhanced configuration management with multi-frequency support."""
    
    # New configuration defaults for multi-frequency
    MULTI_FREQUENCY_DEFAULTS = {
        'DATA_SOURCE_MODE': 'production',
        'ACTIVE_DATA_PROVIDERS': ['polygon'],
        'ENABLE_MULTI_FREQUENCY': False,
        'WEBSOCKET_SUBSCRIPTIONS_FILE': 'config/websocket_subscriptions.json',
        'PROCESSING_CONFIG_FILE': 'config/processing_config.json',
        'WEBSOCKET_CONNECTION_POOL_SIZE': 3,
        'WEBSOCKET_CONNECTION_TIMEOUT': 15,
        'WEBSOCKET_SUBSCRIPTION_BATCH_SIZE': 50,
        'WEBSOCKET_HEALTH_CHECK_INTERVAL': 30,
        'WEBSOCKET_PER_SECOND_ENABLED': True,
        'WEBSOCKET_PER_MINUTE_ENABLED': False,
        'WEBSOCKET_FAIR_VALUE_ENABLED': False,
    }
    
    # Type definitions for new configuration options
    MULTI_FREQUENCY_TYPES = {
        'DATA_SOURCE_MODE': str,
        'ACTIVE_DATA_PROVIDERS': list,
        'ENABLE_MULTI_FREQUENCY': bool,
        'WEBSOCKET_SUBSCRIPTIONS_FILE': str,
        'PROCESSING_CONFIG_FILE': str,
        'WEBSOCKET_CONNECTION_POOL_SIZE': int,
        'WEBSOCKET_CONNECTION_TIMEOUT': int,
        'WEBSOCKET_SUBSCRIPTION_BATCH_SIZE': int,
        'WEBSOCKET_HEALTH_CHECK_INTERVAL': int,
        'WEBSOCKET_PER_SECOND_ENABLED': bool,
        'WEBSOCKET_PER_MINUTE_ENABLED': bool,
        'WEBSOCKET_FAIR_VALUE_ENABLED': bool,
    }
    
    def __init__(self):
        super().__init__()
        # Merge multi-frequency defaults and types
        self.DEFAULTS.update(self.MULTI_FREQUENCY_DEFAULTS)
        self.CONFIG_TYPES.update(self.MULTI_FREQUENCY_TYPES)
        
        # Initialize JSON configuration caches
        self._websocket_subscriptions = None
        self._processing_config = None
        self._last_config_load = None
    
    def load_json_configurations(self):
        """Load JSON configuration files with caching and validation."""
        current_time = time.time()
        
        # Check if reload is needed (cache for 60 seconds)
        if (self._last_config_load and 
            current_time - self._last_config_load < 60):
            return True
        
        try:
            # Load WebSocket subscriptions configuration
            subscriptions_file = self.config.get('WEBSOCKET_SUBSCRIPTIONS_FILE')
            if subscriptions_file and Path(subscriptions_file).exists():
                with open(subscriptions_file, 'r') as f:
                    self._websocket_subscriptions = json.load(f)
                
                # Validate subscriptions configuration
                errors = self.validate_websocket_subscriptions_schema(self._websocket_subscriptions)
                if errors:
                    logger.error(f"WebSocket subscriptions configuration errors: {errors}")
                    return False
            
            # Load processing configuration
            processing_file = self.config.get('PROCESSING_CONFIG_FILE')  
            if processing_file and Path(processing_file).exists():
                with open(processing_file, 'r') as f:
                    self._processing_config = json.load(f)
            
            self._last_config_load = current_time
            logger.info("JSON configurations loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading JSON configurations: {e}")
            return False
    
    def get_websocket_subscriptions(self):
        """Get WebSocket subscriptions configuration with lazy loading."""
        if self._websocket_subscriptions is None:
            self.load_json_configurations()
        return self._websocket_subscriptions or {}
    
    def get_processing_config(self):
        """Get processing configuration with lazy loading.""" 
        if self._processing_config is None:
            self.load_json_configurations()
        return self._processing_config or {}
```

### Environment Variable Interpolation

#### Dynamic Configuration Loading
```python
def load_config_with_interpolation(self, config_dict):
    """Load configuration with environment variable interpolation."""
    def interpolate_value(value):
        """Recursively interpolate environment variables in configuration values."""
        if isinstance(value, str):
            # Replace ${VAR} and ${VAR:default} patterns
            import re
            pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'
            
            def replace_var(match):
                var_name = match.group(1)
                default_value = match.group(2) or ''
                return os.environ.get(var_name, default_value)
            
            return re.sub(pattern, replace_var, value)
        elif isinstance(value, dict):
            return {k: interpolate_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [interpolate_value(item) for item in value]
        else:
            return value
    
    return interpolate_value(config_dict)
```

## Configuration Precedence Order

### Configuration Loading Priority

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **JSON configuration files**
4. **Default values** (lowest priority)

#### Implementation Example
```python
def resolve_configuration_precedence(self):
    """Resolve configuration values based on precedence order."""
    final_config = {}
    
    # 1. Start with defaults (lowest priority)
    final_config.update(self.DEFAULTS)
    
    # 2. Apply JSON configuration files
    json_config = self.get_json_configuration_values()
    final_config.update(json_config)
    
    # 3. Apply environment variables
    env_config = self.get_environment_configuration()
    final_config.update(env_config)
    
    # 4. Apply command-line arguments (highest priority)
    cli_config = self.get_cli_configuration()
    final_config.update(cli_config)
    
    self.config = final_config
    return final_config
```

## Backward Compatibility Maintenance

### Legacy Configuration Support

#### Automatic Migration Logic
```python
def migrate_legacy_configuration(self):
    """Automatically migrate legacy configuration to multi-frequency format."""
    migrations_applied = []
    
    # Migrate USE_POLYGON_API to ACTIVE_DATA_PROVIDERS
    if self.config.get('USE_POLYGON_API') and 'polygon' not in self.config.get('ACTIVE_DATA_PROVIDERS', []):
        providers = list(self.config.get('ACTIVE_DATA_PROVIDERS', []))
        providers.append('polygon')
        self.config['ACTIVE_DATA_PROVIDERS'] = providers
        migrations_applied.append('USE_POLYGON_API -> ACTIVE_DATA_PROVIDERS')
    
    # Migrate USE_SYNTHETIC_DATA to ACTIVE_DATA_PROVIDERS
    if self.config.get('USE_SYNTHETIC_DATA') and 'synthetic' not in self.config.get('ACTIVE_DATA_PROVIDERS', []):
        providers = list(self.config.get('ACTIVE_DATA_PROVIDERS', []))
        providers.append('synthetic')
        self.config['ACTIVE_DATA_PROVIDERS'] = providers
        migrations_applied.append('USE_SYNTHETIC_DATA -> ACTIVE_DATA_PROVIDERS')
    
    # Create default WebSocket subscriptions if multi-frequency is enabled but no config exists
    if (self.config.get('ENABLE_MULTI_FREQUENCY') and 
        not self._websocket_subscriptions):
        self._websocket_subscriptions = self._generate_default_subscriptions()
        migrations_applied.append('Generated default multi-frequency subscriptions')
    
    if migrations_applied:
        logger.info(f"Applied legacy configuration migrations: {migrations_applied}")
    
    return migrations_applied

def _generate_default_subscriptions(self):
    """Generate default WebSocket subscriptions configuration from legacy settings."""
    default_subscriptions = {
        "version": "1.0",
        "default_provider": "polygon" if self.config.get('USE_POLYGON_API') else "synthetic",
        "subscriptions": {}
    }
    
    # Create per-second subscription if Polygon is enabled
    if self.config.get('USE_POLYGON_API'):
        default_subscriptions["subscriptions"]["per_second"] = {
            "enabled": True,
            "provider": "polygon",
            "connection_id": "polygon_per_second",
            "subscription_format": "A.{ticker}",
            "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],  # Default high-profile tickers
            "max_tickers": 1000,
            "priority": 1
        }
    
    # Create synthetic subscription if synthetic is enabled  
    if self.config.get('USE_SYNTHETIC_DATA'):
        default_subscriptions["subscriptions"]["synthetic_simulation"] = {
            "enabled": True,
            "provider": "synthetic", 
            "connection_id": "synthetic_primary",
            "tickers": ["DEMO1", "DEMO2", "DEMO3"],
            "activity_level": self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium'),
            "universe": self.config.get('SIMULATOR_UNIVERSE', 'market_leaders:top_50'),
            "rate": self.config.get('SYNTHETIC_DATA_RATE', 0.1),
            "priority": 10
        }
    
    return default_subscriptions
```

### Compatibility Layer Implementation

#### Legacy API Preservation
```python
def get_legacy_config_value(self, key):
    """Get configuration value using legacy key names for backward compatibility.""" 
    legacy_mappings = {
        'USE_POLYGON_API': lambda: 'polygon' in self.config.get('ACTIVE_DATA_PROVIDERS', []),
        'USE_SYNTHETIC_DATA': lambda: 'synthetic' in self.config.get('ACTIVE_DATA_PROVIDERS', []),
        'POLYGON_SUBSCRIPTION_FORMAT': lambda: self._get_polygon_subscription_format(),
        'SYNTHETIC_TICKERS': lambda: self._get_synthetic_tickers()
    }
    
    if key in legacy_mappings:
        try:
            return legacy_mappings[key]()
        except Exception as e:
            logger.warning(f"Error resolving legacy config key {key}: {e}")
            return self.config.get(key)
    
    return self.config.get(key)
```

## Configuration Validation and Error Handling

### Comprehensive Validation Framework

#### Multi-Stage Validation Process
```python
def validate_complete_configuration(self):
    """Perform comprehensive validation of all configuration aspects."""
    validation_results = {
        'errors': [],
        'warnings': [],
        'info': [],
        'valid': True
    }
    
    # Stage 1: Environment variable validation
    env_errors, env_warnings = self.validate_multi_frequency_config()
    validation_results['errors'].extend(env_errors)
    validation_results['warnings'].extend(env_warnings)
    
    # Stage 2: JSON configuration validation
    if self.config.get('ENABLE_MULTI_FREQUENCY'):
        subscriptions = self.get_websocket_subscriptions()
        if subscriptions:
            json_errors = self.validate_websocket_subscriptions_schema(subscriptions)
            validation_results['errors'].extend(json_errors)
    
    # Stage 3: Cross-dependency validation
    cross_errors, cross_warnings = self.validate_cross_dependencies()
    validation_results['errors'].extend(cross_errors)
    validation_results['warnings'].extend(cross_warnings)
    
    # Stage 4: Resource validation
    resource_errors, resource_warnings = self.validate_resource_limits()
    validation_results['errors'].extend(resource_errors)
    validation_results['warnings'].extend(resource_warnings)
    
    validation_results['valid'] = len(validation_results['errors']) == 0
    
    # Log validation results
    if validation_results['errors']:
        logger.error(f"Configuration validation failed with {len(validation_results['errors'])} errors")
        for error in validation_results['errors']:
            logger.error(f"  ERROR: {error}")
    
    if validation_results['warnings']:
        logger.warning(f"Configuration validation completed with {len(validation_results['warnings'])} warnings")
        for warning in validation_results['warnings']:
            logger.warning(f"  WARNING: {warning}")
    
    return validation_results
```

#### Error Recovery and Fallback Strategies
```python
def apply_configuration_fallbacks(self, validation_results):
    """Apply fallback configuration for recoverable errors."""
    fallbacks_applied = []
    
    for error in validation_results['errors']:
        if 'POLYGON_API_KEY required' in error:
            # Fallback to synthetic data if Polygon API key missing
            providers = [p for p in self.config.get('ACTIVE_DATA_PROVIDERS', []) if p != 'polygon']
            if 'synthetic' not in providers:
                providers.append('synthetic')
            self.config['ACTIVE_DATA_PROVIDERS'] = providers
            fallbacks_applied.append('Switched to synthetic data due to missing Polygon API key')
        
        elif 'Invalid providers' in error:
            # Fallback to simulated provider for invalid providers
            self.config['ACTIVE_DATA_PROVIDERS'] = ['simulated']
            fallbacks_applied.append('Switched to simulated provider due to invalid provider configuration')
    
    if fallbacks_applied:
        logger.info(f"Applied configuration fallbacks: {fallbacks_applied}")
    
    return fallbacks_applied
```

## Configuration Hot-Reloading Support

### Runtime Configuration Updates

#### File Watching and Automatic Reload
```python
def setup_configuration_file_watching(self):
    """Set up file system watching for configuration changes.""" 
    import threading
    from pathlib import Path
    import time
    
    def watch_config_files():
        """Background thread to monitor configuration file changes."""
        config_files = [
            self.config.get('WEBSOCKET_SUBSCRIPTIONS_FILE'),
            self.config.get('PROCESSING_CONFIG_FILE')
        ]
        
        file_timestamps = {}
        
        while True:
            try:
                for file_path in config_files:
                    if file_path and Path(file_path).exists():
                        current_mtime = Path(file_path).stat().st_mtime
                        
                        if file_path not in file_timestamps:
                            file_timestamps[file_path] = current_mtime
                        elif current_mtime > file_timestamps[file_path]:
                            logger.info(f"Configuration file changed: {file_path}")
                            self.reload_json_configurations()
                            file_timestamps[file_path] = current_mtime
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in configuration file watching: {e}")
                time.sleep(30)  # Wait longer on error
    
    # Start file watcher thread
    watcher_thread = threading.Thread(target=watch_config_files, daemon=True)
    watcher_thread.start()
    logger.info("Configuration file watching enabled")
```

#### Safe Configuration Hot-Reload
```python
def reload_json_configurations(self):
    """Safely reload JSON configurations with validation."""
    try:
        # Store current configuration as backup
        backup_subscriptions = self._websocket_subscriptions
        backup_processing = self._processing_config
        
        # Clear cache to force reload
        self._websocket_subscriptions = None
        self._processing_config = None
        self._last_config_load = None
        
        # Attempt to load new configurations
        if self.load_json_configurations():
            # Validate new configuration
            validation_result = self.validate_complete_configuration()
            
            if validation_result['valid']:
                logger.info("Configuration hot-reload successful")
                # Notify application components of configuration change
                self._notify_configuration_change()
                return True
            else:
                logger.error("Configuration hot-reload failed validation, reverting to backup")
                self._websocket_subscriptions = backup_subscriptions
                self._processing_config = backup_processing
                return False
        else:
            logger.error("Configuration hot-reload failed to load files, reverting to backup")
            self._websocket_subscriptions = backup_subscriptions
            self._processing_config = backup_processing
            return False
            
    except Exception as e:
        logger.error(f"Error during configuration hot-reload: {e}")
        return False
```

## Summary

The Multi-Frequency Configuration System provides:

- **Backward Compatibility**: Existing single-frequency configurations continue to work
- **Flexible Provider Support**: Multiple concurrent data providers (Polygon, synthetic, simulated)
- **Per-Frequency Configuration**: Different settings for different data frequencies
- **JSON-Based Complex Configuration**: Rich subscription and processing configuration via JSON files
- **Comprehensive Validation**: Multi-stage validation with clear error messages and fallback strategies
- **Environment Variable Interpolation**: Dynamic configuration with environment variable substitution
- **Hot-Reload Support**: Runtime configuration updates without application restart
- **Configuration Precedence**: Clear priority order for configuration sources
- **Migration Support**: Automatic migration from legacy single-frequency configuration

The system maintains full backward compatibility while enabling sophisticated multi-frequency data processing capabilities required for Sprint 101 and beyond.