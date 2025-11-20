# TickStockPL Health Metrics Calculation Issue

**Date**: October 7, 2025, 2:45 PM ET
**Sprint**: Sprint 40 - Live Streaming Integration
**Issue**: Health events publishing with incorrect metrics (zeros)
**Priority**: MEDIUM - Causes dashboard values to flash between 0 and real values

---

## Issue Description

TickStockPL's `StreamingHealthMonitor` is publishing health events with **Active Symbols: 0** and **TPS: 0.0** even when ticks are actively being processed.

### Observable Behavior

**Dashboard Display**:
- Shows zeros for 3-4 seconds
- Shows real values (60 symbols, 15-20 TPS) for 5-6 seconds
- Cycle repeats continuously

**User Impact**: Confusing, appears broken, values flash and change unexpectedly

---

## Log Evidence

### TickStockPL Publishing (WRONG - Zeros)
```
[TickStockPL Streaming] 2025-10-07 14:22:02,147 - STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 0, TPS: 0.0
```

### TickStockAppV2 Receiving (Multiple Events)
```
14:21:53 - REDIS-SUBSCRIBER: Streaming health update received - Status: healthy, Active Symbols: 60, TPS: 15.2
14:22:02 - REDIS-SUBSCRIBER: Streaming health update received - Status: healthy, Active Symbols: 0, TPS: 0.0   ❌ ZEROS
14:22:03 - REDIS-SUBSCRIBER: Streaming health update received - Status: healthy, Active Symbols: 60, TPS: 16.2
```

**Pattern**: Alternating between zeros and real values

---

## Root Cause Analysis

### Expected Behavior

**TickStockPL StreamingHealthMonitor** should:
1. Track symbols actively being processed
2. Calculate ticks per second from actual tick flow
3. Publish these metrics in health events

### Actual Behavior

**Health monitor is publishing hardcoded or uninitialized values**:
- `active_symbols`: 0 (should be 60 from universe)
- `ticks_per_second`: 0.0 (should be calculated from tick flow)

### Possible Causes

**Cause 1 - Metrics Not Being Updated**:
```python
class StreamingHealthMonitor:
    def __init__(self, redis_client, session_id):
        self.active_symbols = 0  # ← Never updated!
        self.ticks_per_second = 0.0  # ← Never updated!
```

**Cause 2 - Missing Tick Counter Integration**:
```python
# Health monitor not receiving tick flow updates
def check_health(self):
    # Publishes without recalculating metrics
    health_event = {
        'active_symbols': self.active_symbols,  # Still 0
        'ticks_per_second': self.ticks_per_second  # Still 0.0
    }
```

**Cause 3 - Wrong Data Source**:
```python
# Health monitor using wrong source for metrics
# Should use: RedisTickSubscriber tick counter
# Actually using: Local uninitialized variables
```

---

## Required Fix (TickStockPL)

### Step 1: Connect Health Monitor to Tick Subscriber

**Location**: `src/streaming/health_monitor.py` or `src/services/streaming_scheduler.py`

**Current (WRONG)**:
```python
class StreamingHealthMonitor:
    def __init__(self, redis_client, session_id):
        self.active_symbols = 0  # ← Hardcoded
        self.ticks_per_second = 0.0  # ← Hardcoded
```

**Fixed (CORRECT)**:
```python
class StreamingHealthMonitor:
    def __init__(self, redis_client, session_id, tick_subscriber, symbol_universe):
        self.redis_client = redis_client
        self.session_id = session_id
        self.tick_subscriber = tick_subscriber  # ✅ Reference to tick counter
        self.symbol_universe = symbol_universe  # ✅ Reference to symbol list
        self.last_tick_count = 0
        self.last_check_time = time.time()
```

### Step 2: Calculate Metrics from Actual Data

**Add method to calculate TPS**:
```python
def _calculate_ticks_per_second(self):
    """Calculate TPS from tick subscriber."""
    current_tick_count = self.tick_subscriber.get_total_ticks()  # Get from RedisTickSubscriber
    current_time = time.time()

    elapsed_time = current_time - self.last_check_time
    tick_delta = current_tick_count - self.last_tick_count

    if elapsed_time > 0:
        tps = tick_delta / elapsed_time
    else:
        tps = 0.0

    # Update for next calculation
    self.last_tick_count = current_tick_count
    self.last_check_time = current_time

    return round(tps, 1)

def _get_active_symbols(self):
    """Get active symbol count from universe."""
    if hasattr(self.symbol_universe, '__len__'):
        return len(self.symbol_universe)
    return 0
```

### Step 3: Use Calculated Metrics in Health Events

**Current (WRONG)**:
```python
def check_health(self):
    health_event = {
        'type': 'streaming_health',
        'health': {
            'active_symbols': self.active_symbols,  # ← 0
            'ticks_per_second': self.ticks_per_second,  # ← 0.0
            ...
        }
    }
```

**Fixed (CORRECT)**:
```python
def check_health(self):
    # Calculate metrics from actual data
    tps = self._calculate_ticks_per_second()  # ✅ Real calculation
    active_symbols = self._get_active_symbols()  # ✅ From universe

    health_event = {
        'type': 'streaming_health',
        'health': {
            'session_id': self.session_id,
            'status': self._get_status(tps, active_symbols),
            'active_symbols': active_symbols,  # ✅ Real count
            'ticks_per_second': tps,  # ✅ Real TPS
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    self.redis_client.publish('tickstock:streaming:health', json.dumps(health_event))
    logger.info(f"STREAMING-HEALTH: Published health update - Status: {health_event['health']['status']}, Active Symbols: {active_symbols}, TPS: {tps}")
```

---

## Integration Example

### In streaming_scheduler.py

**When initializing health monitor**:
```python
def _start_streaming(self, session_id):
    # ... existing initialization ...

    # Load symbol universe
    self.symbol_universe = self._load_symbol_universe('market_leaders:top_500')
    logger.info(f"Loaded {len(self.symbol_universe)} symbols from universe")

    # Initialize tick subscriber
    self.tick_subscriber = RedisTickSubscriber(
        redis_client=self.redis_client,
        channel='tickstock:market:ticks'
    )

    # Initialize health monitor WITH references to data sources
    self.health_monitor = StreamingHealthMonitor(
        redis_client=self.redis_client,
        session_id=session_id,
        tick_subscriber=self.tick_subscriber,  # ✅ Pass tick counter
        symbol_universe=self.symbol_universe   # ✅ Pass symbol list
    )
    logger.info(f"StreamingHealthMonitor initialized with {len(self.symbol_universe)} symbols")

    # Start health monitoring
    # (APScheduler job already configured to call health_monitor.check_health() every 10s)
```

---

## Alternative: If Tick Subscriber Already Tracks Metrics

If `RedisTickSubscriber` already calculates TPS internally:

```python
class StreamingHealthMonitor:
    def check_health(self):
        # Get metrics directly from tick subscriber
        metrics = self.tick_subscriber.get_metrics()

        health_event = {
            'type': 'streaming_health',
            'health': {
                'session_id': self.session_id,
                'status': 'healthy',
                'active_symbols': len(self.symbol_universe),
                'ticks_per_second': metrics.get('tps', 0.0),  # From subscriber
                'total_ticks': metrics.get('total', 0),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        self.redis_client.publish('tickstock:streaming:health', json.dumps(health_event))
```

---

## Testing After Fix

### Step 1: Restart TickStockPL Streaming

**Expected logs**:
```
[TickStockPL Streaming] StreamingHealthMonitor initialized with 60 symbols
[TickStockPL Streaming] STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 60, TPS: 18.5
[TickStockPL Streaming] STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 60, TPS: 22.3
[TickStockPL Streaming] STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 60, TPS: 19.1
```

**No more zeros!**

### Step 2: Verify Dashboard

**Expected behavior**:
- Initial load: Shows last known values or defaults
- First health event: Updates to real values (60 symbols, 15-25 TPS)
- Subsequent events: Values update smoothly, **no flashing to zero**
- Page refresh: Retains last known values

**Success Criteria**:
```
Status: HEALTHY ✅
Active Symbols: 60  (stable, doesn't flash to 0)
Data Flow: 18-25 ticks/sec  (updates every 10s, doesn't flash to 0)
```

### Step 3: Monitor for 60 Seconds

**Watch logs for pattern**:
```bash
grep "STREAMING-HEALTH" logs/*.log | tail -10
```

**Should see consistent values**:
```
14:50:10 - STREAMING-HEALTH: ... Active Symbols: 60, TPS: 18.2
14:50:20 - STREAMING-HEALTH: ... Active Symbols: 60, TPS: 21.5
14:50:30 - STREAMING-HEALTH: ... Active Symbols: 60, TPS: 19.8
14:50:40 - STREAMING-HEALTH: ... Active Symbols: 60, TPS: 22.1
```

**NO zeros in the sequence** ✅

---

## Current Workaround (TickStockAppV2)

**Not recommended** - treating symptom, not root cause

We could filter out zero-value events in TickStockAppV2:
```python
def _handle_streaming_health(self, event: TickStockEvent):
    health_data = event.data.get('health', event.data)

    # WORKAROUND: Ignore events with zero TPS (likely invalid)
    if health_data.get('ticks_per_second', 0) == 0:
        logger.debug("REDIS-SUBSCRIBER: Ignoring health event with zero TPS")
        return  # Don't update display

    # ... rest of handler ...
```

**Why not recommended**: Hides the real issue, prevents seeing actual zero TPS if streaming genuinely stops

---

## Questions for TickStockPL Developer

1. **Where does health monitor get tick count?**
   - Does it have access to `RedisTickSubscriber`?
   - Is there a central tick counter it should reference?

2. **Where does health monitor get active symbols?**
   - Does it have access to the loaded symbol universe?
   - Should it count symbols from somewhere else?

3. **Why are there two different TPS values?**
   - 14:22:02 - TPS: 0.0 (from health monitor)
   - 14:22:03 - TPS: 16.2 (from another source?)
   - Are there multiple health event publishers?

4. **Is RedisTickSubscriber already calculating TPS?**
   - If yes, health monitor can just use that value
   - If no, health monitor needs to implement calculation

---

## Related Files (TickStockPL)

**Check these files**:
- `src/streaming/health_monitor.py` - Health monitor class
- `src/streaming/redis_tick_subscriber.py` - Tick counter/subscriber
- `src/services/streaming_scheduler.py` - Initialization and integration
- `src/data/symbol_cache_manager.py` - Symbol universe loading

**Look for**:
- How health monitor is initialized (what parameters passed?)
- Where tick count is tracked (RedisTickSubscriber? Elsewhere?)
- Where symbol count comes from (symbol_universe? cache?)

---

## Expected Timeline

**Estimated Fix Time**: 30-60 minutes

**Steps**:
1. Add tick_subscriber and symbol_universe parameters to StreamingHealthMonitor init (5 min)
2. Implement _calculate_ticks_per_second() method (15 min)
3. Implement _get_active_symbols() method (5 min)
4. Update check_health() to use calculated values (10 min)
5. Test and verify metrics are correct (15 min)

---

## Success Metrics

### Before Fix ❌
```
Dashboard displays:
  0 symbols → 60 symbols → 0 symbols → 60 symbols (flashing)
  0 TPS → 18 TPS → 0 TPS → 18 TPS (flashing)
```

### After Fix ✅
```
Dashboard displays:
  60 symbols (stable)
  18-25 TPS (updates smoothly every 10s, no zeros)
```

---

**Status**: ⏳ Awaiting TickStockPL Fix
**Priority**: MEDIUM - Functional but confusing UX
**Workaround**: None - should fix root cause in TickStockPL

---

**Generated**: October 7, 2025, 2:45 PM ET
**Sprint 40 Phase**: Integration Testing - Metrics Calculation Issue
