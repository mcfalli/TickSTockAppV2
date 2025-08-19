# Migration Guide: Single-Frequency to Multi-Frequency Configuration

## Overview

This guide helps migrate existing TickStock deployments from single-frequency data processing to the new multi-frequency configuration system. The migration maintains full backward compatibility while enabling advanced multi-frequency capabilities.

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

#### Phase 1: Enable Multi-Frequency Without Changes
```bash
# Add to existing .env file - all existing behavior preserved
ENABLE_MULTI_FREQUENCY=false  # Keep disabled initially
DATA_SOURCE_MODE=production
ACTIVE_DATA_PROVIDERS=${USE_POLYGON_API:+polygon}${USE_SYNTHETIC_DATA:+,synthetic}
```

#### Phase 2: Create Default Configuration Files
```bash
# Create default configuration files
mkdir -p config
cp docs/examples/websocket_subscriptions_default.json config/websocket_subscriptions.json
cp docs/examples/processing_config_default.json config/processing_config.json
```

#### Phase 3: Enable Multi-Frequency Mode
```bash
# Update .env file
ENABLE_MULTI_FREQUENCY=true

# Existing variables still work (backward compatibility)
# USE_POLYGON_API=true              # Automatically mapped to ACTIVE_DATA_PROVIDERS
# USE_SYNTHETIC_DATA=false          # Automatically mapped to ACTIVE_DATA_PROVIDERS
# POLYGON_API_KEY=your_key_here     # Still required for Polygon.io
```

### Strategy 2: Full Migration (Advanced)

#### Environment Variable Migration
```bash
# Old single-frequency configuration
USE_POLYGON_API=true
USE_SYNTHETIC_DATA=false
POLYGON_API_KEY=your_key_here
SYNTHETIC_DATA_RATE=0.1
SYNTHETIC_ACTIVITY_LEVEL=medium

# New multi-frequency configuration
ENABLE_MULTI_FREQUENCY=true
DATA_SOURCE_MODE=production
ACTIVE_DATA_PROVIDERS=polygon,synthetic
POLYGON_API_KEY=your_key_here

# WebSocket connection settings
WEBSOCKET_CONNECTION_POOL_SIZE=3
WEBSOCKET_CONNECTION_TIMEOUT=15
WEBSOCKET_PER_SECOND_ENABLED=true
WEBSOCKET_PER_MINUTE_ENABLED=true
```

## Configuration File Examples

### Minimal WebSocket Subscriptions Configuration
```json
{
  "version": "1.0",
  "default_provider": "polygon",
  "subscriptions": {
    "per_second": {
      "enabled": true,
      "provider": "polygon",
      "connection_id": "polygon_primary",
      "subscription_format": "A.{ticker}",
      "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA"],
      "max_tickers": 1000,
      "priority": 1
    }
  }
}
```

### Complete WebSocket Subscriptions Configuration
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
      "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"],
      "max_tickers": 1000,
      "priority": 1,
      "fallback_provider": "synthetic"
    },
    "per_minute": {
      "enabled": true,
      "provider": "polygon",
      "connection_id": "polygon_per_minute", 
      "subscription_format": "AM.{ticker}",
      "tickers": ["SPY", "QQQ", "IWM"],
      "max_tickers": 2000,
      "priority": 2,
      "fallback_provider": "synthetic"
    },
    "synthetic_test": {
      "enabled": true,
      "provider": "synthetic",
      "connection_id": "synthetic_primary",
      "tickers": ["DEMO1", "DEMO2", "DEMO3"],
      "activity_level": "medium",
      "universe": "market_leaders:top_50",
      "rate": 0.5,
      "priority": 10
    }
  },
  "routing_rules": {
    "high_priority": {
      "tickers": ["AAPL", "TSLA"],
      "force_frequency": "per_second",
      "force_provider": "polygon"
    }
  }
}
```

### Processing Configuration
```json
{
  "version": "1.0",
  "processing": {
    "batch_processing": {
      "enabled": true,
      "batch_size": 100,
      "max_batch_age_ms": 500
    },
    "parallel_streams": {
      "enabled": true,
      "max_concurrent_streams": 3,
      "stream_isolation": true
    },
    "event_routing": {
      "deduplicate_events": true,
      "frequency_based_buffering": {
        "per_second": {"buffer_size": 1000, "max_age_ms": 1000},
        "per_minute": {"buffer_size": 500, "max_age_ms": 5000}
      }
    }
  }
}
```

## Migration Testing

### Pre-Migration Validation
```bash
# Test current configuration
python -m src.core.services.config_manager --validate

# Check data provider availability
python -c "
from src.infrastructure.data_sources.factory import DataProviderFactory
from src.core.services.config_manager import get_config
config = get_config()
validation = DataProviderFactory.validate_provider_configuration(config)
print('Validation Result:', validation)
"
```

### Post-Migration Verification
```bash
# Verify multi-frequency configuration loading
python -c "
from src.core.services.config_manager import ConfigManager
cm = ConfigManager()
cm.load_from_env()
cm.load_json_configurations()
print('WebSocket Config:', cm.get_websocket_subscriptions())
print('Processing Config:', cm.get_processing_config())
"

# Test provider selection
python -c "
from src.infrastructure.data_sources.factory import DataProviderFactory
from src.core.services.config_manager import get_config
config = get_config()
provider = DataProviderFactory.get_provider(config)
print('Selected Provider:', type(provider).__name__)
"
```

## Backward Compatibility Matrix

| Legacy Configuration | Multi-Frequency Equivalent | Auto-Migration |
|---------------------|----------------------------|----------------|
| `USE_POLYGON_API=true` | `ACTIVE_DATA_PROVIDERS=polygon` | ✅ Yes |
| `USE_SYNTHETIC_DATA=true` | `ACTIVE_DATA_PROVIDERS=synthetic` | ✅ Yes |
| `POLYGON_API_KEY=key` | `POLYGON_API_KEY=key` | ✅ Unchanged |
| `SYNTHETIC_DATA_RATE=0.1` | JSON config `"rate": 0.1` | ⚠️ Manual |
| `SYNTHETIC_ACTIVITY_LEVEL=medium` | JSON config `"activity_level": "medium"` | ⚠️ Manual |

### Legacy Configuration Support

The system maintains full support for legacy configuration variables:

```bash
# These continue to work exactly as before
USE_POLYGON_API=true
USE_SYNTHETIC_DATA=false
POLYGON_API_KEY=your_key_here
SYNTHETIC_DATA_RATE=0.5
SYNTHETIC_ACTIVITY_LEVEL=high
```

## Common Migration Issues and Solutions

### Issue 1: Missing JSON Configuration Files
**Problem**: `ENABLE_MULTI_FREQUENCY=true` but no JSON files found.

**Solution**: 
```bash
# System auto-generates default configuration
# Or manually create minimal files:
mkdir -p config
echo '{"version":"1.0","subscriptions":{}}' > config/websocket_subscriptions.json
echo '{"version":"1.0","processing":{}}' > config/processing_config.json
```

### Issue 2: Provider Configuration Conflicts
**Problem**: Both legacy and new configuration specify providers.

**Solution**:
```bash
# Migration priority: ACTIVE_DATA_PROVIDERS takes precedence
# Remove legacy variables after migration:
# USE_POLYGON_API=    # Remove or comment out
# USE_SYNTHETIC_DATA= # Remove or comment out

# Use only new format:
ACTIVE_DATA_PROVIDERS=polygon,synthetic
```

### Issue 3: API Key Not Found
**Problem**: `POLYGON_API_KEY required when 'polygon' is in ACTIVE_DATA_PROVIDERS`

**Solution**:
```bash
# Ensure API key is set
POLYGON_API_KEY=your_actual_api_key_here

# Or use environment variable interpolation in JSON:
# "${POLYGON_API_KEY}"
```

### Issue 4: Invalid Provider Names
**Problem**: `Invalid providers in ACTIVE_DATA_PROVIDERS`

**Solution**:
```bash
# Valid provider names only:
ACTIVE_DATA_PROVIDERS=polygon,synthetic,simulated

# Fix typos:
# polygon (not polygonio)
# synthetic (not synthetic_data)
# simulated (not simulator)
```

## Performance Considerations

### Resource Usage Changes

#### Before Migration (Single-Frequency)
- **WebSocket connections**: 1 connection maximum
- **Memory usage**: ~50-100MB for data processing
- **CPU usage**: Single-threaded event processing
- **Ticker limits**: 3000 tickers per connection

#### After Migration (Multi-Frequency)
- **WebSocket connections**: Up to 3-5 concurrent connections
- **Memory usage**: ~100-200MB for multi-stream processing  
- **CPU usage**: Multi-threaded with parallel stream processing
- **Ticker limits**: 3000 tickers per frequency/connection

### Optimization Recommendations

#### For Low-Resource Environments
```json
{
  "processing": {
    "parallel_streams": {
      "enabled": false,
      "max_concurrent_streams": 1
    },
    "batch_processing": {
      "batch_size": 50,
      "max_batch_age_ms": 1000
    }
  },
  "performance": {
    "memory_management": {
      "max_memory_mb": 256,
      "gc_trigger_threshold": 0.7
    }
  }
}
```

#### For High-Performance Environments
```json
{
  "processing": {
    "parallel_streams": {
      "enabled": true,
      "max_concurrent_streams": 5
    },
    "batch_processing": {
      "batch_size": 200,
      "max_batch_age_ms": 250
    }
  },
  "performance": {
    "memory_management": {
      "max_memory_mb": 1024,
      "gc_trigger_threshold": 0.9
    }
  }
}
```

## Testing Strategy

### Unit Testing Migration
```python
# Test configuration migration
def test_legacy_configuration_migration():
    config = {
        'USE_POLYGON_API': True,
        'USE_SYNTHETIC_DATA': False,
        'POLYGON_API_KEY': 'test_key'
    }
    
    cm = ConfigManager()
    cm.config = config
    cm._migrate_legacy_configuration()
    
    assert 'polygon' in cm.config['ACTIVE_DATA_PROVIDERS']
    assert 'synthetic' not in cm.config['ACTIVE_DATA_PROVIDERS']

# Test provider selection
def test_provider_selection_compatibility():
    legacy_config = {'USE_POLYGON_API': True, 'POLYGON_API_KEY': 'test'}
    modern_config = {'ACTIVE_DATA_PROVIDERS': ['polygon'], 'POLYGON_API_KEY': 'test'}
    
    legacy_provider = DataProviderFactory.get_provider(legacy_config)
    modern_provider = DataProviderFactory.get_provider(modern_config)
    
    assert type(legacy_provider) == type(modern_provider)
```

### Integration Testing
```bash
# Test full application startup with migrated configuration
python -m src.app --config-validate-only

# Test data flow with both configurations
python -m tests.integration.test_data_flow --legacy-config
python -m tests.integration.test_data_flow --multi-frequency-config
```

## Rollback Strategy

### Emergency Rollback
```bash
# Disable multi-frequency mode immediately
ENABLE_MULTI_FREQUENCY=false

# Revert to legacy configuration
USE_POLYGON_API=true
USE_SYNTHETIC_DATA=false
POLYGON_API_KEY=your_key_here

# Remove new configuration files (optional)
rm -f config/websocket_subscriptions.json
rm -f config/processing_config.json
```

### Gradual Rollback
```bash
# Step 1: Disable new features
WEBSOCKET_PER_MINUTE_ENABLED=false
WEBSOCKET_FAIR_VALUE_ENABLED=false

# Step 2: Simplify configuration
# Edit config/websocket_subscriptions.json to only include per_second

# Step 3: Eventually disable multi-frequency
ENABLE_MULTI_FREQUENCY=false
```

## Support and Troubleshooting

### Configuration Validation Tool
```bash
# Use built-in validation
python -c "
from src.core.services.config_manager import ConfigManager
cm = ConfigManager()
cm.load_from_env()
if cm.validate_config():
    print('✅ Configuration valid')
else:
    print('❌ Configuration invalid')
"
```

### Debug Configuration Loading
```bash
# Enable debug logging for configuration
LOG_CONSOLE_DEBUG=true
LOG_CONSOLE_VERBOSE=true
python -m src.core.services.config_manager
```

### Common Debug Commands
```bash
# Check active providers
python -c "from src.core.services.config_manager import get_config; print(get_config().get('ACTIVE_DATA_PROVIDERS'))"

# Check WebSocket subscriptions
python -c "from src.core.services.config_manager import get_config; cm = get_config(); print(cm.get_websocket_subscriptions() if hasattr(cm, 'get_websocket_subscriptions') else 'Not available')"

# Test provider creation
python -c "from src.infrastructure.data_sources.factory import DataProviderFactory; from src.core.services.config_manager import get_config; print(type(DataProviderFactory.get_provider(get_config())).__name__)"
```

## Migration Checklist

### Pre-Migration
- [ ] Backup existing `.env` file
- [ ] Document current configuration settings
- [ ] Test current system functionality
- [ ] Verify data provider connectivity
- [ ] Record performance baseline metrics

### Migration Execution
- [ ] Add new environment variables
- [ ] Create JSON configuration files
- [ ] Enable multi-frequency mode
- [ ] Validate configuration loading
- [ ] Test provider selection
- [ ] Verify data flow functionality

### Post-Migration Validation
- [ ] Confirm all providers initialize successfully
- [ ] Verify event processing continues normally
- [ ] Check WebSocket connection stability
- [ ] Monitor resource usage changes
- [ ] Test failover scenarios
- [ ] Validate configuration hot-reload (if enabled)

### Cleanup (Optional)
- [ ] Remove commented legacy environment variables
- [ ] Archive old configuration backups
- [ ] Update deployment documentation
- [ ] Train team on new configuration system

## Summary

The migration to multi-frequency configuration is designed to be seamless and risk-free:

1. **Full Backward Compatibility**: Existing configurations continue to work without changes
2. **Gradual Migration**: Can be enabled incrementally with fallback options
3. **Automatic Migration**: Legacy settings automatically converted to new format
4. **Zero Downtime**: Migration can be performed without service interruption
5. **Easy Rollback**: Complete rollback possible at any time

The new system provides enhanced flexibility for multi-frequency data processing while maintaining the simplicity and reliability of the original single-frequency configuration.