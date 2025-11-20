# TickStockAppV2 Configuration Management

**Date**: 2025-09-26
**Sprint**: 36 Configuration Consolidation
**Purpose**: Centralized configuration management using config_manager service

## Overview

TickStockAppV2 uses a centralized configuration management system via `src/core/services/config_manager.py` that provides:

- Single source of truth for all configuration parameters
- Environment variable loading with type validation
- Default value management
- Backward compatibility with legacy configurations
- Multi-frequency synthetic data configuration support

## Configuration Architecture

### Core Components

**ConfigManager Class**: Primary configuration management service
- Loads defaults from `DEFAULTS` dictionary
- Reads environment variables from `.env` file
- Validates configuration types and consistency
- Provides legacy compatibility functions

**Global Access Function**: `get_config()` provides backward compatibility
- Returns global ConfigManager instance
- Automatically loads environment configuration on first call
- Thread-safe singleton pattern

### Configuration Categories

## Application Core Settings

### Basic Application Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `APP_VERSION` | str | '' | Application version string |
| `APP_ENVIRONMENT` | str | 'development' | Runtime environment (development/production) |
| `APP_DEBUG` | bool | False | Flask debug mode |
| `APP_HOST` | str | '0.0.0.0' | Flask application host |
| `APP_PORT` | int | 5000 | Flask application port |
| `MARKET_TIMEZONE` | str | 'US/Eastern' | Market timezone for operations |

### Database Configuration

#### Primary Database (MarketPulse)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `DATABASE_URI` | str | postgresql://app_readwrite:1DfTGVBsECVtJa@localhost/marketpulse | Primary database connection |
| `DATABASE_SYNCH_AGGREGATE_SECONDS` | int | 30 | Database sync interval |

#### TickStock Database (TimescaleDB)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TICKSTOCK_DB_HOST` | str | 'localhost' | TickStock database host |
| `TICKSTOCK_DB_PORT` | int | 5432 | TickStock database port |
| `TICKSTOCK_DB_NAME` | str | 'tickstock' | TickStock database name |
| `TICKSTOCK_DB_USER` | str | 'app_readwrite' | TickStock database user |
| `TICKSTOCK_DB_PASSWORD` | str | 'LJI48rUEkUpe6e' | TickStock database password |

## Integration Configuration

### Redis Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `REDIS_URL` | str | '' | Complete Redis connection URL (if provided) |
| `REDIS_HOST` | str | 'localhost' | Redis server host |
| `REDIS_PORT` | int | 6379 | Redis server port |
| `REDIS_DB` | int | 0 | Redis database number |

### Sprint 36: TickStockPL API Integration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TICKSTOCKPL_HOST` | str | 'localhost' | TickStockPL service host |
| `TICKSTOCKPL_PORT` | int | 8080 | TickStockPL service port |
| `TICKSTOCKPL_API_KEY` | str | 'tickstock-cache-sync-2025' | API key for TickStockPL authentication |

### Data Provider Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `USE_MASSIVE_API` | bool | False | Enable Massive.com data provider |
| `MASSIVE_API_KEY` | str | '' | Massive.com API key |
| `MASSIVE_WEBSOCKET_RECONNECT_DELAY` | int | 5 | Reconnection delay (seconds) |
| `MASSIVE_WEBSOCKET_MAX_RECONNECT_DELAY` | int | 60 | Maximum reconnection delay |
| `MASSIVE_WEBSOCKET_MAX_RETRIES` | int | 5 | Maximum retry attempts |

## Processing Configuration

### Real-Time Processing
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `UPDATE_INTERVAL` | float | 0.5 | Core update interval (seconds) |
| `COLLECTION_INTERVAL` | float | 0.5 | DataPublisher collection rate |
| `EMISSION_INTERVAL` | float | 1.0 | WebSocketPublisher emission rate |
| `HEARTBEAT_INTERVAL` | float | 2.0 | System heartbeat interval |

### Worker Pool Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `WORKER_POOL_SIZE` | int | 12 | Default worker pool size |
| `MIN_WORKER_POOL_SIZE` | int | 8 | Minimum workers |
| `MAX_WORKER_POOL_SIZE` | int | 16 | Maximum workers |
| `WORKER_EVENT_BATCH_SIZE` | int | 1000 | Events per worker batch |
| `WORKER_COLLECTION_TIMEOUT` | float | 0.5 | Worker collection timeout |

### Queue Management
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MAX_QUEUE_SIZE` | int | 100000 | Maximum queue size |
| `QUEUE_OVERFLOW_DROP_THRESHOLD` | float | 0.98 | Queue overflow threshold |
| `EVENT_BATCH_SIZE` | int | 500 | Event processing batch size |
| `MAX_EVENT_AGE_MS` | int | 120000 | Maximum event age (milliseconds) |
| `COLLECTION_MAX_EVENTS` | int | 1000 | Maximum events per collection |
| `COLLECTION_TIMEOUT` | float | 0.5 | Collection timeout |

### Data Publishing
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MAX_EVENTS_PER_PUBLISH` | int | 100 | Events per publish cycle |
| `PUBLISH_BATCH_SIZE` | int | 30 | Publish batch size |
| `ENABLE_LEGACY_FALLBACK` | bool | True | Enable legacy processing fallback |
| `DATA_PUBLISHER_DEBUG_MODE` | bool | True | Debug mode for data publisher |

## Synthetic Data Configuration

### Multi-Frequency Generation
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `USE_SYNTHETIC_DATA` | bool | False | Enable synthetic data generation |
| `ENABLE_MULTI_FREQUENCY` | bool | False | Enable multi-frequency synthetic data |
| `WEBSOCKET_PER_SECOND_ENABLED` | bool | True | Enable per-second data stream |
| `WEBSOCKET_PER_MINUTE_ENABLED` | bool | False | Enable per-minute data stream |
| `WEBSOCKET_FAIR_VALUE_ENABLED` | bool | False | Enable fair market value stream |

### Synthetic Data Validation
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ENABLE_SYNTHETIC_DATA_VALIDATION` | bool | True | Enable data validation |
| `VALIDATION_PRICE_TOLERANCE` | float | 0.001 | Price validation tolerance (0.1%) |
| `VALIDATION_VOLUME_TOLERANCE` | float | 0.05 | Volume validation tolerance (5%) |
| `VALIDATION_VWAP_TOLERANCE` | float | 0.002 | VWAP validation tolerance (0.2%) |

### Per-Second Generator Settings
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SYNTHETIC_TICK_VARIANCE` | float | 0.001 | Tick price variance (0.1%) |
| `SYNTHETIC_VOLUME_MULTIPLIER` | float | 1.0 | Volume scaling multiplier |
| `SYNTHETIC_VWAP_VARIANCE` | float | 0.002 | VWAP variance (0.2%) |
| `SYNTHETIC_ACTIVITY_LEVEL` | str | 'medium' | Activity level (low/medium/high/opening_bell) |

### Fair Market Value Settings
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SYNTHETIC_FMV_UPDATE_INTERVAL` | int | 30 | FMV update interval (seconds) |
| `SYNTHETIC_FMV_CORRELATION` | float | 0.85 | Base correlation strength |
| `SYNTHETIC_FMV_VARIANCE` | float | 0.002 | FMV variance (0.2%) |
| `SYNTHETIC_FMV_PREMIUM_RANGE` | float | 0.01 | Premium/discount range (1%) |
| `SYNTHETIC_FMV_MOMENTUM_DECAY` | float | 0.7 | Momentum persistence factor |
| `SYNTHETIC_FMV_LAG_FACTOR` | float | 0.3 | FMV lag response factor |
| `SYNTHETIC_FMV_VOLATILITY_DAMPENING` | float | 0.6 | Volatility reduction factor |

### Market Regime Correlations
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SYNTHETIC_FMV_TRENDING_CORRELATION` | float | 0.90 | Correlation during trending markets |
| `SYNTHETIC_FMV_SIDEWAYS_CORRELATION` | float | 0.75 | Correlation during sideways markets |
| `SYNTHETIC_FMV_VOLATILE_CORRELATION` | float | 0.65 | Correlation during volatile markets |

## Logging and Error Management

### Sprint 32: Enhanced Error Management
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LOG_FILE_ENABLED` | bool | False | Enable file logging |
| `LOG_FILE_PATH` | str | 'logs/tickstock.log' | Log file path |
| `LOG_FILE_MAX_SIZE` | int | 10485760 | Max log file size (10MB) |
| `LOG_FILE_BACKUP_COUNT` | int | 5 | Number of backup log files |
| `LOG_DB_ENABLED` | bool | False | Enable database logging |
| `LOG_DB_SEVERITY_THRESHOLD` | str | 'error' | Minimum severity for DB logging |
| `REDIS_ERROR_CHANNEL` | str | 'tickstock:errors' | Redis channel for error events |

### Console Logging
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LOG_CONSOLE_VERBOSE` | bool | False | Verbose console logging |
| `LOG_CONSOLE_DEBUG` | bool | False | Debug console logging |
| `LOG_CONSOLE_CONNECTION_VERBOSE` | bool | True | Verbose connection logging |
| `LOG_FILE_PRODUCTION_MODE` | bool | False | Production logging mode |

### Integration Logging
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `INTEGRATION_LOGGING_ENABLED` | bool | True | Enable integration logging |
| `INTEGRATION_LOG_FILE` | bool | False | File logging for integrations |
| `INTEGRATION_LOG_LEVEL` | str | 'INFO' | Integration log level |

## Security Configuration

### Session Management
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `FLASK_SECRET_KEY` | str | Generated | Flask session secret key |
| `MAX_SESSIONS_PER_USER` | int | 1 | Maximum sessions per user |
| `SESSION_EXPIRY_DAYS` | int | 1 | Session expiration (days) |

### Authentication Security
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LOCKOUT_DURATION_MINUTES` | int | 20 | Account lockout duration |
| `MAX_LOCKOUTS` | int | 3 | Maximum lockout attempts |
| `CAPTCHA_ENABLED` | bool | True | Enable CAPTCHA protection |
| `COMMON_PASSWORDS` | str | 'password,password123,12345678,qwerty' | Common passwords to reject |

### Email Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `EMAIL_VERIFICATION_SALT` | str | 'email-verification' | Salt for email verification |
| `PASSWORD_RESET_SALT` | str | 'password-reset' | Salt for password reset |
| `SUPPORT_EMAIL` | str | 'support@tickstock.com' | Support email address |

### SMS Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SMS_TEST_MODE` | bool | True | Enable SMS test mode |
| `TWILIO_ACCOUNT_SID` | str | '' | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | str | '' | Twilio authentication token |
| `TWILIO_PHONE_NUMBER` | str | '+15551234567' | Twilio phone number |
| `SMS_VERIFICATION_CODE_LENGTH` | int | 6 | SMS verification code length |
| `SMS_VERIFICATION_CODE_EXPIRY` | int | 10 | SMS code expiry (minutes) |

## Performance and Data Configuration

### API Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `API_CACHE_TTL` | int | 60 | API cache time-to-live (seconds) |
| `API_MIN_REQUEST_INTERVAL` | float | 0.05 | Minimum request interval |
| `API_BATCH_SIZE` | int | 25 | API batch processing size |

### Market Data Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SEED_FROM_RECENT_CANDLE` | bool | False | Initialize from recent candle data |
| `SYNTHETIC_DATA_RATE` | float | 0.1 | Synthetic data generation rate |
| `SYNTHETIC_DATA_VARIANCE` | float | 0.05 | Synthetic data variance |

### Symbol Universe Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SYMBOL_UNIVERSE_KEY` | str | 'stock_etf_test:combo_test' | Default universe key for WebSocket subscriptions |
| `SIMULATOR_UNIVERSE` | str | 'MARKET_CAP_LARGE_UNIVERSE' | Universe for synthetic data |

### Momentum and Flow Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MOMENTUM_WINDOW_SECONDS` | float | 5 | Momentum calculation window |
| `MOMENTUM_MAX_THRESHOLD` | int | 15 | Maximum momentum threshold |
| `FLOW_WINDOW_SECONDS` | float | 30 | Flow calculation window |
| `FLOW_MAX_THRESHOLD` | int | 40 | Maximum flow threshold |
| `FLOW_DECAY_FACTOR` | float | 0.95 | Flow decay factor |

## WebSocket and Multi-Frequency Configuration

### Connection Management
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `WEBSOCKET_CONNECTION_POOL_SIZE` | int | 3 | WebSocket connection pool size |
| `WEBSOCKET_CONNECTION_TIMEOUT` | int | 15 | Connection timeout (seconds) |
| `WEBSOCKET_SUBSCRIPTION_BATCH_SIZE` | int | 50 | Subscription batch size |
| `WEBSOCKET_HEALTH_CHECK_INTERVAL` | int | 30 | Health check interval (seconds) |

### Data Source Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `DATA_SOURCE_MODE` | str | 'production' | Data source mode (production/test/hybrid) |
| `ACTIVE_DATA_PROVIDERS` | list | ['massive'] | Active data providers |

### Configuration Files
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `WEBSOCKET_SUBSCRIPTIONS_FILE` | str | 'config/websocket_subscriptions.json' | WebSocket subscriptions configuration |
| `PROCESSING_CONFIG_FILE` | str | 'config/processing_config.json' | Processing configuration file |

## Migration and Validation

### Data Migration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MIGRATION_VALIDATION` | bool | True | Enable migration validation |
| `MIGRATION_PARALLEL_PROCESSING` | bool | False | Enable parallel migration processing |

### Event Processing
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `EVENT_RATE_LIMIT` | float | 0.1 | Event processing rate limit |
| `STOCK_DETAILS_MAX_AGE` | int | 3600 | Stock details cache max age (seconds) |

### Performance Monitoring
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `DATA_PUBLISHER_STATS_INTERVAL` | int | 30 | Statistics reporting interval |
| `RESET_STATS_ON_SESSION_CHANGE` | bool | True | Reset stats on session change |

## Usage Patterns

### Basic Configuration Access
```python
from src.core.services.config_manager import get_config

config = get_config()
database_uri = config.get('DATABASE_URI')
redis_host = config.get('REDIS_HOST')
```

### Direct ConfigManager Usage
```python
from src.core.services.config_manager import ConfigManager

config_manager = ConfigManager()
config_manager.load_from_env()
config = config_manager.get_config()
```

### Legacy Compatibility
```python
# Legacy pattern (automatically uses config_manager)
from src.core.services.config_manager import get_config

config = get_config()
# All existing code continues to work
```

## Environment Variable Mapping

All configuration parameters can be set via environment variables using the same name. For example:

```bash
# .env file
DATABASE_URI=postgresql://user:pass@localhost/db
REDIS_HOST=redis.example.com
REDIS_PORT=6380
TICKSTOCKPL_HOST=tickstockpl.example.com
TICKSTOCKPL_API_KEY=your-api-key-here
LOG_FILE_ENABLED=true
LOG_DB_ENABLED=true
```

## Sprint-Specific Additions

### Sprint 10: TickStockPL Integration
- Added Redis configuration for pub-sub communication
- Added TimescaleDB configuration for shared database access
- Added TickStockPL service endpoints configuration

### Sprint 32: Enhanced Error Management
- Added comprehensive error logging configuration
- Added database logging with severity thresholds
- Added Redis error channel integration

### Sprint 36: Configuration Consolidation
- Added TickStockPL API integration configuration
- Enhanced centralized configuration management
- Consolidated scattered environment variable usage

## Best Practices

### Configuration Management
1. **Use config_manager**: Always use `get_config()` instead of `os.getenv()`
2. **Provide defaults**: All configuration keys should have sensible defaults
3. **Validate types**: Use the CONFIG_TYPES dictionary for type validation
4. **Environment files**: Use `.env` files for local development

### Security Considerations
1. **Never commit secrets**: Keep sensitive values in environment variables
2. **Use strong defaults**: Default values should be secure
3. **Validate input**: All configuration values are validated for type and range
4. **Secure channels**: Use encrypted channels for sensitive configuration

### Performance Guidelines
1. **Cache configuration**: The config_manager caches loaded configuration
2. **Lazy loading**: JSON configurations are loaded on demand
3. **Efficient access**: Use the global `get_config()` function for performance
4. **Monitor usage**: Configuration change callbacks available for monitoring

## Troubleshooting

### Common Issues
1. **Missing .env file**: ConfigManager will use defaults if .env is not found
2. **Type validation errors**: Check CONFIG_TYPES for expected data types
3. **Legacy compatibility**: Old code should work without changes via get_config()
4. **JSON configuration**: Multi-frequency configs use separate JSON files

### Debugging Configuration
```python
# Debug configuration loading
config_manager = ConfigManager()
config_manager.load_from_env()
if not config_manager.validate_config():
    print("Configuration validation failed")

# Check specific values
config = config_manager.get_config()
print(f"Database URI: {config.get('DATABASE_URI')}")
print(f"Redis Host: {config.get('REDIS_HOST')}")
```

---

**Maintenance Note**: Update this document when adding new configuration parameters or changing defaults. Ensure all Sprint-specific configuration additions are documented with their Sprint number and purpose.