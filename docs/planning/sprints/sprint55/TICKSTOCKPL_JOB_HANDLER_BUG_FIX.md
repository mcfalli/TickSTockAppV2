# TickStockPL Job Handler Bug Fix - URGENT

**Date**: 2025-11-30
**Sprint**: 55
**Priority**: CRITICAL
**Component**: TickStockPL DataLoader Job Handler

---

## Executive Summary

**Problem**: TickStockPL DataLoader is ignoring the `symbols` array sent in Redis messages and instead defaulting to reading `sp_500.csv` (380 symbols) for ALL universe load jobs, regardless of what was actually requested.

**Impact**: Users cannot load cached universes (ETFs, custom lists) - all jobs incorrectly load S&P 500 data.

**Root Cause**: Job handler expects old message format with `csv_file` field, ignores new `symbols` array format.

---

## Evidence from Logs

### What AppV2 Sends (CORRECT):
```
[TickStockAppV2] 2025-11-30 06:24:36,709 - Publishing job universe_load_1764505476_6849: 3 symbols - ['SPY', 'QQQ', 'IWM']
```

**Redis Message Published:**
```json
{
  "job_id": "universe_load_1764505476_6849",
  "job_type": "csv_universe_load",
  "source": "etf_universe:etf_core",
  "symbols": ["SPY", "QQQ", "IWM"],
  "years": 0.005,
  "submitted_at": "2025-11-30T06:24:36.709000"
}
```

### What TickStockPL Does (WRONG):
```
[TickStockPL DataLoader] 2025-11-30 06:24:36,710 - Processing job universe_load_1764505476_6849: csv_universe_load
[TickStockPL DataLoader] 2025-11-30 06:24:36,713 - CSV Universe Load: sp_500.csv for 2 days (1.8 days) by admin
[TickStockPL DataLoader] 2025-11-30 06:24:36,714 - Read 380 symbols from C:\Users\McDude\TickStockAppV2\data\sp_500.csv
[TickStockPL DataLoader] 2025-11-30 06:24:36,714 - Loaded 380 symbols from sp_500.csv
```

**TickStockPL received the SAME job_id but:**
- ❌ Ignored `symbols: ["SPY", "QQQ", "IWM"]`
- ❌ Ignored `source: "etf_universe:etf_core"`
- ❌ Defaulted to reading `sp_500.csv`
- ❌ Loaded wrong 380 symbols

---

## Required Fix

### Location
**File**: `TickStockPL/src/data/loader.py` (or wherever the job handler for `csv_universe_load` is located)

### Current Behavior (BROKEN):
```python
def handle_csv_universe_load(job_data):
    """Current implementation - BROKEN"""
    job_id = job_data.get('job_id')

    # BUG: Tries to read from CSV file instead of using symbols array
    csv_file = job_data.get('csv_file', 'sp_500.csv')  # ← WRONG! Defaults to sp_500.csv
    file_path = os.path.join('data', csv_file)

    # Reads from file, ignoring the symbols array in the message
    symbols = read_csv_file(file_path)  # ← WRONG!

    # Process symbols...
```

### Expected Behavior (CORRECT):
```python
def handle_csv_universe_load(job_data):
    """Fixed implementation - Use symbols array from message"""
    job_id = job_data.get('job_id')
    years = job_data.get('years', 1)
    source = job_data.get('source', 'unknown')

    # FIX: Use symbols array directly from Redis message
    symbols = job_data.get('symbols')

    # Fallback to CSV file only if symbols array not provided (backward compatibility)
    if not symbols:
        csv_file = job_data.get('csv_file')
        if csv_file:
            file_path = os.path.join('data', csv_file)
            symbols = read_csv_file(file_path)
        else:
            logger.error(f"Job {job_id}: No symbols array or csv_file provided")
            return

    logger.info(f"Job {job_id}: Processing {len(symbols)} symbols from {source}")
    logger.info(f"Job {job_id}: Symbols: {symbols}")

    # Process symbols...
```

---

## Implementation Steps

### Step 1: Locate the Job Handler
Find where `csv_universe_load` job type is handled. Search for:
```bash
grep -r "csv_universe_load" TickStockPL/src/
grep -r "job_type.*csv" TickStockPL/src/
```

### Step 2: Update the Handler Function

**Current code pattern to find:**
```python
csv_file = job_data.get('csv_file')
# or
csv_file = message.get('csv_file')
# or similar file reading logic
```

**Replace with:**
```python
# Priority 1: Use symbols array from message (NEW FORMAT)
symbols = job_data.get('symbols')

# Priority 2: Fallback to CSV file if no symbols array (OLD FORMAT - backward compatibility)
if not symbols:
    csv_file = job_data.get('csv_file')
    if csv_file:
        symbols = load_symbols_from_csv(csv_file)
    else:
        logger.error(f"No symbols or csv_file provided in job")
        return

# Priority 3: Log what we're actually processing
source = job_data.get('source', 'unknown')
logger.info(f"Processing {len(symbols)} symbols from {source}")
logger.info(f"Symbols: {symbols}")
```

### Step 3: Add Logging for Debugging

Add these log statements immediately after receiving the job:
```python
logger.info(f"Received job: {job_id}")
logger.info(f"Job type: {job_data.get('job_type')}")
logger.info(f"Source: {job_data.get('source')}")
logger.info(f"Symbols in message: {job_data.get('symbols')}")
logger.info(f"CSV file in message: {job_data.get('csv_file')}")
logger.info(f"Years: {job_data.get('years')}")
```

This will show exactly what TickStockPL is receiving and help verify the fix.

### Step 4: Remove Hard-coded Defaults

**CRITICAL**: Remove any code that defaults to `sp_500.csv` or any specific CSV file:

**WRONG:**
```python
csv_file = job_data.get('csv_file', 'sp_500.csv')  # ← Remove this!
```

**CORRECT:**
```python
csv_file = job_data.get('csv_file')  # No default
if csv_file:
    # Only use CSV if explicitly provided
```

---

## Testing Instructions

### Test 1: Cached Universe (Core ETFs)

**From TickStockAppV2:**
1. Navigate to `/admin/historical-data`
2. Select "Cached Universe" radio button
3. Select "Core ETFs (3 symbols)"
4. Duration: "1 Day"
5. Click "Load Universe Data"

**Expected TickStockPL Logs:**
```
Processing job universe_load_XXXXX: csv_universe_load
Received job: universe_load_XXXXX
Source: etf_universe:etf_core
Symbols in message: ['SPY', 'QQQ', 'IWM']
Processing 3 symbols from etf_universe:etf_core
Symbols: ['SPY', 'QQQ', 'IWM']
Loading data for SPY...
Loading data for QQQ...
Loading data for IWM...
```

**NOT:**
```
CSV Universe Load: sp_500.csv  ← This should NOT appear!
Read 380 symbols from sp_500.csv  ← This should NOT happen!
```

### Test 2: CSV File (Backward Compatibility)

**From TickStockAppV2:**
1. Select "CSV File" radio button
2. Select "dow_30.csv"
3. Duration: "1 Day"
4. Click "Load Universe Data"

**Expected TickStockPL Logs:**
```
Processing job universe_load_XXXXX: csv_universe_load
CSV file in message: dow_30.csv
Symbols in message: None (or empty)
Reading symbols from CSV: dow_30.csv
Loaded 30 symbols from dow_30.csv
Processing 30 symbols from dow_30.csv
```

---

## Verification Checklist

After making the fix, verify:

- [ ] TickStockPL logs show "Symbols in message: [...]" for every job
- [ ] Core ETFs job processes exactly 3 symbols: SPY, QQQ, IWM
- [ ] CSV file jobs still work (dow_30.csv loads 30 symbols)
- [ ] No jobs default to sp_500.csv unless explicitly requested
- [ ] Source is logged correctly (etf_universe:etf_core, dow_30.csv, etc.)
- [ ] Symbol count in logs matches what was requested

---

## Message Format Reference

### New Format (from AppV2 - cached universes):
```json
{
  "job_id": "universe_load_1764505476_6849",
  "job_type": "csv_universe_load",
  "source": "etf_universe:etf_core",
  "symbols": ["SPY", "QQQ", "IWM"],
  "years": 0.005,
  "submitted_at": "2025-11-30T06:24:36.709000"
}
```

**Key fields:**
- `symbols`: Array of ticker symbols (USE THIS FIRST!)
- `source`: Description of where symbols came from
- No `csv_file` field

### Old Format (from AppV2 - CSV files):
```json
{
  "job_id": "universe_load_XXXXX",
  "job_type": "csv_universe_load",
  "source": "dow_30.csv",
  "symbols": ["AAPL", "MSFT", ...],  // Now included!
  "csv_file": "dow_30.csv",          // Legacy field
  "years": 1,
  "submitted_at": "2025-11-30T..."
}
```

**Key fields:**
- `symbols`: Array already populated by AppV2 (USE THIS!)
- `csv_file`: Legacy field (for backward compatibility only)

---

## FAQ

**Q: Why is the job_type still called `csv_universe_load`?**
A: For backward compatibility. The name is misleading now - it handles both CSV files AND cached universes. The key is to use the `symbols` array, not the job_type name.

**Q: Should I change the job handler to check job_type?**
A: No. Just check for `symbols` array first. If it exists, use it. If not, fall back to reading CSV file.

**Q: What if neither `symbols` nor `csv_file` is provided?**
A: Log an error and reject the job. Never default to any specific file.

**Q: Should I remove CSV file support entirely?**
A: No. Keep it for backward compatibility, but make `symbols` array the primary method.

---

## Contact

If you have questions about this fix, contact the TickStockAppV2 team.

**Testing Support**: Run the monitoring script to see exact messages:
```bash
cd TickStockAppV2
python scripts/util/monitor_job_channel.py
```

This will show you exactly what Redis messages are being published.

---

**Status**: 🔴 BROKEN - TickStockPL ignores symbols array
**After Fix**: 🟢 FIXED - TickStockPL uses symbols array from message
