# Configuration Guide

**Version**: 3.0.0
**Last Updated**: September 26, 2025

## Environment Configuration

### Core Settings (.env)

```bash
# Application
FLASK_ENV=development              # development | production
FLASK_PORT=8501                    # Web server port
FLASK_SECRET_KEY=your-secret-key  # Session encryption key
DEBUG=False                        # Debug mode (never true in production)

# Database (Read-only access)
DATABASE_URL=postgresql://app_readwrite:password@localhost:5432/tickstock
DB_POOL_SIZE=10                   # Connection pool size
DB_MAX_OVERFLOW=20                # Max overflow connections
DB_POOL_TIMEOUT=30                # Connection timeout (seconds)

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=                   # Optional password
REDIS_MAX_CONNECTIONS=50          # Connection pool size

# Redis Channels
REDIS_PATTERN_CHANNEL=tickstock.events.patterns
REDIS_INDICATOR_CHANNEL=tickstock.events.indicators
REDIS_MONITORING_CHANNEL=tickstock:monitoring
REDIS_ERROR_CHANNEL=tickstock:errors
REDIS_PROCESSING_CHANNEL=tickstock.events.processing

# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/tickstock.log
LOG_FILE_MAX_SIZE=10485760        # 10MB
LOG_FILE_BACKUP_COUNT=5
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error   # Only log errors to database

# WebSocket Configuration
WEBSOCKET_CORS_ORIGINS=*          # Allowed origins (* for dev)
WEBSOCKET_MAX_CONNECTIONS=1000    # Max concurrent connections
WEBSOCKET_PING_INTERVAL=25        # Keepalive ping (seconds)
WEBSOCKET_PING_TIMEOUT=60         # Connection timeout (seconds)

# Authentication
SESSION_PERMANENT=False
PERMANENT_SESSION_LIFETIME=3600   # 1 hour
SESSION_COOKIE_SECURE=False       # Set True for HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Performance Tuning
CACHE_TTL=300                     # Cache time-to-live (seconds)
CACHE_REDIS_ENABLED=true
CACHE_MEMORY_ENABLED=true
CACHE_MAX_ENTRIES=10000
BATCH_SIZE=1000                   # Processing batch size
WORKER_THREADS=4                  # Background worker threads

# Feature Flags
FEATURE_PATTERN_DISCOVERY=true
FEATURE_BACKTESTING=true
FEATURE_ADMIN_PANEL=true
FEATURE_HISTORICAL_DATA=true
FEATURE_WEBSOCKET_STREAMING=true

# Data Sources
DATA_SOURCE_TYPE=polygon          # polygon | synthetic | csv
MASSIVE_API_KEY=your-api-key
POLYGON_BASE_URL=https://api.massive.com
SYNTHETIC_TICK_RATE=100           # Ticks per second for synthetic data

# Monitoring
MONITORING_ENABLED=true
HEALTH_CHECK_INTERVAL=60          # Seconds between health checks
METRICS_COLLECTION_INTERVAL=30    # Seconds between metric collections
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_TO=admin@example.com
```

## Configuration Files

### Database Configuration (`config/database_config.py`)
```python
class DatabaseConfig:
    # Connection settings
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 10))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', 20))
    SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', 30))

    # Performance settings
    SQLALCHEMY_POOL_PRE_PING = True  # Verify connections
    SQLALCHEMY_POOL_RECYCLE = 3600   # Recycle connections hourly
    SQLALCHEMY_ECHO = False          # Don't log SQL queries
```

### Redis Configuration (`config/redis_config.py`)
```python
class RedisConfig:
    # Connection
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    # Channels
    CHANNELS = {
        'patterns': 'tickstock.events.patterns',
        'indicators': 'tickstock.events.indicators',
        'monitoring': 'tickstock:monitoring',
        'errors': 'tickstock:errors',
        'processing': 'tickstock.events.processing'
    }

    # Performance
    CONNECTION_POOL_MAX = 50
    SOCKET_KEEPALIVE = True
    SOCKET_KEEPALIVE_OPTIONS = {
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    }
```

### Logging Configuration (`config/logging_config.py`)
```python
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': 'logs/tickstock.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,
            'backupCount': 5
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file', 'error_file']
    }
}
```

## Environment-Specific Settings

### Development
```bash
# .env.development
FLASK_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
CACHE_TTL=60
WEBSOCKET_CORS_ORIGINS=*
```

### Production
```bash
# .env.production
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=WARNING
CACHE_TTL=3600
WEBSOCKET_CORS_ORIGINS=https://yourdomain.com
SESSION_COOKIE_SECURE=True
```

### Testing
```bash
# .env.test
FLASK_ENV=testing
DATABASE_URL=postgresql://test_user:password@localhost:5432/tickstock_test
REDIS_DB=1
LOG_LEVEL=ERROR
```

## Performance Tuning

### Cache Settings
```python
# Optimize for high-traffic
CACHE_REDIS_ENABLED=true
CACHE_TTL=600                  # 10 minutes
CACHE_MAX_ENTRIES=50000        # Increase for more symbols

# Optimize for low-latency
CACHE_MEMORY_ENABLED=true
CACHE_TTL=60                   # 1 minute
BATCH_SIZE=100                 # Smaller batches
```

### Database Pool
```python
# High concurrency
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=10

# Resource constrained
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### WebSocket Settings
```python
# High volume streaming
WEBSOCKET_MAX_CONNECTIONS=5000
WEBSOCKET_PING_INTERVAL=30
WORKER_THREADS=8

# Standard usage
WEBSOCKET_MAX_CONNECTIONS=100
WEBSOCKET_PING_INTERVAL=25
WORKER_THREADS=2
```

## Security Configuration

### Production Hardening
```bash
# Essential security settings
FLASK_SECRET_KEY=$(openssl rand -hex 32)  # Generate strong key
SESSION_COOKIE_SECURE=True                # HTTPS only
SESSION_COOKIE_HTTPONLY=True             # No JS access
SESSION_COOKIE_SAMESITE=Strict           # CSRF protection
DEBUG=False                               # Never in production
FLASK_ENV=production

# API Security
API_RATE_LIMIT=100                       # Requests per minute
API_BURST_LIMIT=20                       # Burst allowance
API_KEY_REQUIRED=true                    # Require API keys
```

### CORS Configuration
```python
# Restrictive (production)
WEBSOCKET_CORS_ORIGINS=https://app.yourdomain.com

# Permissive (development)
WEBSOCKET_CORS_ORIGINS=*

# Multiple origins
WEBSOCKET_CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
```

## Monitoring Configuration

### Health Checks
```python
# Health check settings
HEALTH_CHECK_INTERVAL=60              # Check every minute
HEALTH_CHECK_TIMEOUT=5                # 5 second timeout
HEALTH_CHECK_RETRIES=3                # Retry failed checks

# Component checks
CHECK_DATABASE=true
CHECK_REDIS=true
CHECK_DISK_SPACE=true
CHECK_MEMORY=true
```

### Metrics Collection
```python
# Metrics settings
METRICS_ENABLED=true
METRICS_INTERVAL=30                   # Collect every 30 seconds
METRICS_RETENTION_DAYS=30             # Keep 30 days of metrics

# Performance thresholds
ALERT_CPU_THRESHOLD=80                # Alert at 80% CPU
ALERT_MEMORY_THRESHOLD=90             # Alert at 90% memory
ALERT_RESPONSE_TIME_MS=1000           # Alert if >1s response
```

## Troubleshooting Configuration Issues

### Common Problems

1. **Database Connection Refused**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Confirm firewall allows connection

2. **Redis Connection Failed**
   - Ensure Redis server is running
   - Verify REDIS_HOST and REDIS_PORT
   - Check Redis password if set

3. **WebSocket Not Connecting**
   - Confirm CORS origins are correct
   - Check firewall rules for WebSocket port
   - Verify SSL certificates in production

4. **High Memory Usage**
   - Reduce CACHE_MAX_ENTRIES
   - Lower DB_POOL_SIZE
   - Decrease WORKER_THREADS

5. **Slow Performance**
   - Increase CACHE_TTL
   - Enable CACHE_REDIS_ENABLED
   - Optimize BATCH_SIZE

### Configuration Validation
```bash
# Validate configuration
python scripts/dev_tools/validate_config.py

# Test database connection
python -c "from src.infrastructure.database.tickstock_db import test_connection; test_connection()"

# Test Redis connection
redis-cli ping
```

## Administration Configuration

### User Roles & Access Control

Configure role-based access control for the admin system:

```bash
# User role configuration in .env
DEFAULT_USER_ROLE=user           # New user default role
ADMIN_REGISTRATION_ENABLED=false # Allow admin self-registration
SUPER_USER_EMAIL=admin@example.com # Initial super user
```

#### Available Roles
| Role | Access Level | Description |
|------|-------------|-------------|
| `user` | Regular Pages | Dashboard, account, market data |
| `moderator` | Regular Pages | Future use - same as user |
| `admin` | Admin Pages Only | User management, data loading, monitoring |
| `super` | **Full Access** | Both regular and admin functionality |

### Admin Features Configuration

#### Historical Data Management
```bash
# Historical data loading settings
HISTORICAL_DATA_BATCH_SIZE=100   # Symbols per batch
HISTORICAL_DATA_WORKERS=4         # Parallel workers
HISTORICAL_DATA_RETRY_COUNT=3    # API retry attempts
HISTORICAL_DATA_CACHE_DAYS=30    # Cache retention

# Scheduler configuration
SCHEDULER_ENABLED=false          # Enable automated loading
SCHEDULER_CRON_DAILY="0 16 * * *"  # Daily at 4 PM
SCHEDULER_UNIVERSE=sp500          # Default universe to load
```

#### User Management
```bash
# User management settings
USER_SESSION_TIMEOUT=3600        # 1 hour timeout
USER_MAX_SESSIONS=5              # Max concurrent sessions
USER_REGISTRATION_ENABLED=true   # Allow new registrations
USER_EMAIL_VERIFICATION=false    # Require email verification
USER_PASSWORD_MIN_LENGTH=8       # Minimum password length
```

#### Health Monitoring
```bash
# Health monitor configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=60         # Seconds
HEALTH_DB_TIMEOUT=5              # Database check timeout
HEALTH_REDIS_TIMEOUT=2           # Redis check timeout
HEALTH_ALERT_THRESHOLD=3         # Failed checks before alert
```

### Admin Endpoints

All admin routes require authentication and appropriate role:

- `/admin/` - Admin dashboard (requires admin/super role)
- `/admin/users` - User management interface
- `/admin/historical-data` - Historical data loading
- `/admin/health` - System health monitoring

### Setting Up Admin Access

1. **Create Initial Super User**:
```bash
python scripts/admin/create_admin_user.py \
  --username admin@example.com \
  --password SecurePassword123 \
  --role super
```

2. **Upgrade Existing User**:
```bash
python scripts/admin/upgrade_to_super.py --username user@example.com
```

3. **Configure Admin Features**:
```bash
# Enable all admin features
ADMIN_FEATURES_ENABLED=true
ADMIN_HISTORICAL_DATA=true
ADMIN_USER_MANAGEMENT=true
ADMIN_HEALTH_MONITOR=true
```