# TickStockPL Indicator Symbol Field Issue

**Date**: 2025-10-15
**Issue**: Indicator events arriving on Redis WITHOUT symbol field
**Reporter**: TickStockAppV2 Redis Integration Specialist

---

## Problem Statement

TickStockPL is publishing indicator events to `tickstock:indicators:streaming` but the `symbol` field is **NOT present** in the events arriving on the Redis channel.

### Evidence from TickStockAppV2

**Redis Monitoring Results** (`check_redis_pattern_events.py`):
- Monitored: `tickstock:indicators:streaming` channel
- Duration: 15 seconds
- Events captured: 84+ indicator events
- **Result**: 100% of events show "Symbol: N/A"

**Sample Output**:
```
Time         | Channel                             | Event Type           | Symbol     | Details
------------------------------------------------------------------------------------------------------------------------
20:39:28.236 | tickstock:indicators:streaming      | streaming_indicator  | N/A        | Indicator: N/A
20:39:28.269 | tickstock:indicators:streaming      | streaming_indicator  | N/A        | Indicator: N/A
20:39:28.301 | tickstock:indicators:streaming      | streaming_indicator  | N/A        | Indicator: N/A
... (84+ more events, ALL with Symbol: N/A)
```

**Pattern Events Work Correctly** (for comparison):
```
20:39:28.339 | tickstock:patterns:streaming        | streaming_pattern    | NVDA       | Pattern: PriceChange, Conf: 0.95
20:39:28.372 | tickstock:patterns:streaming        | streaming_pattern    | NVDA       | Pattern: AlwaysDetected, Conf: 0.85
20:39:28.504 | tickstock:patterns:streaming        | streaming_pattern    | MSFT       | Pattern: PriceChange, Conf: 0.95
```

Pattern events **DO include symbols** correctly (NVDA, MSFT, AAPL, etc.)

---

## TickStockPL Feedback

TickStockPL team states the code **should** include the symbol:

```python
# Line 217: "symbol": symbol in the calculation dict
# Line 511: "symbol": calculation["symbol"] in the Redis event
```

**Expected Redis event structure**:
```json
{
  "type": "streaming_indicator",
  "calculation": {
    "symbol": "VGT",       // <-- SHOULD BE HERE
    "indicator": "AlwaysTrue",
    "value": 1.0,
    "timestamp": "2025-10-15T20:39:28.236Z"
  }
}
```

---

## Actual vs Expected

### What's Expected (According to TickStockPL)
```json
{
  "type": "streaming_indicator",
  "calculation": {
    "symbol": "VGT",               // ✅ SHOULD BE PRESENT
    "indicator": "AlwaysTrue",
    "value": 1.0
  }
}
```

### What's Actually Arriving on Redis
```json
{
  "type": "streaming_indicator",
  "calculation": {
    // ❌ NO SYMBOL FIELD
    "indicator": "???",            // Unknown (parsed as N/A)
    "value": "???"
  }
}
```

---

## Diagnostic Code Used (TickStockAppV2 Side)

### Redis Event Parsing Logic

**File**: `scripts/diagnostics/check_redis_pattern_events.py`

**Indicator Event Extraction**:
```python
# Line 67-71: How we extract indicator details
calculation = data.get('calculation', {})
symbol = calculation.get('symbol', 'N/A')        # Returns N/A for ALL events
indicator_type = calculation.get('indicator_type',
                calculation.get('indicator', 'N/A'))
```

**Pattern Event Extraction** (works correctly):
```python
# Line 60-64: Pattern symbol extraction (WORKS)
detection = data.get('detection', {})
symbol = detection.get('symbol', 'N/A')          # Returns correct symbols
pattern_type = detection.get('pattern_type', 'N/A')
confidence = detection.get('confidence', 0)
```

---

## Requests for TickStockPL Team

### 1. Verify Symbol Variable at Line 217

**Question**: What is the value of the `symbol` variable at line 217?

```python
# Line 217 (TickStockPL code)
calculation = {
    "symbol": symbol,    # <-- What is `symbol` here? Is it None? Empty string?
    "indicator": "...",
    "value": ...
}
```

**Debugging Request**:
```python
# Add logging before line 217
logger.info(f"DEBUG: symbol variable = '{symbol}' (type: {type(symbol)})")

calculation = {
    "symbol": symbol,
    ...
}

logger.info(f"DEBUG: calculation dict = {json.dumps(calculation, indent=2)}")
```

### 2. Verify Redis Publish at Line 511

**Question**: What does the event look like right before publishing to Redis?

```python
# Line 511 (TickStockPL code)
redis_event = {
    "type": "streaming_indicator",
    "calculation": {
        "symbol": calculation["symbol"],   # <-- What's in calculation["symbol"]?
        ...
    }
}

# Add logging
logger.info(f"DEBUG: Publishing to Redis - {json.dumps(redis_event, indent=2)}")

redis_client.publish('tickstock:indicators:streaming', json.dumps(redis_event))
```

### 3. Test with AlwaysTrue Indicator on Known Symbol

**Request**: Manually trigger AlwaysTrue indicator for a specific symbol (e.g., NVDA) and:

1. Log the `symbol` variable before creating the calculation dict
2. Log the `calculation` dict after creation
3. Log the complete `redis_event` before publishing
4. Publish to Redis
5. Verify on TickStockAppV2 side that symbol arrives correctly

---

## Next Steps

### For TickStockPL:
1. ✅ Add debug logging at lines 217 and 511
2. ✅ Verify symbol variable is not None/empty
3. ✅ Manually test with AlwaysTrue on NVDA
4. ✅ Confirm Redis event structure before publishing

### For TickStockAppV2:
1. ✅ Continue monitoring Redis with `check_redis_pattern_events.py`
2. ✅ Wait for TickStockPL fixes
3. ⏳ Verify indicators start showing symbols correctly
4. ⏳ Verify indicators appear in UI once symbols are present

---

## Database Evidence

Indicators **ARE being written to database** correctly with symbols:

```sql
SELECT symbol, indicator_type, COUNT(*)
FROM intraday_indicators
WHERE detected_at >= CURRENT_DATE
GROUP BY symbol, indicator_type
ORDER BY symbol, indicator_type;
```

**Result**: 690 indicators written with proper symbols (NVDA, MSFT, AAPL, etc.)

This proves:
- ✅ TickStockPL IS calculating indicators correctly
- ✅ TickStockPL IS writing to database with symbols
- ❌ TickStockPL is NOT publishing to Redis with symbols

**Hypothesis**: There may be a separate code path for:
- Database writes (includes symbols) ✅
- Redis publish (missing symbols) ❌

---

## Impact

### Current State:
- ❌ Indicators NOT showing in UI (StreamingBuffer cannot buffer without symbols)
- ❌ Real-time indicator alerts NOT working
- ✅ Database writes working correctly
- ✅ Pattern streaming working correctly

### When Fixed:
- ✅ Indicators will show in UI in real-time
- ✅ StreamingBuffer will batch and emit indicator events
- ✅ Users will see indicator alerts within 250ms
- ✅ Full streaming functionality operational

---

## Related Documents

- `docs/planning/sprints/sprint43/PATTERN_INDICATOR_UI_ISSUE_2025-10-15.md` - Original issue report
- `docs/planning/sprints/sprint43/STREAMING_BUFFER_ANALYSIS.md` - Pattern delay analysis
- `scripts/diagnostics/check_redis_pattern_events.py` - Redis monitoring script
- `src/core/services/redis_event_subscriber.py` - Event consumption logic

---

**Summary**: TickStockPL code claims to include `symbol` field in indicator events, but Redis monitoring confirms 100% of indicator events arrive WITHOUT symbols. Need TickStockPL to add debug logging and verify the symbol variable is populated correctly at lines 217 and 511.
