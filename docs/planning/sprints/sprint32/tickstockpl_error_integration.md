# TickStockPL Error Integration Instructions

## Document Overview
**Created**: 2025-09-25
**Purpose**: Instructions for TickStockPL to integrate with unified error handling system
**Target**: TickStockPL Developer
**Status**: ✅ READY FOR IMPLEMENTATION - TickStockAppV2 side is fully operational

## Quick Start
1. Copy the `error_publisher.py` code from Section 2 to your project
2. Initialize with your Redis client on startup (Section 6)
3. Replace critical error logging with `log_error()` calls (Section 3)
4. Test with the provided test script (Section 7)
5. Verify TickStockAppV2 is receiving errors (Section 8)

## Integration Overview

**IMPORTANT**: TickStockAppV2's enhanced error handling system is **fully implemented and operational**. It is actively listening on Redis channel `tickstock:errors` and will automatically:
- Log all received errors to rotating file logs
- Store errors in database if severity >= configured threshold (default: error)
- Provide unified error tracking across both systems

TickStockPL needs to publish errors to Redis channel `tickstock:errors` using a standardized JSON format. TickStockAppV2 will subscribe to this channel and handle logging to file/database based on configured thresholds.

## Required Implementation

### 1. Error Message Format

Use this exact JSON structure for all errors published to Redis:

```json
{
    "error_id": "550e8400-e29b-41d4-a716-446655440000",
    "source": "TickStockPL",
    "severity": "error",
    "category": "pattern",
    "message": "Pattern detection failed for AAPL",
    "component": "PatternEngine",
    "traceback": "Full Python traceback...",
    "context": {
        "symbol": "AAPL",
        "pattern_type": "doji",
        "timeframe": "1min",
        "data_points": 20
    },
    "timestamp": "2025-09-25T12:00:00Z"
}
```

### 2. Python Implementation

Create a file `error_publisher.py` in TickStockPL:

```python
import redis
import json
import uuid
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

class ErrorPublisher:
    """Publish errors to TickStockAppV2 via Redis"""

    SEVERITY_LEVELS = ['critical', 'error', 'warning', 'info', 'debug']
    CATEGORIES = ['pattern', 'indicator', 'database', 'network', 'validation', 'performance', 'configuration']

    def __init__(self, redis_client: redis.Redis, channel: str = 'tickstock:errors'):
        self.redis_client = redis_client
        self.channel = channel

    def publish_error(self,
                     message: str,
                     severity: str = 'error',
                     category: Optional[str] = None,
                     component: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None,
                     include_traceback: bool = True):
        """
        Publish error to Redis for TickStockAppV2 consumption

        Args:
            message: Error message
            severity: One of: critical, error, warning, info, debug
            category: One of: pattern, indicator, database, network, validation, performance, configuration
            component: Component name where error occurred (e.g., 'PatternEngine')
            context: Additional context data (symbol, user_id, etc.)
            include_traceback: Whether to include Python traceback
        """
        if severity not in self.SEVERITY_LEVELS:
            severity = 'error'

        error_data = {
            'error_id': str(uuid.uuid4()),
            'source': 'TickStockPL',
            'severity': severity,
            'category': category,
            'message': message,
            'component': component,
            'traceback': traceback.format_exc() if include_traceback else None,
            'context': context or {},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        try:
            self.redis_client.publish(self.channel, json.dumps(error_data))
        except Exception as e:
            # Fallback to console logging if Redis fails
            print(f"Failed to publish error to Redis: {e}")
            print(f"Original error: {message}")

# Global instance
error_publisher = None

def initialize_error_publisher(redis_client: redis.Redis):
    """Initialize the global error publisher"""
    global error_publisher
    error_publisher = ErrorPublisher(redis_client)

def log_error(message: str, **kwargs):
    """Convenience function to publish errors"""
    if error_publisher:
        error_publisher.publish_error(message, **kwargs)
    else:
        print(f"Error publisher not initialized: {message}")
```

### 3. Integration Pattern

Wrap your existing exception handling:

```python
from error_publisher import log_error

def detect_pattern(symbol: str, data: list, pattern_type: str):
    """Example pattern detection with error handling"""
    try:
        # Your existing pattern detection code
        if len(data) < 20:
            raise ValueError("Insufficient data points")

        result = calculate_pattern(data)
        return result

    except ValueError as e:
        # Publish to Redis for TickStockAppV2
        log_error(
            message=f"Pattern detection failed: {str(e)}",
            severity='error',
            category='pattern',
            component='PatternDetector',
            context={
                'symbol': symbol,
                'pattern_type': pattern_type,
                'data_points': len(data),
                'required_points': 20
            }
        )
        # Re-raise or handle as needed
        raise

    except Exception as e:
        # Critical unexpected errors
        log_error(
            message=f"Unexpected error in pattern detection: {str(e)}",
            severity='critical',
            category='pattern',
            component='PatternDetector',
            context={
                'symbol': symbol,
                'pattern_type': pattern_type
            }
        )
        raise
```

### 4. Severity Guidelines

Use these severity levels consistently:

| Severity | When to Use | Example |
|----------|-------------|---------|
| **critical** | System failure, data corruption risk | Database connection lost, Redis unavailable |
| **error** | Operation failed, needs attention | Pattern detection failed, API call failed |
| **warning** | Degraded performance, non-critical issue | Slow query, missing optional data |
| **info** | Normal operational events | Pattern detected, job completed |
| **debug** | Development/troubleshooting only | Detailed processing steps |

### 5. Category Guidelines

| Category | Description | Example |
|----------|-------------|---------|
| **pattern** | Pattern detection issues | Insufficient data, pattern calculation errors |
| **indicator** | Technical indicator errors | Moving average failures, RSI calculation errors |
| **database** | Database operations | Connection errors, query failures |
| **network** | External API/network issues | Polygon.io timeouts, connection failures |
| **validation** | Data validation failures | Invalid symbols, malformed data |
| **performance** | Performance issues | Slow processing, threshold violations |
| **configuration** | Config/setup issues | Missing environment variables, invalid settings |

### 6. Initialization in TickStockPL

In your main application startup:

```python
import redis
from error_publisher import initialize_error_publisher

def initialize_app():
    # Your existing initialization
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True
    )

    # Initialize error publisher
    initialize_error_publisher(redis_client)

    # Rest of your initialization...
```

### 7. Testing Your Integration

Test script for TickStockPL:

```python
from error_publisher import log_error
import time

def test_error_publishing():
    """Test that errors are published correctly"""

    # Test different severity levels
    severities = ['debug', 'info', 'warning', 'error', 'critical']

    for severity in severities:
        log_error(
            message=f"Test {severity} message from TickStockPL",
            severity=severity,
            category='test',
            component='TestComponent',
            context={
                'test_id': 123,
                'timestamp': time.time()
            }
        )
        print(f"Published {severity} error")
        time.sleep(1)

    print("Test complete - check TickStockAppV2 logs")

if __name__ == "__main__":
    test_error_publishing()
```

### 8. Verification

To verify your integration is working:

1. **Check Redis channel has subscribers**:
```bash
redis-cli
> PUBSUB NUMSUB tickstock:errors
```

2. **Monitor the channel directly**:
```bash
redis-cli
> SUBSCRIBE tickstock:errors
```

3. **Check TickStockAppV2 logs**:
   - Console output should show received errors
   - File log at `logs/tickstock.log` (if enabled)
   - Database table `error_logs` for severity >= threshold

### 9. Best Practices

1. **Always include context** - Symbol, timeframe, user_id when relevant
2. **Use appropriate severity** - Don't mark everything as 'error'
3. **Meaningful messages** - Include what failed and why
4. **Component identification** - Always specify component
5. **Category consistency** - Use standard categories
6. **Don't over-log** - Avoid logging in tight loops
7. **Performance consideration** - Redis publish is fast but not free

### 10. Migration Checklist

- [ ] Add `error_publisher.py` to TickStockPL
- [ ] Initialize error publisher on startup
- [ ] Identify critical error points
- [ ] Wrap existing exception handlers
- [ ] Test each severity level
- [ ] Verify Redis connectivity
- [ ] Confirm TickStockAppV2 receives errors
- [ ] Monitor for performance impact

## What Happens to Your Errors

Once TickStockPL publishes an error to Redis, TickStockAppV2 automatically:

1. **Receives** the error via Redis subscriber (always running)
2. **Validates** the JSON format
3. **Logs to file** - Always written to `logs/tickstock.log` with rotation
4. **Stores in database** - If severity >= threshold (currently set to 'error')
5. **Tracks metrics** - Error counts, component statistics

### Current TickStockAppV2 Configuration
```bash
# From TickStockAppV2 .env
LOG_FILE_PATH=logs/tickstock.log
LOG_FILE_MAX_SIZE=10485760       # 10MB rotation
LOG_FILE_BACKUP_COUNT=5           # Keep 5 rotated files
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error  # error and critical go to DB
REDIS_ERROR_CHANNEL=tickstock:errors
```

This means:
- ✅ All your errors are logged to file
- ✅ Only 'error' and 'critical' severities stored in database
- ✅ 'warning', 'info', 'debug' only go to file (not database)

## Questions/Support

If you need clarification or encounter issues:
1. Check that Redis is running and accessible
2. Verify channel name matches: `tickstock:errors`
3. Ensure JSON format exactly matches specification
4. Test with simple messages first, then add complexity
5. Check TickStockAppV2 logs for confirmation:
   - Console output will show "Received error from TickStockPL"
   - File log at `C:\Users\McDude\TickStockAppV2\logs\tickstock.log`
   - Database table `error_logs` for errors meeting threshold

## Handoff Checklist

### For TickStockPL Developer:
- [ ] Redis client available and connected
- [ ] `error_publisher.py` added to project
- [ ] Error publisher initialized on startup
- [ ] Critical error points identified
- [ ] Test script run successfully
- [ ] Verified errors appear in TickStockAppV2

### TickStockAppV2 Status (COMPLETED):
- ✅ Enhanced logger implemented and tested
- ✅ Redis subscriber running and listening
- ✅ Database table `error_logs` created
- ✅ File logging with rotation configured
- ✅ Performance verified (<100ms, actual 1-2ms)
- ✅ Integration tests passing

---

**Note**: This integration allows TickStockPL to report errors without implementing its own file/database logging. TickStockAppV2 handles all persistence based on configured thresholds. The system is live and ready to receive your errors immediately.