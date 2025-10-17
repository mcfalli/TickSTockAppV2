# Redis Message Monitor Dashboard
**Sprint 43: Redis Communication Debugging Tool**

## Purpose

Comprehensive monitoring dashboard for debugging Redis pub-sub communication between TickStockPL (producer) and TickStockAppV2 (consumer).

## Problem Solved

Patterns and indicators were flowing through Redis but not displaying in UI due to field name inconsistencies between systems. This monitor provides:

1. **Full visibility** into every Redis message
2. **Structure analysis** showing exact field names used
3. **Field naming validation** detecting inconsistencies
4. **Real-time monitoring** with auto-refresh capability

## Access

**URL**: `http://localhost:5000/redis-monitor`

**Authentication**: Requires login

## Features

### 1. Statistics Dashboard
- **Total Messages**: Count of all captured messages
- **Messages/Second**: Real-time throughput
- **Pattern Events**: Count of pattern-related messages
- **Indicator Events**: Count of indicator-related messages

### 2. Field Name Analysis
Automatically detects field naming inconsistencies:
- ✅ **Consistent**: All messages use same field names
- ⚠️ **Inconsistent**: Multiple variations detected (e.g., `pattern` vs `pattern_type`)

### 3. Message List
Each message shows:
- **Channel**: Redis channel name (e.g., `tickstock:patterns:streaming`)
- **Event Type**: Event classification (e.g., `streaming_pattern`)
- **Summary**: Quick overview (Pattern/Indicator + Symbol)
- **Structure**: All field names at each nesting level
- **Field Name Highlight**: Shows exact field name used for patterns/indicators
- **Full JSON**: Expandable raw message data

### 4. Filtering
- **Channel Filter**: Show only specific channels (partial match)
- **Type Filter**: Filter by event type
- **Limit**: Control number of messages (50-500)

### 5. Controls
- **Refresh**: Manual refresh of data
- **Clear**: Reset all captured messages
- **Auto**: Toggle auto-refresh every 2 seconds

## Architecture

### Components Created

1. **`src/core/services/redis_monitor.py`**
   - `RedisMonitor` class
   - Captures all Redis messages
   - Analyzes message structure
   - Tracks field name variations
   - Provides statistics

2. **`src/api/rest/redis_monitor_routes.py`**
   - Flask Blueprint
   - API endpoints:
     - `GET /redis-monitor/` - Dashboard page
     - `GET /redis-monitor/api/messages` - Get messages
     - `GET /redis-monitor/api/stats` - Get statistics
     - `GET /redis-monitor/api/field-names` - Field analysis report
     - `POST /redis-monitor/api/clear` - Clear captured data

3. **`web/templates/redis_monitor.html`**
   - Interactive dashboard UI
   - Real-time updates
   - Message structure visualization
   - Field name highlighting

### Integration Points

**RedisEventSubscriber** (`src/core/services/redis_event_subscriber.py`):
```python
# Line 29: Import monitor
from src.core.services.redis_monitor import RedisMonitor

# Line 157: Initialize monitor
self.redis_monitor = RedisMonitor(max_messages=500)

# Lines 313-318: Capture every message
self.redis_monitor.capture_message(
    channel=channel,
    message_data=event_data,
    event_type=event_type.value
)
```

**App Registration** (`src/app.py:2267-2270`):
```python
from src.api.rest.redis_monitor_routes import redis_monitor_bp
app.register_blueprint(redis_monitor_bp)
```

## Usage Guide

### Step 1: Start Services
```bash
# Ensure both services are running
python start_all_services.py
```

### Step 2: Access Dashboard
1. Navigate to: `http://localhost:5000/redis-monitor`
2. Login if prompted

### Step 3: Monitor Messages
- Click **Auto** button to enable real-time updates
- Watch messages flow in from TickStockPL
- Observe field names and structure

### Step 4: Identify Issues
Look for:
- **Missing fields**: Summary shows "N/A" for pattern/indicator names
- **Wrong field names**: Structure shows unexpected field names
- **Inconsistent naming**: Alert banner at top warns of variations

### Step 5: Analyze Patterns
Filter to specific channels:
- `patterns:streaming` - Pattern detection events
- `indicators:streaming` - Indicator calculation events
- `health` - System health updates

## Field Name Standardization

### Current State (Sprint 43)

**TickStockPL sends**:
```json
{
  "detection": {
    "pattern": "PriceChange",          // ← Uses "pattern"
    "symbol": "NVDA",
    "confidence": 0.95
  }
}
```

**TickStockAppV2 expected**:
```python
pattern_type = detection.get('pattern_type')  # ← Looked for "pattern_type"
```

**Fix Applied**:
```python
# Now checks all variations
pattern_type = detection.get('pattern_type') or detection.get('pattern') or detection.get('pattern_name')
```

### Recommended Standard

For future consistency across ALL TickStock systems:

**Patterns**:
```json
{
  "detection": {
    "pattern_type": "PriceChange",    // Standard field name
    "symbol": "NVDA",
    "confidence": 0.95,
    "timestamp": "2025-10-16T...",
    "timeframe": "1min",
    "parameters": {}
  }
}
```

**Indicators**:
```json
{
  "calculation": {
    "indicator_type": "SMA5",          // Standard field name
    "symbol": "NVDA",
    "value": 123.45,
    "timestamp": "2025-10-16T...",
    "timeframe": "1min",
    "metadata": {}
  }
}
```

## API Reference

### GET /redis-monitor/api/messages

Query recent Redis messages.

**Parameters**:
- `limit` (optional): Number of messages (default: 50, max: 500)
- `channel` (optional): Filter by channel (partial match)
- `type` (optional): Filter by event type

**Response**:
```json
{
  "messages": [
    {
      "id": 123,
      "timestamp": "2025-10-16T05:48:18.529Z",
      "channel": "tickstock:patterns:streaming",
      "event_type": "streaming_pattern",
      "structure": {
        "summary": "Pattern: PriceChange on NVDA (0.95)",
        "top_level_keys": ["type", "detection"],
        "nested_keys": {
          "detection": ["pattern", "symbol", "confidence", "timestamp"]
        },
        "pattern_field_name": "pattern"
      },
      "data": { ... },
      "raw_json": "..."
    }
  ],
  "count": 50
}
```

### GET /redis-monitor/api/stats

Get monitoring statistics.

**Response**:
```json
{
  "total_messages": 1234,
  "messages_per_second": 5.67,
  "by_channel": {
    "tickstock:patterns:streaming": 456,
    "tickstock:indicators:streaming": 778
  },
  "by_type": {
    "streaming_pattern": 456,
    "streaming_indicator": 778
  },
  "field_names_seen": {
    "patterns": ["pattern", "symbol", "confidence"],
    "indicators": ["indicator", "symbol", "value"]
  }
}
```

### GET /redis-monitor/api/field-names

Get field naming consistency report.

**Response**:
```json
{
  "patterns": {
    "all_fields": ["pattern", "symbol", "confidence", "timestamp"],
    "name_field_variations": ["pattern"],
    "has_inconsistency": false
  },
  "indicators": {
    "all_fields": ["indicator", "symbol", "value", "timestamp"],
    "name_field_variations": ["indicator"],
    "has_inconsistency": false
  },
  "recommendation": "✅ Field naming is consistent across messages."
}
```

## Troubleshooting

### No Messages Appearing

**Check**:
1. Is TickStockPL running? (`ps aux | grep python`)
2. Is Redis running? (`redis-cli ping`)
3. Are services connected? (Check `/streaming/api/status`)

### Messages Show But UI Doesn't Update

**Check**:
1. Browser console for JavaScript errors
2. Redis monitor shows correct field names?
3. Compare actual vs expected field names in structure

### Field Name Inconsistencies

**Solution**:
1. Note field names from monitor
2. Update consuming code to check all variations
3. OR update TickStockPL to use standard names

## Performance

- **Memory**: Stores last 500 messages (~500KB)
- **CPU**: Minimal overhead (message copying only)
- **Network**: API calls on-demand only
- **Auto-refresh**: 2-second interval (low impact)

## Security

- **Authentication**: Requires login (`@require_auth`)
- **Read-only**: Cannot modify Redis data
- **Local only**: No external exposure

## Future Enhancements

1. **Message Search**: Search by symbol, pattern name
2. **Export**: Download messages as JSON/CSV
3. **Alerts**: Notify on field name changes
4. **Historical**: Store messages to database
5. **Comparison**: Side-by-side message comparison

## Related Documents

- `docs/planning/sprints/sprint43/ROOT_CAUSE_PATTERN_DELAY.md` - Original issue
- `docs/planning/sprints/sprint43/PATTERN_FIELD_NAME_FIX.md` - Pattern field fix
- `docs/planning/sprints/sprint43/INDICATOR_FIELD_NAME_FIX.md` - Indicator field fix
- `src/core/services/redis_event_subscriber.py` - Redis subscriber
- `src/core/services/streaming_buffer.py` - Streaming buffer

---

**Status**: ✅ COMPLETE - Ready for production use

**Created**: 2025-10-16
**Sprint**: 43
**Author**: Redis Integration Specialist + Claude Code
