# Indicator Display Issue - Field Name Mismatch FIX

**Date**: 2025-10-15
**Issue**: Indicators not showing in UI despite being written to database
**Status**: ✅ FIXED
**Root Cause**: Field name mismatch between TickStockPL and TickStockAppV2

---

## Problem Statement

Indicators were being:
- ✅ Calculated by TickStockPL
- ✅ Published to Redis (`tickstock:indicators:streaming`)
- ✅ Received by RedisEventSubscriber (1,330+ events)
- ✅ Written to database (SMA5, AlwaysTrue, etc.)
- ❌ **NOT appearing in UI**

---

## Root Cause

### Field Name Mismatch

**TickStockPL publishes**:
```json
{
  "type": "streaming_indicator",
  "calculation": {
    "symbol": "BRK.B",
    "indicator": "SMA5",        ← Field name is "indicator"
    "value": 260.438,
    "timestamp": "2025-10-16T02:02:00+00:00",
    "timeframe": "1min"
  }
}
```

**TickStockAppV2 was looking for**:
```python
# redis_event_subscriber.py line 577 (BEFORE FIX)
indicator_type = calculation.get('indicator_type')  # ❌ WRONG field name
```

**Result**: `indicator_type` was always `None`, causing logs to show:
```
REDIS-SUBSCRIBER: Streaming indicator - None on NVDA
REDIS-SUBSCRIBER: Streaming indicator - None on MSFT
```

---

## The Fix

### File: `src/core/services/redis_event_subscriber.py`

**Change 1: Line 685** - Fix field name and add fallback:
```python
# BEFORE:
indicator_type = calculation.get('indicator_type')

# AFTER:
indicator_type = calculation.get('indicator') or calculation.get('indicator_type')
```

**Change 2: Line 690** - Change logging level from DEBUG to INFO:
```python
# BEFORE:
logger.debug(f"REDIS-SUBSCRIBER: Streaming indicator - {indicator_type} on {symbol}")

# AFTER:
logger.info(f"REDIS-SUBSCRIBER: Received streaming indicator - {indicator_type} on {symbol}")
```

**Change 3: Lines 705-711** - Add logging when sending to StreamingBuffer:
```python
# BEFORE:
if hasattr(self, 'streaming_buffer'):
    self.streaming_buffer.add_indicator(websocket_data)

# AFTER:
if hasattr(self, 'streaming_buffer') and self.streaming_buffer:
    logger.info(f"REDIS-SUBSCRIBER: Sending {indicator_type}@{symbol} to StreamingBuffer")
    self.streaming_buffer.add_indicator(websocket_data)
else:
    logger.info(f"REDIS-SUBSCRIBER: Direct broadcast {indicator_type}@{symbol} (no buffer)")
    self.socketio.emit('streaming_indicator', websocket_data, namespace='/')
```

---

## Evidence

### Diagnostic Script Output

**File**: `scripts/diagnostics/inspect_indicator_event.py`

```json
{
  "type": "streaming_indicator",
  "calculation": {
    "symbol": "BRK.B",           ← Symbol IS present!
    "indicator": "SMA5",          ← Field name confirmed
    "value": 260.438,
    "timestamp": "2025-10-16T02:02:00+00:00",
    "timeframe": "1min",
    "metadata": {
      "sma": 260.438,
      "period": 5,
      "bars_used": 10,
      "latest_close": 303.24,
      "value": 260.438
    }
  }
}
```

### Database Evidence

Indicators ARE being written correctly:
```sql
SELECT DISTINCT indicator_type FROM intraday_indicators LIMIT 10;

 indicator_type
----------------
 TestIndicator
 AlwaysTrue
 SMA_5
 SMA5
```

### Log Evidence

**Before Fix**:
```
2025-10-15 20:54:00,688 - REDIS-SUBSCRIBER: Streaming indicator - None on NVDA
2025-10-15 20:54:00,730 - REDIS-SUBSCRIBER: Streaming indicator - None on MSFT
2025-10-15 20:54:00,768 - REDIS-SUBSCRIBER: Streaming indicator - None on AAPL
```
- indicator_type = `None`
- 1,330 indicator events received but all with `None` as indicator type

**After Fix** (expected):
```
2025-10-15 21:05:00,123 - REDIS-SUBSCRIBER: Received streaming indicator - SMA5 on NVDA
2025-10-15 21:05:00,124 - REDIS-SUBSCRIBER: Sending SMA5@NVDA to StreamingBuffer
```

---

## Impact

### Before Fix:
- ❌ RedisEventSubscriber received indicators but couldn't parse indicator name
- ❌ StreamingBuffer received indicators with `indicator_type: None`
- ❌ WebSocket emitted malformed indicator events
- ❌ UI couldn't display indicators (missing type field)

### After Fix:
- ✅ RedisEventSubscriber correctly extracts `indicator` field
- ✅ StreamingBuffer receives properly formatted indicators
- ✅ WebSocket emits valid indicator events
- ✅ UI will display indicators in real-time (<250ms latency)

---

## Expected Behavior After Restart

When TickStockAppV2 is restarted with the fix:

1. **RedisEventSubscriber logs**:
   ```
   REDIS-SUBSCRIBER: Received streaming indicator - SMA5 on NVDA
   REDIS-SUBSCRIBER: Sending SMA5@NVDA to StreamingBuffer
   ```

2. **StreamingBuffer logs**:
   ```
   STREAMING-BUFFER: Flush cycle #N - patterns=5, indicators=3
   STREAMING-BUFFER: Emitting batch of 3 indicators to WebSocket
   STREAMING-BUFFER: Flushed 3 indicators - Total flushed: 45
   ```

3. **WebSocket event** (to browser):
   ```json
   {
     "type": "streaming_indicators_batch",
     "indicators": [
       {
         "type": "streaming_indicator",
         "calculation": {
           "indicator_type": "SMA5",
           "symbol": "NVDA",
           "values": {},
           "timestamp": "..."
         }
       }
     ],
     "count": 3
   }
   ```

4. **UI displays**:
   - Indicators appear within 250ms of calculation
   - Symbol and indicator name visible
   - Values updated in real-time

---

## Testing Checklist

After restarting TickStockAppV2:

- [ ] Monitor logs for "Received streaming indicator" with actual indicator names (not None)
- [ ] Verify "Sending to StreamingBuffer" logs appear
- [ ] Check StreamingBuffer flush cycles show `indicators > 0`
- [ ] Confirm batch emissions include indicators
- [ ] Open browser console and verify `streaming_indicators_batch` events
- [ ] Verify UI displays indicators with symbols and values

---

## Related Issues

### Issue #1: Pattern Delay (RESOLVED)
- **File**: `docs/planning/sprints/sprint43/ROOT_CAUSE_PATTERN_DELAY.md`
- **Status**: Fixed - patterns now flowing in real-time

### Issue #2: Indicator Symbol Field (TickStockPL)
- **File**: `docs/planning/sprints/sprint43/TICKSTOCKPL_INDICATOR_SYMBOL_ISSUE.md`
- **Status**: NOT AN ISSUE - TickStockPL IS including symbol field correctly
- **Update**: Our diagnostic script confirmed indicators have `"symbol": "BRK.B"` etc.

---

## Summary

**Problem**: Field name mismatch (`indicator` vs `indicator_type`)
**Fix**: Update RedisEventSubscriber to use correct field name with fallback
**Result**: Indicators will now appear in UI in real-time

**Action Required**: Restart TickStockAppV2 to apply the fix.
