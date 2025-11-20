# TickStockPL Health Event Requirements

**Date**: October 7, 2025, 12:40 PM ET
**Sprint**: Sprint 40 - Live Streaming Integration
**Priority**: MEDIUM - Required for dashboard health display
**Status**: Awaiting TickStockPL Implementation

---

## Summary

TickStockPL streaming service needs to publish periodic health status updates to Redis so the Live Streaming dashboard can display real-time system health metrics.

**Current Status**:
- ✅ Session events working (session_started/stopped)
- ✅ Dashboard shows session online
- ❌ Health metrics showing "UNKNOWN" - no health events received

---

## Required Implementation

### Health Event Publication

**Channel**: `tickstock:streaming:health`

**Frequency**: Every **5-10 seconds** while streaming session is active

**Event Structure**:
```json
{
  "type": "streaming_health",
  "health": {
    "session_id": "df4f5558-c1d6-496f-9b43-6849a55838aa",
    "status": "healthy",
    "active_symbols": 60,
    "ticks_per_second": 15.2,
    "patterns_detected": 5,
    "indicators_calculated": 150,
    "timestamp": "2025-10-07T17:35:00.000Z"
  },
  "timestamp": "2025-10-07T17:35:00.000Z"
}
```

### Field Definitions

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | string | Always "streaming_health" | `"streaming_health"` |
| `health.session_id` | string (UUID) | Current streaming session ID | `"df4f5558-c1d6-496f-9b43-6849a55838aa"` |
| `health.status` | string | System health status | `"healthy"`, `"degraded"`, `"error"` |
| `health.active_symbols` | integer | Number of symbols being processed | `60` |
| `health.ticks_per_second` | float | Current tick processing rate | `15.2` |
| `timestamp` | string (ISO 8601) | Event timestamp in UTC | `"2025-10-07T17:35:00.000Z"` |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `health.patterns_detected` | integer | Total patterns detected this session | `5` |
| `health.indicators_calculated` | integer | Total indicators calculated this session | `150` |
| `health.memory_usage_mb` | float | Current memory usage | `256.5` |
| `health.cpu_percent` | float | CPU usage percentage | `45.2` |
| `health.errors_count` | integer | Error count this session | `0` |
| `health.uptime_seconds` | integer | Session uptime | `3600` |

---

## Status Values

### health.status

| Value | Meaning | When to Use |
|-------|---------|-------------|
| `"healthy"` | System operating normally | Ticks flowing, no errors, performance good |
| `"degraded"` | System running but with issues | Slow performance, some errors, reduced capacity |
| `"error"` | System experiencing critical issues | Unable to process ticks, connection issues |
| `"starting"` | System initializing | During startup, before full operation |
| `"stopping"` | System shutting down | During graceful shutdown |

---

## Implementation Example (Python)

### Option 1: Periodic Health Publisher

```python
import asyncio
import json
from datetime import datetime

class StreamingHealthMonitor:
    """Publishes health metrics to Redis every 5 seconds."""

    def __init__(self, redis_client, session_id):
        self.redis_client = redis_client
        self.session_id = session_id
        self.active_symbols = 0
        self.ticks_per_second = 0.0
        self.patterns_detected = 0
        self.indicators_calculated = 0
        self.running = False

    async def start(self):
        """Start health monitoring loop."""
        self.running = True
        while self.running:
            await self._publish_health()
            await asyncio.sleep(5.0)  # Publish every 5 seconds

    def stop(self):
        """Stop health monitoring."""
        self.running = False

    async def _publish_health(self):
        """Publish current health status to Redis."""
        try:
            health_event = {
                'type': 'streaming_health',
                'health': {
                    'session_id': self.session_id,
                    'status': self._get_status(),
                    'active_symbols': self.active_symbols,
                    'ticks_per_second': self.ticks_per_second,
                    'patterns_detected': self.patterns_detected,
                    'indicators_calculated': self.indicators_calculated,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                },
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

            self.redis_client.publish(
                'tickstock:streaming:health',
                json.dumps(health_event)
            )

            logger.debug(f"STREAMING-HEALTH: Published health update - Status: {health_event['health']['status']}, Active Symbols: {self.active_symbols}, TPS: {self.ticks_per_second:.1f}")

        except Exception as e:
            logger.error(f"STREAMING-HEALTH: Failed to publish health event: {e}")

    def _get_status(self):
        """Determine current health status."""
        if self.ticks_per_second > 5.0 and self.active_symbols > 0:
            return 'healthy'
        elif self.ticks_per_second > 0:
            return 'degraded'
        else:
            return 'starting'

    def update_metrics(self, active_symbols, ticks_per_second):
        """Update health metrics (call from tick processor)."""
        self.active_symbols = active_symbols
        self.ticks_per_second = ticks_per_second

    def increment_patterns(self):
        """Increment pattern detection count."""
        self.patterns_detected += 1

    def increment_indicators(self, count=1):
        """Increment indicator calculation count."""
        self.indicators_calculated += count
```

### Option 2: Integrate with Existing Health Monitor

If you already have a `StreamingHealthMonitor` class:

```python
# In streaming_scheduler.py or similar

def _start_streaming(self, session_id):
    """Start streaming session."""
    # ... existing initialization code ...

    # Initialize health monitor with Redis publishing
    self.health_monitor = StreamingHealthMonitor(
        redis_client=self.redis_client,
        session_id=session_id
    )

    # Start health publishing loop
    asyncio.create_task(self.health_monitor.start())

    logger.info("STREAMING: Health monitor started, publishing to tickstock:streaming:health")

# In your tick processing loop
def _process_tick(self, tick_data):
    """Process incoming tick."""
    # ... existing tick processing ...

    # Update health metrics
    self.health_monitor.update_metrics(
        active_symbols=len(self.symbols),
        ticks_per_second=self._calculate_tick_rate()
    )
```

---

## Testing Instructions

### Step 1: Start Streaming Service

```bash
cd C:\Users\McDude\TickStockPL
python streaming_service.py
```

**Expected Log**:
```
STREAMING: Health monitor started, publishing to tickstock:streaming:health
STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 60, TPS: 15.2
```

### Step 2: Monitor Redis Channel

```bash
redis-cli SUBSCRIBE tickstock:streaming:health
```

**Expected Output** (every 5-10 seconds):
```
1) "message"
2) "tickstock:streaming:health"
3) "{\"type\":\"streaming_health\",\"health\":{\"session_id\":\"df4f5558-c1d6-496f-9b43-6849a55838aa\",\"status\":\"healthy\",\"active_symbols\":60,\"ticks_per_second\":15.2,\"patterns_detected\":5,\"indicators_calculated\":150,\"timestamp\":\"2025-10-07T17:35:00.000Z\"},\"timestamp\":\"2025-10-07T17:35:00.000Z\"}"
```

### Step 3: Verify TickStockAppV2 Receives Events

**Check TickStockAppV2 logs**:
```bash
grep "REDIS-SUBSCRIBER.*health" C:\Users\McDude\TickStockAppV2\temp_log.log | tail -10
```

**Expected**:
```
REDIS-SUBSCRIBER: Streaming health update received - Status: healthy
```

### Step 4: Verify Dashboard Display

1. Open: `http://localhost:5000/dashboard`
2. Navigate to: "Live Streaming" (sidebar)
3. **Expected Health Section**:
   ```
   Status: HEALTHY ✅
   Active Symbols: 60
   Data Flow: 15.2 ticks/sec
   ```

---

## Current Dashboard Behavior

### Before Health Events
**What you see now**:
```
Status: UNKNOWN
Active Symbols: 0
Data Flow: 0 ticks/sec
```

**Reason**: No health events received from TickStockPL

### After Health Events
**What you should see**:
```
Status: HEALTHY ✅
Active Symbols: 60
Data Flow: 15.2 ticks/sec
```

**Reason**: Health events flowing every 5-10 seconds

---

## Validation Checklist

### TickStockPL Developer Tasks

- [ ] Implement health event publishing to `tickstock:streaming:health`
- [ ] Set publication frequency to 5-10 seconds
- [ ] Include all required fields (`session_id`, `status`, `active_symbols`, `ticks_per_second`, `timestamp`)
- [ ] Test event format matches specification
- [ ] Verify events appear in `redis-cli SUBSCRIBE tickstock:streaming:health`
- [ ] Add logging for health publication (debug level)
- [ ] Handle Redis publish errors gracefully

### TickStockAppV2 Verification

- [ ] TickStockAppV2 logs show health events received
- [ ] Dashboard health section updates every 5-10 seconds
- [ ] Status changes from "UNKNOWN" to "HEALTHY"
- [ ] Active Symbols shows correct count (should be 60)
- [ ] Data Flow shows ticks/sec > 0

---

## Performance Impact

### Publishing Overhead

| Metric | Impact |
|--------|--------|
| **CPU** | <0.01% per publish |
| **Memory** | Negligible (JSON serialization) |
| **Network** | ~300 bytes per event, every 5 seconds = 60 bytes/sec |
| **Redis** | ~12 publishes/minute = trivial load |

**Conclusion**: Health event publishing has **negligible performance impact** ✅

---

## Error Handling

### Redis Publish Failure

```python
try:
    self.redis_client.publish('tickstock:streaming:health', json.dumps(health_event))
except redis.ConnectionError:
    logger.warning("STREAMING-HEALTH: Redis connection lost, health not published")
    # Continue streaming - health publishing is not critical
except Exception as e:
    logger.error(f"STREAMING-HEALTH: Unexpected error publishing health: {e}")
```

**Important**: Health publishing failures should **NOT** stop the streaming service. Log the error and continue.

---

## Message Retention

**Redis Pub/Sub**: Messages are **not stored** - only delivered to active subscribers

**Behavior**:
- If TickStockAppV2 is offline, messages are lost (no persistence)
- When TickStockAppV2 reconnects, it receives **new** messages only
- This is acceptable - health is current state, not historical

---

## Integration with Existing Code

### If You Already Have StreamingHealthMonitor

**File**: `src/streaming/health_monitor.py`

Add this method:

```python
def publish_health_to_redis(self):
    """Publish health status to Redis for TickStockAppV2 dashboard."""
    try:
        health_event = {
            'type': 'streaming_health',
            'health': {
                'session_id': self.session_id,
                'status': 'healthy' if self.is_healthy() else 'degraded',
                'active_symbols': self.get_active_symbol_count(),
                'ticks_per_second': self.get_tick_rate(),
                'patterns_detected': self.patterns_detected_count,
                'indicators_calculated': self.indicators_calculated_count,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        self.redis_client.publish('tickstock:streaming:health', json.dumps(health_event))

    except Exception as e:
        logger.error(f"Failed to publish health to Redis: {e}")
```

Then call this method every 5-10 seconds in your existing health check loop.

---

## Troubleshooting

### Issue: No health events appearing in redis-cli

**Check 1**: Is Redis running?
```bash
redis-cli ping
# Should return: PONG
```

**Check 2**: Is health monitor started?
```bash
# Look for this in TickStockPL logs:
grep "Health monitor started" logs/*.log
```

**Check 3**: Are events being published?
```bash
# Look for health publication logs:
grep "STREAMING-HEALTH" logs/*.log
```

### Issue: Health events published but dashboard shows UNKNOWN

**Check 1**: Is TickStockAppV2 subscribed?
```bash
# Look for subscription confirmation:
grep "Channel subscribe: tickstock:streaming:health" C:\Users\McDude\TickStockAppV2\temp_log.log
```

**Check 2**: Is event handler being called?
```bash
# Look for health event processing:
grep "Streaming health update" C:\Users\McDude\TickStockAppV2\temp_log.log
```

---

## Success Criteria

### Complete When

1. ✅ Health events publishing every 5-10 seconds to `tickstock:streaming:health`
2. ✅ TickStockAppV2 receiving health events (confirmed in logs)
3. ✅ Dashboard health section shows:
   - Status: HEALTHY (not UNKNOWN)
   - Active Symbols: 60 (not 0)
   - Data Flow: >0 ticks/sec (not 0)
4. ✅ Health updates refresh every 5-10 seconds in dashboard

---

## Related Documentation

- **Session Events**: `docs/planning/sprints/sprint40/TICKSTOCKPL_MISSING_SESSION_EVENT.md`
- **Requirements**: `docs/planning/sprints/sprint40/TICKSTOCKPL_REQUIREMENTS.md`
- **Sprint Plan**: `docs/planning/sprints/sprint40/SPRINT40_PLAN.md`
- **Redis Forwarding**: `docs/planning/sprints/sprint40/REDIS_FORWARDING_COMPLETE.md`

---

## Contact & Support

**TickStockAppV2 Developer**: Claude (Developer Assistant)
**TickStockPL Developer**: [Your contact info]
**Sprint**: Sprint 40 - Live Streaming Verification
**Current Session ID**: `df4f5558-c1d6-496f-9b43-6849a55838aa`

---

**Status**: ⏳ Awaiting Implementation
**Priority**: MEDIUM - Dashboard health display
**Estimated Time**: 30-60 minutes to implement

---

**Generated**: October 7, 2025, 12:40 PM ET
**Sprint 40 Phase**: Integration Testing & Health Monitoring
