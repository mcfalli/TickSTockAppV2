# TickStockPL Follow-Up Issue: Pattern/Indicator Job Triggering

**Status**: 🔴 Not Working
**Priority**: Medium
**Sprint**: Post-Sprint 42
**Component**: TickStockPL Streaming Service
**Related**: Sprint 42 Phase 3 Validation

---

## 🎯 Issue Summary

During Sprint 42 Phase 3 validation, we confirmed that **TickStockPL TickAggregator is successfully creating OHLCV bars** in the database. However, **pattern detection and indicator calculation jobs are not being triggered** when bars complete.

---

## ✅ What's Working

1. **TickAggregator**: Creating minute bars from Redis ticks
   - Evidence: 220 bars created in 3 minutes
   - Rate: 70 bars/minute (perfect distribution)
   - Database: `ohlcv_1min` table populated correctly

2. **Pattern/Indicator Jobs**: Properly initialized
   - StreamingPatternJob: Loaded 3 patterns (Doji, Hammer, HeadShoulders)
   - StreamingIndicatorJob: Loaded 2 indicators (RSI, SMA)
   - Jobs registered with StreamingPersistenceManager

3. **Redis Integration**: Tick consumption working
   - 300+ ticks processed from `tickstock:market:ticks` channel
   - TickAggregator callback registered and receiving ticks

---

## ❌ What's NOT Working

### Pattern Detection (Test 4)
```sql
SELECT pattern_type, COUNT(*) as count
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY pattern_type;
```
**Result**: 0 rows (no patterns detected)

### Indicator Calculation (Test 5)
```sql
SELECT indicator_type, COUNT(*) as count
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY indicator_type;
```
**Result**: 0 rows (no indicators calculated)

---

## 🔍 Root Cause Analysis

### Expected Behavior:
```
TickAggregator processes ticks
    ↓
Minute boundary reached
    ↓
TickAggregator completes bar
    ↓
StreamingPersistenceManager.add_minute_bar() called
    ↓
Persistence manager calls subscribers:
    - process_minute_bar_sequentially()
    ↓
StreamingIndicatorJob.process_bar() triggered
    ↓
StreamingPatternJob.process_bar() triggered
    ↓
Results written to intraday_patterns/intraday_indicators tables
```

### Actual Behavior:
```
TickAggregator processes ticks ✅
    ↓
Minute boundary reached ✅
    ↓
TickAggregator completes bar (assumed) ⚠️
    ↓
StreamingPersistenceManager.add_minute_bar() NOT called? ❌
    OR
Bar completion callback chain broken? ❌
    ↓
Subscribers never invoked ❌
    ↓
No patterns/indicators calculated ❌
```

### Evidence from Logs:
```
✅ Present: "TICK-AGGREGATOR: Initialized"
✅ Present: "StreamingIndicatorJob initialized with 1 indicators"
✅ Present: "StreamingPatternJob initialized with 1 patterns"
✅ Present: "Added minute bar subscriber: process_minute_bar_sequentially"
✅ Present: "STREAMING: Processed 300 ticks from Redis"
❌ MISSING: "Completed bar for AAPL at 15:37:00"
❌ MISSING: "Processing bar for indicator calculation"
❌ MISSING: "Detected pattern: Doji for NVDA"
```

---

## 🐛 Potential Issues to Investigate

### 1. **TickAggregator Not Calling Persistence Manager**
**File**: `TickStockPL/src/streaming/tick_aggregator.py`

**Check**:
- Does `TickAggregator.on_tick()` detect minute boundaries correctly?
- Does it call `self.persistence_manager.add_minute_bar()` on completion?
- Are there any exceptions preventing the call?

**Expected Code Pattern**:
```python
class TickAggregator:
    async def on_tick(self, tick_data: Dict[str, Any]) -> None:
        symbol = tick_data['symbol']

        # Detect minute boundary
        if self._is_new_minute(tick_data['timestamp'], symbol):
            # Complete previous bar
            if symbol in self._current_bars:
                completed_bar = self._current_bars[symbol]

                # THIS CALL MIGHT BE MISSING OR FAILING:
                await self.persistence_manager.add_minute_bar(
                    symbol=symbol,
                    timestamp=completed_bar.timestamp,
                    open=completed_bar.open,
                    high=completed_bar.high,
                    low=completed_bar.low,
                    close=completed_bar.close,
                    volume=completed_bar.volume
                )
```

### 2. **StreamingPersistenceManager Not Notifying Subscribers**
**File**: `TickStockPL/src/streaming/persistence_manager.py`

**Check**:
- Does `add_minute_bar()` write to database AND call subscribers?
- Are subscribers being called asynchronously?
- Are there any errors in the subscriber notification loop?

**Expected Code Pattern**:
```python
class StreamingPersistenceManager:
    async def add_minute_bar(self, symbol: str, timestamp: datetime,
                            open: float, high: float, low: float,
                            close: float, volume: int) -> bool:
        # Write to database
        success = await self._write_bar_to_db(...)

        if success:
            # THIS CALL MIGHT BE MISSING OR FAILING:
            await self._notify_subscribers({
                'symbol': symbol,
                'timestamp': timestamp,
                'open': open,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

        return success
```

### 3. **Minute Boundary Detection Failing**
**Issue**: TickAggregator might not be detecting minute rollovers correctly

**Check**:
- Is timestamp parsing correct (timezone handling)?
- Is the "current minute" tracking logic working?
- Are bars timing out without completion?

### 4. **Database Write Succeeding but Callbacks Failing**
**Issue**: Bars written to DB but subscribers not notified

**Check**:
- Is there a try/catch swallowing callback errors?
- Are callbacks executed in a separate thread/async context that's failing silently?

---

## 🧪 Debugging Steps

### Step 1: Add Debug Logging to TickAggregator
```python
# In TickAggregator.on_tick()
logger.info(f"TICK-AGGREGATOR: Processing tick for {symbol} at {timestamp}")

if self._is_new_minute(timestamp, symbol):
    logger.info(f"TICK-AGGREGATOR: Minute boundary detected for {symbol}")

    if symbol in self._current_bars:
        completed_bar = self._current_bars[symbol]
        logger.info(f"TICK-AGGREGATOR: Completing bar for {symbol} at {completed_bar.timestamp}")

        # Add try/catch to identify failures
        try:
            await self.persistence_manager.add_minute_bar(...)
            logger.info(f"TICK-AGGREGATOR: Bar persisted successfully for {symbol}")
        except Exception as e:
            logger.error(f"TICK-AGGREGATOR: Failed to persist bar: {e}")
```

### Step 2: Verify Subscriber Registration
```python
# In StreamingPersistenceManager
logger.info(f"PERSISTENCE-MANAGER: Registered subscribers: {len(self._bar_subscribers)}")
logger.info(f"PERSISTENCE-MANAGER: Subscriber names: {[s.__name__ for s in self._bar_subscribers]}")
```

### Step 3: Add Subscriber Notification Logging
```python
# In StreamingPersistenceManager._notify_subscribers()
async def _notify_subscribers(self, bar_data: Dict[str, Any]) -> None:
    logger.info(f"PERSISTENCE-MANAGER: Notifying {len(self._bar_subscribers)} subscribers")

    for subscriber in self._bar_subscribers:
        try:
            logger.info(f"PERSISTENCE-MANAGER: Calling subscriber {subscriber.__name__}")
            await subscriber(bar_data)
            logger.info(f"PERSISTENCE-MANAGER: Subscriber {subscriber.__name__} completed")
        except Exception as e:
            logger.error(f"PERSISTENCE-MANAGER: Subscriber {subscriber.__name__} failed: {e}")
```

### Step 4: Manual Query to Check Bar Timing
```sql
-- Check if bars are being created at expected times
SELECT
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(*) as bars,
    MAX(timestamp) - MIN(timestamp) as time_span
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY minute
ORDER BY minute DESC;
```

### Step 5: Check Pattern/Indicator Job Logs
```bash
# In TickStockPL logs, search for:
grep -E "(process_minute_bar_sequentially|process_bar|Calculating indicator|Detecting pattern)" streaming.log
```

---

## 📋 Reproduction Steps

1. Start TickStockAppV2 with synthetic data:
   ```bash
   cd C:\Users\McDude\TickStockAppV2
   python app.py
   ```

2. Start TickStockPL streaming service:
   ```bash
   cd C:\Users\McDude\TickStockPL
   python -m src.services.streaming_scheduler
   ```

3. Wait 5 minutes for multiple bar completions

4. Run validation queries:
   ```bash
   psql -h localhost -U app_readwrite -d tickstock -f quick_phase3_check.sql
   ```

5. Observe:
   - ✅ Test 1: OHLCV bars present (220+ bars)
   - ✅ Test 3: No duplicates (0 rows)
   - ❌ Test 4: No patterns detected (0 rows)
   - ❌ Test 5: No indicators calculated (0 rows)

---

## 🎯 Expected Resolution

### Success Criteria:
1. ✅ Bars continue to be created (already working)
2. ✅ "Completed bar" log messages appear every minute
3. ✅ Pattern detection queries return results (Test 4)
4. ✅ Indicator calculation queries return results (Test 5)
5. ✅ Logs show subscriber callbacks being invoked

### Validation Query After Fix:
```sql
-- Should return results after fix
SELECT
    'Bars Created' as metric,
    COUNT(*) as count
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes'
UNION ALL
SELECT
    'Patterns Detected' as metric,
    COUNT(*) as count
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
UNION ALL
SELECT
    'Indicators Calculated' as metric,
    COUNT(*) as count
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '5 minutes';
```

**Expected Result After Fix**:
```
metric                  | count
-----------------------|-------
Bars Created           | 220+
Patterns Detected      | 5+    (previously 0)
Indicators Calculated  | 140+  (previously 0)
```

---

## 🔗 Related Files

**TickStockPL Files to Review:**
- `src/streaming/tick_aggregator.py` - Bar aggregation logic
- `src/streaming/persistence_manager.py` - Subscriber notification
- `src/streaming/redis_tick_subscriber.py` - Tick consumption
- `src/jobs/streaming_indicator_job.py` - Indicator calculation
- `src/jobs/streaming_pattern_job.py` - Pattern detection

**TickStockAppV2 Validation Files:**
- `docs/planning/sprints/sprint42/quick_phase3_check.sql` - Quick validation
- `docs/planning/sprints/sprint42/test5_fixed.sql` - Indicator query
- `docs/planning/sprints/sprint42/check_streaming_pipeline.sql` - Full pipeline check

---

## 💡 Recommendation

**Priority**: Medium (not critical - bars are being created)

**Action Items**:
1. Add debug logging to TickAggregator and StreamingPersistenceManager
2. Run streaming service with verbose logging
3. Monitor for "Completed bar" messages
4. Verify subscriber callback chain is executing
5. Fix the callback/notification mechanism
6. Re-run Phase 3 validation queries to confirm fix

**Timeline**:
- Investigation: 1-2 hours
- Fix: 1-2 hours
- Testing: 30 minutes
- **Total**: 3-4 hours

---

## 📊 Impact Assessment

**Current State**:
- ✅ Sprint 42 goal achieved (architectural realignment complete)
- ✅ OHLCV bars being created by TickStockPL (220 bars in 3 min)
- ✅ Single source of truth established (0 duplicates)
- ⚠️ Real-time pattern detection not working
- ⚠️ Real-time indicator calculation not working

**User Impact**:
- Historical pattern/indicator analysis: ✅ Working (daily batch processing)
- Real-time streaming alerts: ⚠️ Not working
- Dashboard data: ⚠️ Missing real-time patterns/indicators

**Workaround**:
- Daily batch processing still works for pattern/indicator calculation
- Real-time streaming features degraded until fix implemented

---

## 📝 Next Steps

1. Create TickStockPL ticket: "StreamingPersistenceManager bar completion callbacks not triggering pattern/indicator jobs"
2. Assign to TickStockPL team for investigation
3. Reference this document for reproduction steps and debugging guidance
4. Test fix by running `quick_phase3_check.sql` after implementation
5. Validate all 5 tests pass (including Test 4 & 5)

---

**Created**: October 12, 2025
**Sprint**: Post-Sprint 42
**Severity**: Medium
**Component**: TickStockPL Streaming Pipeline
**Related Sprint**: Sprint 42 - Architectural Realignment

---

*This issue was identified during Sprint 42 Phase 3 validation. While Sprint 42's goal (move OHLCV aggregation to TickStockPL) was successfully achieved, this separate operational issue with pattern/indicator job triggering needs to be addressed to restore full real-time streaming functionality.*
