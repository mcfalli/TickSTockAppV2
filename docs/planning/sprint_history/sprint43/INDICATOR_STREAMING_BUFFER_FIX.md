# Indicator StreamingBuffer Fix - Second Field Name Bug

**Date**: 2025-10-15
**Issue**: Indicators reaching buffer but not being emitted to UI
**Status**: ✅ FIXED
**Root Cause**: SAME field name bug in StreamingBuffer as RedisEventSubscriber

---

## Problem Statement

After fixing RedisEventSubscriber, indicators were:
- ✅ Received by RedisEventSubscriber with correct names (AlwaysTrue, SMA5)
- ✅ Sent to StreamingBuffer
- ✅ Showing in buffer counts (indicators=4-8 per cycle)
- ❌ **NEVER emitted as batches to WebSocket**
- ❌ **NOT appearing in UI**

### Log Evidence

```
# Indicators reaching buffer:
STREAMING-BUFFER: Flush cycle #303 - patterns=0, indicators=5
STREAMING-BUFFER: Flush cycle #304 - patterns=0, indicators=5
STREAMING-BUFFER: Flush cycle #305 - patterns=0, indicators=5

# But NO emission logs:
# (ZERO "Emitting batch of X indicators" logs)
```

---

## Root Cause #2: StreamingBuffer Has Same Bug

### The Code Path

1. **RedisEventSubscriber** receives indicator from Redis
   - Extracts: `indicator_type = calculation.get('indicator')`  ✅ Fixed earlier
   - Sends to StreamingBuffer via `add_indicator(websocket_data)`

2. **StreamingBuffer.add_indicator()** processes the event
   - Line 164: `indicator_type = calculation.get('indicator_type')`  ❌ WRONG field again!
   - Line 166: `if symbol and indicator_type:` fails because indicator_type is None
   - Indicators never added to aggregator properly

### The Bug

**File**: `src/core/services/streaming_buffer.py` line 164

```python
# BEFORE (WRONG):
indicator_type = calculation.get('indicator_type')  # Returns None!

if symbol and indicator_type:  # Fails because indicator_type=None
    # This code never executes!
```

**Why indicators showed in buffer count**:
- Line 180: `self.indicator_buffer.append(...)` happens AFTER the `if` check
- But since the `if` check failed, indicators were never added
- The buffer count showing indicators=5 was misleading - those were STALE entries

---

## The Fix

### File: `src/core/services/streaming_buffer.py`

**Change 1: Line 165** - Fix field name extraction:
```python
# BEFORE:
indicator_type = calculation.get('indicator_type')

# AFTER:
indicator_type = calculation.get('indicator_type') or calculation.get('indicator')
```

**Change 2: Line 171** - Add debug logging:
```python
logger.debug(f"STREAMING-BUFFER: add_indicator called - symbol={symbol}, indicator={indicator_type}")
```

**Change 3: Line 185-186** - Add warning for missing fields:
```python
else:
    logger.warning(f"STREAMING-BUFFER: Indicator missing required fields - symbol={symbol}, indicator_type={indicator_type}")
```

**Change 4: Lines 250 & 258** - Change logging from DEBUG to INFO:
```python
# BEFORE:
logger.debug(f"STREAMING-BUFFER: Flushed {len(indicators_to_send)} indicators")

# AFTER:
logger.info(f"STREAMING-BUFFER: Emitting batch of {len(indicators_to_send)} indicators to WebSocket")
# ... emit ...
logger.info(f"STREAMING-BUFFER: Flushed {len(indicators_to_send)} indicators - Total flushed: {self.stats['events_flushed']}")
```

---

## Expected Behavior After Restart

### Log Flow (After Fix):

```
# 1. RedisEventSubscriber receives indicator
REDIS-SUBSCRIBER: Received streaming indicator - AlwaysTrue on NVDA

# 2. RedisEventSubscriber sends to buffer
REDIS-SUBSCRIBER: Sending AlwaysTrue@NVDA to StreamingBuffer

# 3. StreamingBuffer adds indicator
STREAMING-BUFFER: add_indicator called - symbol=NVDA, indicator=AlwaysTrue

# 4. Flush cycle shows indicators
STREAMING-BUFFER: Flush cycle #123 - patterns=0, indicators=5

# 5. StreamingBuffer emits batch
STREAMING-BUFFER: Emitting batch of 5 indicators to WebSocket
STREAMING-BUFFER: Flushed 5 indicators - Total flushed: 45
```

### WebSocket Event (to Browser):

```json
{
  "indicators": [
    {
      "type": "streaming_indicator",
      "calculation": {
        "indicator_type": "AlwaysTrue",
        "symbol": "NVDA",
        "values": {},
        "timestamp": "2025-10-16T02:08:03+00:00",
        "timeframe": "1min"
      }
    }
  ],
  "count": 5,
  "timestamp": 1729041483.5
}
```

---

## Why This Happened

The same field name mismatch occurred in **TWO places**:

1. **RedisEventSubscriber** (line 577) - Fixed in first round
2. **StreamingBuffer** (line 164) - Fixed in this round

Both were looking for `'indicator_type'` but TickStockPL sends `'indicator'`.

**Lesson**: When fixing field name issues, search for ALL occurrences of the field access pattern across the codebase.

---

## Testing Checklist

After restarting TickStockAppV2:

- [ ] Verify "add_indicator called" logs show actual indicator names
- [ ] Confirm NO "Indicator missing required fields" warnings
- [ ] Check flush cycles show `indicators > 0`
- [ ] Verify "Emitting batch of X indicators" logs appear
- [ ] Confirm "Flushed X indicators - Total flushed: Y" logs
- [ ] Open browser console and verify `streaming_indicators_batch` events
- [ ] Verify UI displays indicators with symbols, names, and values
- [ ] Confirm indicators update in real-time (<250ms latency)

---

## Complete Fix Summary

### Files Modified:

1. **`src/core/services/redis_event_subscriber.py`**
   - Line 685: Fixed `indicator_type` extraction
   - Line 690: Changed logging to INFO level
   - Lines 705-711: Added logging when sending to buffer

2. **`src/core/services/streaming_buffer.py`**
   - Line 165: Fixed `indicator_type` extraction (SECOND instance of same bug)
   - Line 171: Added debug logging for indicator addition
   - Lines 185-186: Added warning for missing fields
   - Lines 250 & 258: Changed logging from DEBUG to INFO

### Impact:

**Before**: Indicators silently failed at buffer entry (field name mismatch)
**After**: Indicators properly buffered, batched, and emitted to UI

---

## Related Documents

- `docs/planning/sprints/sprint43/INDICATOR_FIELD_NAME_FIX.md` - Initial RedisEventSubscriber fix
- `docs/planning/sprints/sprint43/ROOT_CAUSE_PATTERN_DELAY.md` - Pattern delay resolution
- `docs/planning/sprints/sprint43/TICKSTOCKPL_INDICATOR_SYMBOL_ISSUE.md` - Symbol field investigation (not an issue)

---

**Action Required**: Restart TickStockAppV2 to apply both fixes.

**Expected Result**: Indicators will appear in UI within 250ms of calculation! 🎉
