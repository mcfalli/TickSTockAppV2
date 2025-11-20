# TickStockPL Requirements for Sprint 40 - Live Streaming Dashboard

**Version**: 1.0
**Date**: October 5, 2025
**Owner**: TickStockPL Developer
**Consumer**: TickStockAppV2 Live Streaming Dashboard

---

## Overview

TickStockAppV2's Live Streaming dashboard requires real-time event data from TickStockPL streaming services. This document specifies the **exact requirements** for event publishing, data formats, and performance expectations.

**Status**: ✅ = Implemented | ⏳ = In Progress | ❌ = Not Implemented

---

## Architecture Reminder

```
┌─────────────────────┐         ┌──────────────────────┐
│   TickStockPL       │         │  TickStockAppV2      │
│   (Producer)        │─Redis─>│  (Consumer)          │
│                     │ Pub/Sub │                      │
│  Streaming Service  │────────>│  Live Streaming Page │
│  Pattern Detection  │         │  WebSocket → Browser │
│  Health Monitor     │         │                      │
└─────────────────────┘         └──────────────────────┘
```

**Communication Model**: Loose coupling via Redis pub/sub
**Performance Target**: End-to-end latency <100ms (Redis publish → Browser display)

---

## Required Redis Channels (8 Total)

### 1. Session Lifecycle Events

#### Channel: `tickstock:streaming:session_started`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Market open (9:30 AM ET)
- Manual streaming start via admin trigger

**Event Structure**:
```json
{
  "type": "streaming_session_started",
  "session": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "universe": "market_leaders:top_500",
    "started_at": "2025-10-05T09:30:00.000Z",
    "symbol_count": 500,
    "status": "active"
  },
  "timestamp": "2025-10-05T09:30:00.000Z"
}
```

**Required Fields**:
- `session_id` (string, UUID): Unique session identifier
- `universe` (string): Symbol universe key (e.g., "market_leaders:top_500")
- `started_at` (string, ISO 8601): Session start timestamp in UTC
- `symbol_count` (integer): Number of symbols in universe
- `status` (string): Always "active"

**Notes**:
- Session ID should be unique per day (recommend: date-based UUID)
- Timestamp must be UTC (ISO 8601 format)

---

#### Channel: `tickstock:streaming:session_stopped`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Market close (4:00 PM ET)
- Manual streaming stop via admin trigger
- Critical system failure

**Event Structure**:
```json
{
  "type": "streaming_session_stopped",
  "session": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "stopped_at": "2025-10-05T16:00:00.000Z",
    "duration_seconds": 23400,
    "total_patterns": 1250,
    "total_indicators": 45000,
    "final_status": "completed"
  },
  "timestamp": "2025-10-05T16:00:00.000Z"
}
```

**Required Fields**:
- `session_id` (string, UUID): Same as session_started
- `stopped_at` (string, ISO 8601): Session end timestamp in UTC
- `duration_seconds` (integer): Total session duration
- `total_patterns` (integer): Total patterns detected during session
- `total_indicators` (integer): Total indicator calculations
- `final_status` (string): "completed", "stopped", "failed"

---

### 2. Real-time Pattern Detection

#### Channel: `tickstock:patterns:streaming`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Immediately after pattern detected on 1-minute bar
- Batch publishing acceptable (max 50 patterns per batch)

**Event Structure (Single Pattern)**:
```json
{
  "type": "streaming_pattern",
  "detection": {
    "symbol": "NVDA",
    "pattern_type": "Doji",
    "confidence": 0.85,
    "timestamp": "2025-10-05T10:15:00.000Z",
    "timeframe": "1min",
    "bar_data": {
      "open": 125.50,
      "high": 125.75,
      "low": 125.45,
      "close": 125.52,
      "volume": 250000
    },
    "metadata": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "detection_method": "DynamicPatternIndicatorLoader",
      "pattern_id": "uuid-pattern-specific"
    }
  }
}
```

**Event Structure (Batch)**:
```json
{
  "type": "streaming_patterns_batch",
  "patterns": [
    {
      "symbol": "NVDA",
      "pattern_type": "Doji",
      "confidence": 0.85,
      "timestamp": "2025-10-05T10:15:00.000Z",
      ...
    },
    {
      "symbol": "TSLA",
      "pattern_type": "Hammer",
      "confidence": 0.78,
      "timestamp": "2025-10-05T10:15:00.000Z",
      ...
    }
  ],
  "count": 2,
  "batch_timestamp": "2025-10-05T10:15:01.000Z"
}
```

**Required Fields**:
- `symbol` (string): Stock symbol (uppercase)
- `pattern_type` (string): Pattern name (e.g., "Doji", "Hammer")
- `confidence` (float): 0.0 to 1.0 (0% to 100%)
- `timestamp` (string, ISO 8601): Detection time in UTC
- `timeframe` (string): Always "1min" for streaming
- `bar_data.open/high/low/close` (float): OHLC prices
- `bar_data.volume` (integer): Volume

**Performance Requirement**:
- Publish within 100ms of detection
- Batch size: 1-50 patterns

---

#### Channel: `tickstock:patterns:detected`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Same as `tickstock:patterns:streaming` BUT only for high-confidence patterns

**Filter Rule**: `confidence >= 0.8` (80% or higher)

**Event Structure**: Same as `tickstock:patterns:streaming`

**Purpose**: Separate channel for high-priority patterns (may add alerts/notifications later)

---

### 3. Indicator Calculations

#### Channel: `tickstock:indicators:streaming`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- After each 1-minute bar close
- For each active symbol
- For each enabled indicator (RSI, SMA, MACD, etc.)

**Event Structure**:
```json
{
  "type": "streaming_indicator",
  "calculation": {
    "symbol": "TSLA",
    "indicator": "RSI",
    "value": 72.5,
    "timestamp": "2025-10-05T10:15:00.000Z",
    "timeframe": "1min",
    "metadata": {
      "period": 14,
      "overbought_threshold": 70,
      "oversold_threshold": 30
    }
  }
}
```

**Required Fields**:
- `symbol` (string): Stock symbol
- `indicator` (string): Indicator name ("RSI", "SMA", "MACD", "BB", etc.)
- `value` (float): Calculated indicator value
- `timestamp` (string, ISO 8601): Calculation time in UTC
- `timeframe` (string): Always "1min"
- `metadata` (object): Indicator-specific parameters

**Supported Indicators** (Minimum):
- RSI (Relative Strength Index)
- SMA (Simple Moving Average) - 20, 50, 200 periods
- MACD (Moving Average Convergence Divergence)
- BB (Bollinger Bands)

**Performance Requirement**:
- Publish within 100ms of bar close

---

### 4. Indicator Alerts

#### Channel: `tickstock:alerts:indicators`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- When indicator crosses threshold
- Immediately upon detection

**Event Structure**:
```json
{
  "type": "indicator_alert",
  "alert": {
    "symbol": "AAPL",
    "alert_type": "RSI_OVERBOUGHT",
    "timestamp": "2025-10-05T11:30:00.000Z",
    "data": {
      "indicator": "RSI",
      "value": 75.2,
      "threshold": 70,
      "direction": "above"
    },
    "severity": "warning"
  }
}
```

**Required Alert Types**:
1. `RSI_OVERBOUGHT` - RSI > 70
2. `RSI_OVERSOLD` - RSI < 30
3. `MACD_BULLISH_CROSS` - MACD crosses above signal line
4. `MACD_BEARISH_CROSS` - MACD crosses below signal line
5. `BB_UPPER_BREAK` - Price breaks above upper Bollinger Band
6. `BB_LOWER_BREAK` - Price breaks below lower Bollinger Band

**Required Fields**:
- `symbol` (string): Stock symbol
- `alert_type` (string): One of the 6 types above
- `timestamp` (string, ISO 8601): Alert time in UTC
- `data.indicator` (string): Indicator name
- `data.value` (float): Current indicator value
- `data.threshold` (float): Threshold that was crossed
- `severity` (string): "info", "warning", "critical"

**Performance Requirement**:
- Publish within 50ms of threshold cross

---

### 5. System Health Monitoring

#### Channel: `tickstock:streaming:health`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Every 60 seconds during active streaming session
- Immediately when status changes (healthy → warning → critical)

**Event Structure**:
```json
{
  "type": "streaming_health",
  "health": {
    "status": "healthy",
    "timestamp": "2025-10-05T10:15:00.000Z",
    "active_symbols": 485,
    "connection_status": "connected",
    "data_flow": {
      "ticks_per_second": 125.3,
      "bars_per_minute": 480,
      "processing_lag_ms": 45
    },
    "resource_usage": {
      "cpu_percent": 35.2,
      "memory_mb": 512,
      "threads_active": 8
    },
    "issues": []
  }
}
```

**Required Fields**:
- `status` (string): "healthy", "warning", "critical"
- `timestamp` (string, ISO 8601): Health check time
- `active_symbols` (integer): Currently active symbol count
- `connection_status` (string): "connected", "disconnected", "reconnecting"
- `data_flow.ticks_per_second` (float): Average tick rate
- `data_flow.bars_per_minute` (integer): Minute bars processed
- `data_flow.processing_lag_ms` (integer): Processing latency in milliseconds
- `resource_usage.cpu_percent` (float): CPU usage (0-100)
- `resource_usage.memory_mb` (integer): Memory usage in MB
- `issues` (array): List of current issues (empty if healthy)

**Status Determination Logic**:
- `healthy`: All metrics within normal range
- `warning`: Non-critical issue (e.g., high CPU >70%, lag >200ms)
- `critical`: System failure (e.g., WebSocket disconnected, lag >1000ms)

**Issues Array Example**:
```json
"issues": [
  "High CPU usage: 85%",
  "Processing lag above threshold: 250ms"
]
```

---

### 6. Critical Alerts

#### Channel: `tickstock:alerts:critical`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**When to Publish**:
- Immediate system failures
- Critical errors requiring attention
- Recovery notifications

**Event Structure**:
```json
{
  "type": "critical_alert",
  "alert": {
    "severity": "critical",
    "message": "WebSocket connection lost to Massive",
    "timestamp": "2025-10-05T12:45:00.000Z",
    "component": "polygon_websocket",
    "action_required": "Manual intervention needed - check API credentials",
    "recovery": null
  }
}
```

**Required Fields**:
- `severity` (string): "warning", "error", "critical"
- `message` (string): Human-readable error description
- `timestamp` (string, ISO 8601): Alert time
- `component` (string): Component that failed
- `action_required` (string): What needs to be done
- `recovery` (string|null): Recovery message if issue resolved

**Recovery Event Example**:
```json
{
  "type": "critical_alert",
  "alert": {
    "severity": "info",
    "message": "WebSocket connection restored",
    "timestamp": "2025-10-05T12:50:00.000Z",
    "component": "polygon_websocket",
    "action_required": null,
    "recovery": "Connection re-established successfully after 5 minutes"
  }
}
```

---

## Database Tables (TickStockPL)

These tables should be populated with data during streaming. TickStockAppV2 may query them for historical data.

### Table: `streaming_sessions`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**Purpose**: Track streaming session lifecycle

**Schema** (Expected):
```sql
CREATE TABLE streaming_sessions (
    session_id UUID PRIMARY KEY,
    universe VARCHAR(100) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    stopped_at TIMESTAMP WITH TIME ZONE,
    symbol_count INTEGER NOT NULL,
    total_patterns INTEGER DEFAULT 0,
    total_indicators INTEGER DEFAULT 0,
    final_status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**TickStockAppV2 Usage**:
- Query most recent session via `/api/streaming/status`
- Display session history in admin dashboard

---

### Table: `intraday_patterns`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**Purpose**: Store real-time pattern detections

**Schema** (Expected):
```sql
CREATE TABLE intraday_patterns (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES streaming_sessions(session_id),
    symbol VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe VARCHAR(10) DEFAULT '1min',
    bar_open DECIMAL(12,2),
    bar_high DECIMAL(12,2),
    bar_low DECIMAL(12,2),
    bar_close DECIMAL(12,2),
    bar_volume BIGINT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_intraday_patterns_symbol ON intraday_patterns(symbol);
CREATE INDEX idx_intraday_patterns_detected_at ON intraday_patterns(detected_at DESC);
```

**TickStockAppV2 Usage**:
- Query pattern history via `/api/streaming/patterns/<symbol>`
- Limit to last 100 patterns per symbol

---

### Table: `intraday_indicators`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**Purpose**: Store indicator calculations

**Schema** (Expected):
```sql
CREATE TABLE intraday_indicators (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES streaming_sessions(session_id),
    symbol VARCHAR(10) NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DECIMAL(12,4) NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe VARCHAR(10) DEFAULT '1min',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_intraday_indicators_symbol ON intraday_indicators(symbol);
CREATE INDEX idx_intraday_indicators_calculated_at ON intraday_indicators(calculated_at DESC);
```

**TickStockAppV2 Usage**:
- Display recent indicator values in UI
- Query last 50 values per symbol/indicator

---

### Table: `streaming_health_metrics`
**Status**: ___ (Please fill in: ✅/⏳/❌)

**Purpose**: Store health monitoring snapshots

**Schema** (Expected):
```sql
CREATE TABLE streaming_health_metrics (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES streaming_sessions(session_id),
    status VARCHAR(20) NOT NULL,
    active_symbols INTEGER,
    ticks_per_second DECIMAL(10,2),
    bars_per_minute INTEGER,
    processing_lag_ms INTEGER,
    cpu_percent DECIMAL(5,2),
    memory_mb INTEGER,
    issues JSONB,
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_streaming_health_measured_at ON streaming_health_metrics(measured_at DESC);
```

**TickStockAppV2 Usage**:
- Display current health status
- Query health history for troubleshooting

---

## Performance Requirements Summary

| Metric | Target | Critical |
|--------|--------|----------|
| Redis Publish Latency | <50ms | <100ms |
| Event Processing Rate | 1000+ events/sec | 500+ events/sec |
| Health Update Frequency | 60 seconds | 120 seconds |
| Pattern Detection Latency | <100ms | <200ms |
| Indicator Calculation Latency | <100ms | <200ms |
| Database Write Latency | <50ms | <100ms |

**End-to-End Latency** (Pattern detected → Browser display):
- **Target**: <100ms
- **Acceptable**: <200ms
- **Critical**: >500ms

---

## Testing Coordination

### Pre-Testing Requirements

Before TickStockAppV2 testing, please confirm:

1. [ ] **All 8 Redis channels publishing** during market hours
2. [ ] **Database tables exist** and are being populated
3. [ ] **Sample events** match specifications above
4. [ ] **Health monitoring** operational (60-second updates)
5. [ ] **Session lifecycle** events triggered at market open/close

### Test Data Scenarios

For comprehensive testing, we need:

#### Scenario 1: Normal Operation (30 minutes)
- 500 active symbols
- 50-100 patterns detected
- 20-30 indicator alerts
- Health status: "healthy"
- No errors

#### Scenario 2: High Volume (15 minutes)
- 1000+ patterns/minute
- 100+ indicator alerts/minute
- Test TickStockAppV2 performance under load

#### Scenario 3: Error Recovery (15 minutes)
- Simulate WebSocket disconnect (publish critical alert)
- Reconnect after 2 minutes (publish recovery)
- Verify TickStockAppV2 handles gracefully

#### Scenario 4: Market Close
- Publish session_stopped event
- Verify final metrics (total_patterns, total_indicators)
- Confirm session written to database

### Mock Data (If Streaming Not Available)

If live streaming is unavailable, please provide:
- Python script to publish mock events to Redis
- 100 sample patterns (various symbols/types)
- 50 sample indicator alerts
- 10 health snapshots (varying status)
- Session lifecycle events (start/stop)

**Mock data location**: Provide in TickStockPL repository under `/tests/mock_data/`

---

## Communication

### Questions for TickStockPL Developer

1. **What is currently implemented?**
   - Please mark status (✅/⏳/❌) for each channel above
   - Which database tables exist and are populated?

2. **What needs to be implemented?**
   - List any missing channels or features
   - Estimated timeline for completion?

3. **Testing availability**
   - When can we schedule live testing during market hours?
   - Can you provide mock data if live testing unavailable?

4. **Known issues or limitations**
   - Are there any performance bottlenecks?
   - Any channels with incomplete data?

5. **Monitoring**
   - How can we verify TickStockPL is publishing events?
   - Redis monitoring commands or logs?

### Response Template

Please fill out and return:

```markdown
## TickStockPL Streaming Status Report

**Date**: [DATE]
**Reporter**: [YOUR NAME]

### Channel Implementation Status

1. tickstock:streaming:session_started: [✅/⏳/❌] - [Notes]
2. tickstock:streaming:session_stopped: [✅/⏳/❌] - [Notes]
3. tickstock:streaming:health: [✅/⏳/❌] - [Notes]
4. tickstock:patterns:streaming: [✅/⏳/❌] - [Notes]
5. tickstock:patterns:detected: [✅/⏳/❌] - [Notes]
6. tickstock:indicators:streaming: [✅/⏳/❌] - [Notes]
7. tickstock:alerts:indicators: [✅/⏳/❌] - [Notes]
8. tickstock:alerts:critical: [✅/⏳/❌] - [Notes]

### Database Tables Status

1. streaming_sessions: [✅/⏳/❌] - [Notes]
2. intraday_patterns: [✅/⏳/❌] - [Notes]
3. intraday_indicators: [✅/⏳/❌] - [Notes]
4. streaming_health_metrics: [✅/⏳/❌] - [Notes]

### Testing Availability

- Live testing available: [YES/NO]
- Proposed date/time: [DATE/TIME]
- Mock data available: [YES/NO]
- Mock data location: [PATH]

### Known Issues

[List any issues, limitations, or concerns]

### Questions for TickStockAppV2

[Any questions or clarifications needed?]
```

---

## Verification Commands (For Testing)

### Redis Monitoring
```bash
# Monitor all streaming channels
redis-cli PSUBSCRIBE "tickstock:streaming:*" "tickstock:patterns:*" "tickstock:indicators:*" "tickstock:alerts:*"

# Check specific channel
redis-cli SUBSCRIBE "tickstock:patterns:streaming"

# Publish test event (for testing)
redis-cli PUBLISH "tickstock:patterns:streaming" '{"type":"streaming_pattern","detection":{"symbol":"TEST","pattern_type":"Doji","confidence":0.9}}'
```

### Database Queries
```sql
-- Check recent session
SELECT * FROM streaming_sessions ORDER BY started_at DESC LIMIT 1;

-- Check pattern count
SELECT COUNT(*) FROM intraday_patterns WHERE detected_at > NOW() - INTERVAL '1 hour';

-- Check health status
SELECT status, active_symbols, measured_at
FROM streaming_health_metrics
ORDER BY measured_at DESC
LIMIT 10;
```

---

## Success Criteria

Sprint 40 is successful when:

1. ✅ All 8 Redis channels publishing valid events
2. ✅ All 4 database tables populated with data
3. ✅ TickStockAppV2 Live Streaming page displays real-time data
4. ✅ End-to-end latency <100ms (95th percentile)
5. ✅ Health monitoring accurate and updating every 60 seconds
6. ✅ Session lifecycle events trigger correctly at market hours
7. ✅ Integration tests pass with live data
8. ✅ No critical errors during 1-hour streaming session

---

**Document Version**: 1.0
**Last Updated**: October 5, 2025
**Contact**: TickStockAppV2 Development Team
