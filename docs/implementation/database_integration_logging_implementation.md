# Database Integration Logging Implementation

## Overview

Comprehensive database integration logging system that tracks pattern events flowing between TickStockPL (producer) and TickStockAppV2 (consumer) through Redis pub-sub architecture. Provides complete visibility into system integration health, pattern flow latency, and component connectivity.

## Purpose

- **Integration Verification**: Confirm that both systems are connected and communicating
- **Pattern Flow Tracking**: Track patterns from detection to user delivery with end-to-end latency metrics
- **System Health Monitoring**: Continuous heartbeat and subscription status logging
- **Debugging Support**: Identify where patterns get stuck in the pipeline

## Architecture Components

### 1. Database Schema

#### `integration_events` Table
```sql
CREATE TABLE integration_events (
    id SERIAL PRIMARY KEY,
    flow_id UUID,                    -- Unique identifier for tracking pattern flow
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50),          -- pattern_detected, heartbeat, subscription_active
    source_system VARCHAR(50),       -- TickStockPL or TickStockAppV2
    checkpoint VARCHAR(50),          -- PATTERN_PUBLISHED, EVENT_RECEIVED, etc.
    channel VARCHAR(100),            -- Redis channel used
    symbol VARCHAR(20),              -- Stock symbol (for patterns)
    pattern_name VARCHAR(50),        -- Pattern detected (for patterns)
    confidence NUMERIC,              -- Pattern confidence score
    user_count INTEGER,              -- Users notified (for WebSocket delivery)
    details JSONB,                   -- Additional event details
    latency_ms NUMERIC,              -- Processing latency
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `pattern_flow_analysis` View
```sql
CREATE VIEW pattern_flow_analysis AS
SELECT
    flow_id,
    MIN(timestamp) AS start_time,
    MAX(timestamp) AS end_time,
    EXTRACT(epoch FROM MAX(timestamp) - MIN(timestamp)) * 1000 AS total_latency_ms,
    symbol,
    pattern_name,
    MAX(confidence) AS confidence,
    MAX(user_count) AS users_notified,
    COUNT(*) AS checkpoints_logged,
    ARRAY_AGG(checkpoint ORDER BY timestamp) AS flow_path
FROM integration_events
WHERE flow_id IS NOT NULL
GROUP BY flow_id, symbol, pattern_name;
```

### 2. Database Integration Logger (`src/core/services/database_integration_logger.py`)

**Key Features**:
- Logs integration checkpoints to database
- Extracts flow_id from TickStockPL events for end-to-end tracking
- Handles both enum and string checkpoint values
- Provides health monitoring and recent flow analysis
- Graceful degradation when database unavailable

**Event Types Supported**:
- `PATTERN_DETECTED`: Pattern detection events
- `HEARTBEAT`: System heartbeat (every 60 seconds)
- `SUBSCRIPTION_ACTIVE`: Channel subscription status
- `SUBSCRIPTION_CONFIRMED`: Redis confirmation of subscription

**Checkpoints Tracked**:
- `PATTERN_PUBLISHED`: TickStockPL publishes pattern
- `EVENT_RECEIVED`: TickStockAppV2 receives from Redis
- `EVENT_PARSED`: Pattern data extracted successfully
- `WEBSOCKET_DELIVERED`: Sent to connected users
- `SUBSCRIBER_ALIVE`: Heartbeat checkpoint
- `CHANNEL_SUBSCRIBED`: Subscription activated

### 3. Enhanced Redis Event Subscriber (`src/core/services/redis_event_subscriber.py`)

**Integration Logging Features**:
- Logs channel subscriptions on startup
- Records Redis subscription confirmations
- Heartbeat logging every 60 seconds with stats
- Pattern event flow tracking with flow_id preservation

**Heartbeat Information Logged**:
```python
{
    'subscribed_channels': [...],
    'events_received': count,
    'events_processed': count,
    'events_forwarded': count,
    'connection_errors': count,
    'uptime_seconds': seconds,
    'last_event_time': timestamp
}
```

### 4. System Monitoring Tools

#### `scripts/monitor_system_health.py`
- Real-time health dashboard
- Shows active subscriptions and heartbeats
- Displays pattern flow with latency metrics
- Identifies incomplete flows and system issues

#### `scripts/diagnose_integration.py`
- Diagnoses integration problems
- Tests Redis pub-sub connectivity
- Publishes test patterns
- Suggests fixes for common issues

#### `scripts/test_integration_monitoring.py`
- Comprehensive test suite for integration logging
- Tests database connectivity
- Simulates complete pattern flows
- Verifies all logging mechanisms

## Implementation Flow

### Pattern Detection Flow (Normal Operation)

1. **TickStockPL** detects pattern
   - Logs: `PATTERN_PUBLISHED` with flow_id
   - Publishes to Redis channel `tickstock.events.patterns`

2. **TickStockAppV2** receives pattern
   - Logs: `EVENT_RECEIVED` with extracted flow_id
   - Processes pattern data
   - Logs: `EVENT_PARSED`

3. **WebSocket Broadcasting**
   - Sends to connected users
   - Logs: `WEBSOCKET_DELIVERED` with user count

4. **Pattern Flow Analysis**
   - View aggregates all checkpoints
   - Calculates end-to-end latency
   - Shows complete flow path

### System Health Monitoring (Continuous)

1. **On Startup**
   - Logs all channel subscriptions
   - Records Redis confirmations

2. **Every 60 Seconds**
   - Logs heartbeat with system stats
   - Shows events processed and uptime

3. **Connection Issues**
   - Logs connection errors
   - Tracks recovery attempts

## Usage

### Starting Services with Logging

```bash
# Both services log automatically when started
python start_both_services.py
```

### Monitoring Integration

```bash
# Real-time health monitoring
python scripts/monitor_system_health.py --watch

# Diagnose integration issues
python scripts/diagnose_integration.py

# Run comprehensive tests
python scripts/test_integration_monitoring.py
```

### Database Queries

```sql
-- Recent heartbeats
SELECT timestamp, source_system, details
FROM integration_events
WHERE event_type = 'heartbeat'
ORDER BY timestamp DESC LIMIT 10;

-- Complete pattern flows
SELECT * FROM pattern_flow_analysis
WHERE checkpoints_logged > 1
ORDER BY start_time DESC;

-- Check subscriptions
SELECT channel, checkpoint, timestamp
FROM integration_events
WHERE event_type = 'subscription_active'
ORDER BY timestamp DESC;
```

## Configuration

### Database Connection
- Host: localhost
- Port: 5433
- Database: tickstock
- User: app_readwrite
- Password: Configured in environment

### Logging Intervals
- Heartbeat: Every 60 seconds
- Health check: Every 60 seconds
- Subscription confirmation: On startup

## Troubleshooting

### No Pattern Events
If only heartbeats appear after hours:
1. Check if TickStockPL is running
2. Verify market data is flowing
3. Confirm pattern detection is active
4. Run diagnostic script

### Missing Checkpoints
Incomplete flows indicate:
- TickStockPL not publishing (no PATTERN_PUBLISHED)
- Redis connection issue (no EVENT_RECEIVED)
- Processing error (no EVENT_PARSED)
- No users connected (no WEBSOCKET_DELIVERED)

### Database Errors
- UUID format errors: Fixed by using proper UUIDs
- Enum/string mismatches: Handled with type conversion
- Connection issues: Check database configuration

## Performance Metrics

- **Target Latency**: <100ms end-to-end
- **Heartbeat Frequency**: 60 seconds
- **Database Write Rate**: Low impact (events + heartbeats only)
- **Storage Growth**: ~1MB per day typical usage

## Future Enhancements

- [ ] Alert system for missing heartbeats
- [ ] Automated recovery for subscription failures
- [ ] Pattern flow performance analytics dashboard
- [ ] Historical trend analysis for system health
- [ ] Automated integration testing on deployment

## Related Documentation

- [System Architecture](../architecture/system-architecture.md)
- [Redis Integration](../architecture/redis-integration.md)
- [Database Schema](../data/database-schema.md)
- [Monitoring Guide](../operations/monitoring.md)

---

*Last Updated: 2025-09-17*
*Sprint: Integration Monitoring Implementation*