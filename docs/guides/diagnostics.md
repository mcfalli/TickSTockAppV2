# Diagnostic Tools Guide

**Version**: 1.0.0
**Last Updated**: October 17, 2025 (Sprint 43)
**Status**: Production Ready

## Overview

This guide covers diagnostic tools for monitoring and troubleshooting the TickStockAppV2 and TickStockPL integration, with a focus on Redis pub-sub communication, streaming performance, and system health.

## Quick Links

- **Redis Channel Monitoring**: Real-time pub-sub activity tracking
- **Live Streaming Dashboard**: Browser-based Redis content viewer
- **Log Analysis**: Finding and interpreting system logs
- **Performance Metrics**: Measuring and validating performance targets

---

## Redis Channel Monitor

### Overview

The Redis Channel Monitor is a real-time diagnostic script that tracks all Redis pub-sub messages flowing between TickStockPL and TickStockAppV2.

**File**: `scripts/diagnostics/monitor_redis_channels.py`

### When to Use

- **Pattern/Indicator not appearing**: Verify Redis channels are flowing
- **Startup delays**: Check when channels start publishing
- **Integration issues**: Confirm TickStockPL → TickStockAppV2 communication
- **Performance tuning**: Measure message rates and throughput

### Usage

```bash
# Start monitoring (runs until Ctrl+C)
python scripts/diagnostics/monitor_redis_channels.py

# Output will show:
# - Real-time channel messages
# - Message counts per channel
# - Event type mapping
# - Health analysis
```

### Sample Output

```
================================================================================
REDIS CHANNEL MONITOR - Sprint 43 Diagnostic
================================================================================
Started: 2025-10-17 20:25:00

Monitoring for Redis channel messages...
Press Ctrl+C to stop and see summary
================================================================================

[20:25:01] Channel: tickstock:indicators:streaming
[20:25:02] Channel: tickstock:patterns:streaming
[20:25:02] Channel: tickstock:patterns:detected
[20:25:03] STREAMING-BUFFER: Flush cycle completed (12 events)
[20:25:03] *** Received streaming pattern - Doji on AAPL (confidence: 0.85)

^C
================================================================================
SUMMARY
================================================================================
Total messages received: 54

Channels Received:
  tickstock:indicators:streaming: 24 messages
  tickstock:patterns:streaming: 15 messages
  tickstock:patterns:detected: 15 messages

Event Types Mapped:
  STREAMING_INDICATOR: 24 events
  STREAMING_PATTERN: 30 events

ANALYSIS:
  ✅ Indicators channel WORKING (24 messages)
  ✅ Patterns channel WORKING (30 messages)

================================================================================
```

### Interpreting Results

**✅ Healthy System:**
- All channels receiving messages within 1-2 minutes
- Message counts increasing steadily
- Both patterns and indicators flowing

**⚠️ Warning Signs:**
- Only indicators, no patterns (or vice versa)
- No messages for 5+ minutes
- Event type mapping missing

**❌ Critical Issues:**
- No messages at all
- Channels not listed in summary
- TickStockPL not publishing

### Troubleshooting

**Problem**: No messages appearing

**Solutions**:
1. Verify TickStockPL is running: `ps aux | grep tickstockpl`
2. Check Redis server: `redis-cli ping` (should return PONG)
3. Verify Redis connection in `.env`: `REDIS_HOST=localhost`, `REDIS_PORT=6379`
4. Check TickStockAppV2 logs: `tail -f logs/tickstock.log | grep REDIS-SUBSCRIBER`

**Problem**: Only indicators, no patterns

**Solutions**:
1. Check TickStockPL pattern detection job is running
2. Verify bars are being created: `SELECT COUNT(*) FROM ohlcv_1min WHERE created_at > NOW() - INTERVAL '5 minutes';`
3. Check TickStockPL logs for pattern detection errors
4. Verify pattern bar requirements (Sprint 43 fix applied)

---

## Live Streaming Dashboard

### Overview

Browser-based dashboard showing real-time pattern and indicator events with raw Redis JSON content.

**URL**: http://localhost:5000/streaming

### Features

- **Stacked Vertical Layout**: Patterns above indicators
- **Raw Redis JSON**: See exact message structure
- **Dark Theme Code Display**: Easy-to-read JSON formatting
- **Real-time Updates**: 250ms refresh via WebSocket
- **Message Counters**: Track total patterns and indicators

### When to Use

- **Visual confirmation**: See patterns/indicators appearing in real-time
- **Data inspection**: Review exact Redis message structure
- **Field debugging**: Verify field names (pattern_type, indicator_type)
- **Timing analysis**: Check timestamp accuracy and lag

### Using the Dashboard

1. **Start TickStockAppV2**: `python start_all_services.py`
2. **Navigate**: http://localhost:5000/streaming
3. **Observe**: Messages appear as they're received

### Sample Display

```
Real-time Patterns                                              15 patterns
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Doji    AAPL                                85.0%    20:25:30
  Raw Redis Content:
  {
    "type": "streaming_pattern",
    "detection": {
      "symbol": "AAPL",
      "pattern_type": "Doji",
      "confidence": 0.85,
      "timestamp": "2025-10-17T20:25:30.123Z",
      "timeframe": "1min",
      "bar_data": {
        "open": 150.25,
        "high": 150.50,
        "low": 150.10,
        "close": 150.30,
        "volume": 125000
      }
    }
  }

Indicator Alerts                                                 24 alerts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RSI    TSLA                              72.5      20:25:29
  Raw Redis Content:
  {
    "type": "streaming_indicator",
    "calculation": {
      "symbol": "TSLA",
      "indicator_type": "RSI",
      "value": 72.5,
      "timestamp": "2025-10-17T20:25:29.456Z",
      "timeframe": "1min"
    }
  }
```

### Interpreting the Dashboard

**Field Names to Check**:
- ✅ Correct: `pattern_type`, `indicator_type`
- ❌ Incorrect: `pattern`, `indicator` (old field names, Sprint 43 fixed)

**Timing Analysis**:
- Pattern detection should appear within 1-2 minutes of startup
- Indicators should appear within 1-2 minutes
- Timestamps should be recent (within seconds)

---

## Log Analysis

### Application Logs

**Location**: `logs/tickstock.log`

### Key Log Patterns

#### Redis Channel Activity

```bash
# View all Redis subscriber debug messages
grep "REDIS-SUBSCRIBER DEBUG" logs/tickstock.log

# Count messages per channel
grep "REDIS-SUBSCRIBER DEBUG: Received message on channel:" logs/tickstock.log | \
  cut -d"'" -f2 | sort | uniq -c

# Example output:
#   24 tickstock:indicators:streaming
#   15 tickstock:patterns:streaming
#   15 tickstock:patterns:detected
```

#### Pattern Detection

```bash
# View pattern detections
grep "Received streaming pattern" logs/tickstock.log

# Count by pattern type
grep "Received streaming pattern" logs/tickstock.log | \
  awk -F'-' '{print $NF}' | awk '{print $1}' | sort | uniq -c

# Example output:
#    5 Doji
#    3 Hammer
#    2 BullishEngulfing
```

#### Streaming Buffer Activity

```bash
# View buffer flush cycles
grep "STREAMING-BUFFER: Flush cycle" logs/tickstock.log

# Example:
# 2025-10-17 20:25:30 - STREAMING-BUFFER: Flush cycle completed (12 events: 7 patterns, 5 indicators)
```

#### Error Tracking

```bash
# View all errors
grep -E "ERROR|CRITICAL" logs/tickstock.log

# View Redis-specific errors
grep "REDIS.*ERROR" logs/tickstock.log

# View pattern detection errors
grep "PATTERN.*ERROR" logs/tickstock.log
```

### TickStockPL Logs

**Location**: `../TickStockPL/logs/tickstockpl.log` (or configured location)

### Key TickStockPL Log Patterns

```bash
# Pattern detection activity
grep "PATTERN-JOB:" ../TickStockPL/logs/tickstockpl.log | tail -20

# View bar processing
grep "Successfully detected.*patterns" ../TickStockPL/logs/tickstockpl.log

# Check bar buffer status
grep "bars in buffer" ../TickStockPL/logs/tickstockpl.log

# Example output:
# 2025-10-17 20:25:30 - PATTERN-JOB: AAPL has 3 bars in buffer
# 2025-10-17 20:25:30 - PATTERN-JOB: Successfully detected 2 patterns for AAPL in 15.42ms
```

---

## Performance Metrics

### Real-time Performance Monitoring

#### WebSocket Latency

```bash
# From browser console (F12):
# Calculate latency between server timestamp and client receipt

# In streaming dashboard JavaScript:
const serverTime = new Date(event.timestamp);
const clientTime = new Date();
const latency = clientTime - serverTime;
console.log('Latency:', latency, 'ms');

# Target: <100ms
```

#### Redis Operation Timing

```bash
# Monitor Redis latency
redis-cli --latency

# Output:
# min: 0, max: 1, avg: 0.12 (microseconds)

# Target: <10ms (10,000 microseconds)
```

#### Pattern Detection Timing

```bash
# Extract detection times from TickStockPL logs
grep "Successfully detected.*patterns.*in.*ms" ../TickStockPL/logs/tickstockpl.log | \
  grep -oP 'in \K[0-9.]+(?=ms)' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# Target: <50ms per symbol
```

#### Streaming Buffer Performance

```bash
# Count flush cycles and events
grep "STREAMING-BUFFER: Flush cycle completed" logs/tickstock.log | \
  grep -oP '\(\K[0-9]+(?= events)' | \
  awk '{sum+=$1; count++} END {print "Avg events/flush:", sum/count}'

# Target: 10-20 events per flush (250ms interval)
```

### Performance Targets (Sprint 42/43)

| Metric | Target | Measurement | Status |
|--------|--------|-------------|--------|
| Pattern Detection Start | <2 min | Time to first pattern in logs | ✅ 1-2 min |
| WebSocket Delivery | <100ms | Server timestamp → client receipt | ✅ ~50ms |
| Redis Publish | <10ms | `redis-cli --latency` | ✅ ~5ms |
| Streaming Buffer Flush | 250ms | Configured interval | ✅ 250ms |
| Pattern Detection | <50ms | TickStockPL log timings | ✅ ~15ms |

---

## Common Diagnostic Workflows

### Workflow 1: Verify Streaming is Working

**Goal**: Confirm end-to-end pattern/indicator flow

**Steps**:
1. Start Redis channel monitor: `python scripts/diagnostics/monitor_redis_channels.py`
2. Start TickStockPL streaming session
3. Start TickStockAppV2
4. Open Live Streaming dashboard: http://localhost:5000/streaming
5. Wait 1-2 minutes and verify:
   - ✅ Redis monitor shows messages
   - ✅ Dashboard displays patterns/indicators
   - ✅ Timestamps are recent

**Expected Result**: Messages flowing within 1-2 minutes

---

### Workflow 2: Diagnose Pattern Delay

**Goal**: Identify why patterns are delayed

**Steps**:
1. Check Redis channels: `python scripts/diagnostics/monitor_redis_channels.py`
2. If NO pattern messages after 5 minutes:
   - Check TickStockPL bar creation: `SELECT COUNT(*) FROM ohlcv_1min WHERE created_at > NOW() - INTERVAL '5 minutes';`
   - Check TickStockPL pattern job: `grep "PATTERN-JOB:" ../TickStockPL/logs/tickstockpl.log | tail -20`
   - Verify bar buffer: Look for "bars in buffer" messages
3. If pattern messages appear but dashboard doesn't show:
   - Check TickStockAppV2 Redis subscriber: `grep "REDIS-SUBSCRIBER" logs/tickstock.log`
   - Check streaming buffer: `grep "STREAMING-BUFFER" logs/tickstock.log`
   - Check WebSocket delivery: Browser console (F12) for errors

**Common Causes**:
- TickStockPL not creating bars (check TickAggregator)
- Pattern job not running (check TickStockPL logs)
- Insufficient bar history (Sprint 43 should fix to 1-2 bars)
- Redis connection issue (check connectivity)

---

### Workflow 3: Validate Sprint 43 Fix

**Goal**: Confirm pattern-specific bar requirements working

**Steps**:
1. Start fresh TickStockPL streaming session
2. Monitor TickStockPL logs: `tail -f ../TickStockPL/logs/tickstockpl.log | grep "PATTERN-JOB"`
3. Look for first pattern detection
4. Note the "bars in buffer" count when first pattern detected

**Expected Result** (Sprint 43):
- Single-bar patterns (Doji, Hammer): Detect at bar 1
- Multi-bar patterns (Engulfing): Detect at bar 2
- Old behavior (pre-Sprint 43): All patterns waited for bar 5

**Example Log Evidence**:
```
# Sprint 43 (CORRECT):
2025-10-17 20:25:01 - PATTERN-JOB: AAPL has 1 bars in buffer
2025-10-17 20:25:01 - PATTERN-JOB: Calling Doji.detect() for AAPL
2025-10-17 20:25:01 - PATTERN-JOB: Successfully detected 1 patterns for AAPL

# Old behavior (INCORRECT):
2025-10-15 15:30:05 - PATTERN-JOB: AAPL has 4 bars in buffer
2025-10-15 15:30:05 - PATTERN-JOB: Insufficient history for AAPL: 4 < 5
2025-10-15 15:30:05 - PATTERN-JOB: (No patterns detected - waiting for bar 5)
```

---

## Database Diagnostic Queries

### Check Pattern Detection History

```sql
-- Recent intraday patterns
SELECT
    symbol,
    pattern_type,
    confidence,
    detection_timestamp,
    timeframe,
    bar_close
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '30 minutes'
ORDER BY detection_timestamp DESC
LIMIT 50;
```

### Check OHLCV Bar Creation (Sprint 42)

```sql
-- Verify bars being created by TickStockPL
SELECT
    symbol,
    COUNT(*) as bar_count,
    MIN(timestamp) as first_bar,
    MAX(timestamp) as last_bar
FROM ohlcv_1min
WHERE created_at > NOW() - INTERVAL '10 minutes'
GROUP BY symbol
ORDER BY bar_count DESC;

-- Expected: ~70 symbols, 1-10 bars each depending on runtime
```

### Check Redis Event Flow

```sql
-- View system health metrics
SELECT
    metric_name,
    metric_value,
    timestamp
FROM system_metrics
WHERE metric_name IN ('redis_messages_received', 'pattern_events_processed')
AND timestamp > NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC;
```

---

## Environment Variables for Diagnostics

### Enable Enhanced Logging

```bash
# In .env file:

# Enable file logging
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/tickstock.log

# Enable debug-level logging (verbose)
LOG_LEVEL=DEBUG

# Enable Redis debug logging (Sprint 43)
REDIS_DEBUG_LOGGING=true

# Enable tracing for specific symbols
TRACE_ENABLED=true
TRACE_TICKERS=["AAPL","TSLA","NVDA"]
TRACE_LEVEL=VERBOSE
```

### Redis Channel Configuration

```bash
# Verify these are set correctly:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Channel names (should match TickStockPL)
REDIS_PATTERN_STREAMING_CHANNEL=tickstock:patterns:streaming
REDIS_PATTERN_DETECTED_CHANNEL=tickstock:patterns:detected
REDIS_INDICATOR_STREAMING_CHANNEL=tickstock:indicators:streaming
```

---

## Troubleshooting Reference

### Symptom: No patterns appearing in dashboard

**Check**:
1. Redis channels: `python scripts/diagnostics/monitor_redis_channels.py`
2. TickStockPL logs: `grep "PATTERN-JOB" ../TickStockPL/logs/tickstockpl.log`
3. Database: `SELECT COUNT(*) FROM ohlcv_1min WHERE created_at > NOW() - INTERVAL '5 minutes';`

**Likely Causes**:
- TickStockPL not running
- Pattern job not started
- Insufficient bar history (Sprint 43 fix needed)

---

### Symptom: Indicators work, patterns don't

**Check**:
1. Redis channels: Verify `tickstock:patterns:streaming` is silent
2. TickStockPL pattern job status
3. Bar buffer count in TickStockPL logs

**Likely Causes**:
- Pattern-specific issue in TickStockPL
- Bar requirement blocking (Sprint 43 issue)
- Pattern detection errors

---

### Symptom: 5-8 minute pattern delay

**Status**: ✅ FIXED in Sprint 43

**If still occurring**:
1. Verify Sprint 43 fix applied in TickStockPL
2. Check for "Insufficient history" messages in TickStockPL logs
3. Verify pattern-specific bar requirements in code

**Expected After Sprint 43**:
- Patterns appear within 1-2 minutes
- No "Insufficient history" warnings
- Bar buffer starts at 1-2 bars

---

## Related Documentation

- [Architecture Overview](../architecture/README.md) - System architecture with Sprint 42/43 changes
- [Sprint 42 Complete](../planning/sprints/sprint42/SPRINT42_COMPLETE.md) - OHLCV architecture changes
- [Sprint 43 Complete](../planning/sprints/sprint43/SPRINT43_COMPLETE.md) - Pattern delay fix details
- [Redis Integration](../architecture/redis-integration.md) - Redis pub-sub patterns

---

**Last Updated**: October 17, 2025 (Sprint 43)
**Status**: Active diagnostic tools in use
