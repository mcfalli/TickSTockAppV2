# Error Handling Architecture

**Created**: 2025-09-25
**Sprint**: 32
**Status**: IMPLEMENTED

## Executive Summary

TickStockAppV2 uses a **dual-logging system** consisting of:
1. **Standard Python Logging** - Existing `logger.*` calls (unchanged)
2. **Enhanced Error Handling** - New database/file/Redis system (Sprint 32)

**CRITICAL**: These are separate systems. Standard logger calls do NOT automatically go to the database.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TickStockAppV2                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Standard Python Logging          Enhanced Error System    │
│  ┌──────────────────┐            ┌────────────────────┐   │
│  │ logger.info()    │            │ enhanced_logger    │   │
│  │ logger.error()   │            │ .log_error()       │   │
│  │ logger.debug()   │            └─────────┬──────────┘   │
│  └────────┬─────────┘                      │              │
│           │                                 │              │
│           ↓                                 ↓              │
│  ┌──────────────────┐            ┌────────────────────┐   │
│  │ Console Output   │            │ Severity Check     │   │
│  │ Standard Files   │            └─────────┬──────────┘   │
│  └──────────────────┘                      │              │
│                                   ┌─────────┴─────────┐   │
│                                   ↓                   ↓   │
│                          ┌──────────────┐   ┌──────────┐  │
│                          │ File Logger  │   │ Database │  │
│                          │ (rotating)   │   │ (if >=   │  │
│                          └──────────────┘   │threshold)│  │
│                                              └──────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Redis Subscriber                        │ │
│  │         (tickstock:errors channel)                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                           ↑                                │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │  TickStockPL   │
                    │    Errors      │
                    └────────────────┘
```

## Two Separate Systems

### 1. Standard Python Logging (Existing)

**What it is**: The current logging throughout the codebase
```python
logger = logging.getLogger(__name__)
logger.info("Processing started")
logger.error("Connection failed")
```

**Where it goes**:
- Console output (stdout/stderr)
- Standard log files (if configured)
- **NOT to the database**
- **NOT to the enhanced system**

**No changes required** - All existing code continues to work

### 2. Enhanced Error System (Sprint 32)

**What it is**: New system for critical error tracking
```python
enhanced_logger = get_enhanced_logger()
enhanced_logger.log_error(
    severity='error',
    message='Connection failed',
    category='network',
    component='DataService',
    context={'retry_count': 3}
)
```

**Where it goes**:
- Rotating file logs (always)
- Database `error_logs` table (if severity >= threshold)
- Receives TickStockPL errors via Redis

**Requires explicit calls** - Must use `enhanced_logger.log_error()`

## Key Design Decisions

### Why Two Systems?

1. **Backward Compatibility**: No refactoring of existing code required
2. **Performance**: Only critical errors go to database
3. **Flexibility**: Can choose which errors deserve database storage
4. **Simplicity**: Standard logging remains simple and fast

### When to Use Each System

| Use Standard Logger | Use Enhanced Logger |
|-------------------|-------------------|
| Debug information | Critical errors |
| Info/status messages | Cross-system errors |
| Temporary logging | Persistent error tracking |
| Development debugging | Production monitoring |
| High-frequency events | Important failures |

## Configuration

### Environment Variables (.env)
```bash
# Enhanced Error System Configuration
LOG_FILE_ENABLED=true               # Enable file logging
LOG_FILE_PATH=logs/tickstock.log    # Log file location
LOG_FILE_MAX_SIZE=10485760          # 10MB rotation size
LOG_FILE_BACKUP_COUNT=5              # Keep 5 rotated files
LOG_DB_ENABLED=true                  # Enable database storage
LOG_DB_SEVERITY_THRESHOLD=error      # Only error/critical to DB
REDIS_ERROR_CHANNEL=tickstock:errors # Redis channel for PL errors
```

### Severity Levels and Database Storage

| Severity | Numeric Level | Goes to File? | Goes to DB? (threshold=error) |
|----------|--------------|---------------|-------------------------------|
| debug    | 10           | Yes           | No                            |
| info     | 20           | Yes           | No                            |
| warning  | 30           | Yes           | No                            |
| error    | 40           | Yes           | **Yes**                       |
| critical | 50           | Yes           | **Yes**                       |

## Usage Patterns

### Pattern 1: Keep Standard Logging As-Is
```python
# No changes needed - works exactly as before
logger = logging.getLogger(__name__)
logger.info("Starting process")
logger.error("Process failed")  # Only goes to console/standard logs
```

### Pattern 2: Add Enhanced Logging for Critical Errors
```python
# Standard logging for visibility
logger.error(f"Pattern detection failed for {symbol}")

# Also log to database for tracking
enhanced_logger = get_enhanced_logger()
if enhanced_logger:  # Graceful if not available
    enhanced_logger.log_error(
        severity='error',
        message=f"Pattern detection failed for {symbol}",
        category='pattern',
        component='PatternDetector',
        context={'symbol': symbol, 'user_id': user_id}
    )
```

### Pattern 3: Helper Function (Optional)
```python
def log_critical_error(message, **context):
    """Log to both standard and enhanced systems"""
    logger.error(message)

    enhanced_logger = get_enhanced_logger()
    if enhanced_logger:
        enhanced_logger.log_error(
            severity='error',
            message=message,
            category=context.get('category', 'general'),
            component=context.get('component', __name__),
            context=context
        )

# Usage
log_critical_error(
    "Database connection lost",
    category='database',
    retry_count=3
)
```

## Cross-System Integration

### TickStockPL → TickStockAppV2 Flow

1. TickStockPL publishes error to Redis:
```python
# In TickStockPL
redis_client.publish('tickstock:errors', json.dumps({
    'severity': 'error',
    'message': 'Backtesting failed',
    'category': 'backtesting',
    'component': 'BacktestEngine',
    'source': 'TickStockPL',
    'error_id': str(uuid.uuid4()),
    'timestamp': datetime.utcnow().isoformat(),
    'context': {'job_id': '123'}
}))
```

2. TickStockAppV2 subscriber receives and processes:
```python
# Automatically handled by error_subscriber.py
# Goes to enhanced logger → file + database (if threshold met)
```

## Database Schema

### error_logs Table
```sql
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    error_id UUID NOT NULL,
    source VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    message TEXT NOT NULL,
    component VARCHAR(100),
    traceback TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX idx_error_logs_severity ON error_logs(severity);
CREATE INDEX idx_error_logs_source ON error_logs(source);
CREATE INDEX idx_error_logs_component ON error_logs(component);
```

## Performance Characteristics

- **Standard Logger**: ~0.1ms per call
- **Enhanced Logger**: 1-2ms average, <100ms maximum
- **Database Writes**: Async, batched if volume high
- **File Rotation**: Automatic, non-blocking
- **Redis Subscription**: Persistent connection, auto-reconnect

## Migration Guide (Optional)

### If You Want Database Logging for Existing Errors

#### Option 1: Add Custom Handler (Recommended)
```python
# Add to app.py after enhanced logger initialization
class DatabaseLogHandler(logging.Handler):
    """Send ERROR and CRITICAL to database automatically"""

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            enhanced_logger = get_enhanced_logger()
            if enhanced_logger:
                enhanced_logger.log_error(
                    severity=record.levelname.lower(),
                    message=record.getMessage(),
                    category='auto',
                    component=record.name,
                    context={'auto_captured': True}
                )

# Attach to root logger
logging.getLogger().addHandler(DatabaseLogHandler())
```

#### Option 2: Selective Enhancement
Only enhance specific, critical error points in the code where database tracking is valuable.

## Monitoring & Diagnostics

### Check System Health
```python
enhanced_logger = get_enhanced_logger()
stats = enhanced_logger.get_stats()
print(f"Total errors: {stats['total_errors']}")
print(f"Database writes: {stats['database_writes']}")
print(f"File logging: {stats['file_logging_enabled']}")
print(f"Database logging: {stats['database_logging_enabled']}")
```

### Query Recent Errors
```sql
-- Last 10 critical errors
SELECT * FROM error_logs
WHERE severity = 'critical'
ORDER BY created_at DESC
LIMIT 10;

-- Errors by component today
SELECT component, COUNT(*)
FROM error_logs
WHERE created_at > CURRENT_DATE
GROUP BY component;
```

## FAQ

**Q: Do I need to change all my logger calls?**
A: No. All existing `logger.*` calls continue to work unchanged.

**Q: Will my errors automatically go to the database?**
A: No. Only explicit `enhanced_logger.log_error()` calls go to database.

**Q: Can I make standard logger errors go to database?**
A: Yes, by adding a custom handler (see Migration Guide).

**Q: What if the database is down?**
A: Enhanced logger gracefully degrades - errors still go to file.

**Q: How do I log TickStockPL errors?**
A: Publish to Redis channel `tickstock:errors` - AppV2 handles the rest.

## Summary

The Sprint 32 Enhanced Error Handling provides:
- **Separate system** from standard Python logging
- **Opt-in database storage** for critical errors
- **Configurable thresholds** via environment variables
- **Cross-system integration** via Redis
- **No breaking changes** to existing code

Standard `logger.*` calls remain unchanged and do NOT automatically go to the database. Use `enhanced_logger.log_error()` explicitly for database storage.