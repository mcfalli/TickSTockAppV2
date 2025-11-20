# Health Check Diagnostic - APScheduler Not Firing

**Date**: October 7, 2025, 2:18 PM ET
**Sprint**: Sprint 40 - Live Streaming Integration
**Issue**: APScheduler "Streaming Health Check" job scheduled but not executing

---

## Diagnostic Results

### ✅ What's Working

1. **StreamingHealthMonitor Initialized**:
   ```
   [TickStockPL Streaming] 2025-10-07 14:15:24,194 - StreamingHealthMonitor initialized for session 5e100de4
   ```

2. **Health Check Job Scheduled**:
   ```
   [TickStockPL Streaming] 2025-10-07 14:15:24,091 - Added job "Streaming Health Check" to job store "default"
   [TickStockPL Streaming] 2025-10-07 14:15:24,091 - Scheduler started
   ```

3. **Streaming Session Started**:
   ```
   [TickStockPL Streaming] 2025-10-07 14:15:24,317 - STREAMING: Starting Redis tick listener loop
   ```

### ❌ **Issue Identified: SCENARIO A - APScheduler Job Not Firing**

**Evidence**:
```bash
grep "HEALTH-CHECK" temp_log.log
# Result: NO MATCHES
```

**Expected Logs** (from debug logging added by TickStockPL developer):
```
[TickStockPL Streaming] HEALTH-CHECK: Called (is_streaming=True)
[TickStockPL Streaming] HEALTH-CHECK: Calling health_monitor.check_health()
[TickStockPL Streaming] STREAMING-HEALTH: Published health update - Status: healthy
```

**Actual**: Zero "HEALTH-CHECK" logs - the `health_check()` method **never called**

---

## Root Cause Analysis

### APScheduler Job Not Executing

**Possible Causes**:

1. **Job Interval Not Configured**
   - Job added to scheduler but no interval specified
   - Missing `interval`, `seconds=5` in job configuration

2. **Job Trigger Not Set**
   - Job scheduled but trigger condition never met
   - Missing `trigger='interval'` parameter

3. **Scheduler Event Loop Not Running**
   - Scheduler started but background thread/task not processing jobs
   - Event loop blocked or not started

4. **Job Configuration Error**
   - Job name mismatch between scheduled job and callable function
   - Function reference incorrect or not callable

---

## Expected vs Actual APScheduler Configuration

### Expected Configuration (Working Example)

```python
# Option 1: Using interval trigger
scheduler.add_job(
    func=self.health_check,
    trigger='interval',
    seconds=5,  # CRITICAL: Run every 5 seconds
    id='streaming_health_check',
    name='Streaming Health Check',
    replace_existing=True
)
```

**OR**

```python
# Option 2: Using decorator
@scheduler.scheduled_job('interval', seconds=5, id='streaming_health_check')
def health_check(self):
    logger.info(f"HEALTH-CHECK: Called (is_streaming={self.is_streaming})")
    # ... rest of health check logic
```

### Current Configuration (Inferred from Logs)

```python
# What we can see from logs:
scheduler.add_job(
    # ... some parameters ...
    name='Streaming Health Check'
)
# Added to job store: "default"
# Scheduler started: True
# Trigger interval: UNKNOWN - not logged
```

**Missing from logs**:
- ❌ No "Added job with trigger 'interval'" log
- ❌ No "Next run time" log for health check job
- ❌ No execution logs showing job running

---

## Verification Steps

### Step 1: Check APScheduler Job Configuration

**Location**: `src/services/streaming_scheduler.py` (or wherever health check job is scheduled)

**Look for this code**:
```python
# Search for: scheduler.add_job.*health
# Should have: trigger='interval', seconds=5
```

**Expected Pattern**:
```python
self.scheduler.add_job(
    func=self.health_check,
    trigger='interval',      # ← MUST BE PRESENT
    seconds=5,               # ← MUST BE PRESENT
    id='streaming_health_check',
    name='Streaming Health Check'
)
```

### Step 2: Verify Job is in Scheduler

**Add debug logging right after job scheduled**:
```python
self.scheduler.add_job(...)

# Add this immediately after:
jobs = self.scheduler.get_jobs()
for job in jobs:
    logger.info(f"SCHEDULER-DEBUG: Job '{job.name}' - Next run: {job.next_run_time}, Trigger: {job.trigger}")
```

**Expected Output**:
```
SCHEDULER-DEBUG: Job 'Streaming Health Check' - Next run: 2025-10-07 14:15:29, Trigger: interval[0:00:05]
```

**If Missing**: Job not properly configured with trigger

### Step 3: Test Manual Health Check Call

**Add manual call immediately after scheduler starts**:
```python
self.scheduler.start()
logger.info("Streaming scheduler started")

# Add this for testing:
logger.info("SCHEDULER-TEST: Calling health_check() manually for testing")
self.health_check()
logger.info("SCHEDULER-TEST: Manual health_check() completed")
```

**Expected Output**:
```
SCHEDULER-TEST: Calling health_check() manually for testing
HEALTH-CHECK: Called (is_streaming=True)
HEALTH-CHECK: Calling health_monitor.check_health()
STREAMING-HEALTH: Published health update - Status: starting, Active Symbols: 0, TPS: 0.0
SCHEDULER-TEST: Manual health_check() completed
```

**If Works**: Scheduler trigger configuration is the issue
**If Fails**: Problem with health_check() method itself

---

## Quick Fix Options

### Option 1: Fix APScheduler Trigger (Most Likely)

**File**: `src/services/streaming_scheduler.py`

**Find**:
```python
self.scheduler.add_job(
    # ... existing code ...
    name='Streaming Health Check'
)
```

**Change to**:
```python
self.scheduler.add_job(
    func=self.health_check,           # Method to call
    trigger='interval',               # ← ADD THIS
    seconds=5,                        # ← ADD THIS (5 second interval)
    id='streaming_health_check',
    name='Streaming Health Check',
    replace_existing=True
)
logger.info("SCHEDULER: Health check job scheduled to run every 5 seconds")
```

### Option 2: Alternative - Use Background Loop Instead

**If APScheduler causing issues, switch to async loop**:

```python
async def _health_publishing_loop(self):
    """Background loop to publish health every 5 seconds."""
    while self.is_streaming:
        try:
            self.health_check()
            await asyncio.sleep(5.0)
        except Exception as e:
            logger.error(f"HEALTH-PUBLISHING-LOOP: Error: {e}")
            await asyncio.sleep(5.0)  # Continue despite errors

# Start loop when streaming starts:
def _start_streaming(self, session_id):
    # ... existing initialization ...

    # Start health publishing loop
    asyncio.create_task(self._health_publishing_loop())
    logger.info("STREAMING: Health publishing background loop started")
```

### Option 3: Use Threading Instead

**If not using asyncio**:

```python
import threading
import time

def _health_publishing_thread(self):
    """Background thread to publish health every 5 seconds."""
    while self.is_streaming:
        try:
            self.health_check()
            time.sleep(5.0)
        except Exception as e:
            logger.error(f"HEALTH-PUBLISHING-THREAD: Error: {e}")
            time.sleep(5.0)

# Start thread when streaming starts:
def _start_streaming(self, session_id):
    # ... existing initialization ...

    # Start health publishing thread
    health_thread = threading.Thread(target=self._health_publishing_thread, daemon=True)
    health_thread.start()
    logger.info("STREAMING: Health publishing background thread started")
```

---

## APScheduler Common Issues

### Issue 1: Job Added But No Trigger
**Symptom**: Job in job store but never executes
**Cause**: Missing `trigger='interval'` parameter
**Fix**: Add trigger configuration

### Issue 2: Job Scheduled Before Scheduler Starts
**Symptom**: Job added but scheduler not running
**Cause**: `scheduler.start()` called before `add_job()`
**Fix**: Ensure `add_job()` called BEFORE `scheduler.start()`

### Issue 3: Event Loop Not Running
**Symptom**: Scheduler started but jobs don't fire
**Cause**: Main thread exits or event loop blocked
**Fix**: Ensure main thread stays alive or use `scheduler.start(paused=False)`

### Issue 4: Job Function Not Callable
**Symptom**: Job added but errors when trying to execute
**Cause**: `func` parameter references non-callable or incorrect method
**Fix**: Verify `func=self.health_check` points to valid method

---

## Timeline Analysis

**14:15:24.091** - Health Check job added to scheduler ✅
**14:15:24.091** - Scheduler started ✅
**14:15:24.194** - StreamingHealthMonitor initialized ✅
**14:15:24.317** - Streaming session started ✅
**14:15:29** - **Expected first health check** ❌ (never fired)
**14:15:34** - **Expected second health check** ❌ (never fired)
**14:15:39** - **Expected third health check** ❌ (never fired)

**Current Time**: ~14:18 (3+ minutes elapsed)
**Expected Health Events**: ~36 (every 5 seconds for 3 minutes)
**Actual Health Events**: 0

---

## Recommended Next Steps

1. **Check APScheduler Configuration**
   - Verify `trigger='interval', seconds=5` parameters present
   - Add debug logging to show job trigger details

2. **Test Manual Health Check**
   - Call `health_check()` manually to verify method works
   - Confirms issue is scheduler configuration, not health check logic

3. **Add Scheduler Debugging**
   - Log all scheduled jobs with their next run times
   - Verify health check job has proper trigger interval

4. **Consider Alternative Implementation**
   - If APScheduler issues persist, switch to background thread/loop
   - Simpler and more direct control over execution timing

---

## Success Criteria

Once fixed, you should see:

**Immediate (on service start)**:
```
[TickStockPL Streaming] SCHEDULER: Health check job scheduled to run every 5 seconds
[TickStockPL Streaming] SCHEDULER-DEBUG: Job 'Streaming Health Check' - Next run: 2025-10-07 14:XX:XX
```

**Every 5 Seconds**:
```
[TickStockPL Streaming] HEALTH-CHECK: Called (is_streaming=True)
[TickStockPL Streaming] HEALTH-CHECK: Calling health_monitor.check_health()
[TickStockPL Streaming] STREAMING-HEALTH: Published health update - Status: healthy, Active Symbols: 60, TPS: 15.2
[TickStockPL Streaming] HEALTH-CHECK: check_health() returned status='healthy'
```

**TickStockAppV2**:
```
[TickStockAppV2] REDIS-SUBSCRIBER: Streaming health update received - Status: healthy
```

**Dashboard**:
```
Status: HEALTHY ✅
Active Symbols: 60
Data Flow: 15.2 ticks/sec
```

---

**Status**: ⏳ **APScheduler Configuration Issue**
**Blocker**: Health check job scheduled but trigger interval missing/incorrect
**Impact**: Dashboard showing "UNKNOWN" - no health events published

**Estimated Fix Time**: 5-15 minutes (add trigger configuration)

---

**Generated**: October 7, 2025, 2:18 PM ET
**Sprint 40 Phase**: APScheduler Job Configuration Debugging
