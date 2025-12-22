# Universe Loader Consolidation - Sprint 55

## Context

**Problem**: Two separate, duplicate loading mechanisms for universe data:
- CSV Universe Loading (lines 351-441 in template)
- ETF Universe Loading (lines 443-512 in template)

**Issues**:
- Code duplication (162 lines of duplicate forms)
- Inconsistent features (CSV had `include_ohlcv`, ETF didn't)
- Maintenance burden (changes needed in two places)
- Both send same job type to TickStockPL anyway

**Solution**: Consolidate into single "Universe Data Loading" form with source toggle.

---

## ✅ Completed Work

### 1. HTML Template Consolidation
**File**: `web/templates/admin/historical_data_dashboard.html`
**Status**: ✅ COMPLETE (729 lines → 695 lines, removed 34 duplicate lines)

**Changes**:
- Removed duplicate CSV and ETF forms
- Added unified form with data source radio buttons (CSV / Cached Universe)
- CSV dropdown shown when "CSV File" selected
- Universe dropdown shown when "Cached Universe" selected
- Shared controls: duration, include_ohlcv, submit button
- Unified progress tracking

### 2. JavaScript Source Toggle
**File**: `web/static/js/admin/historical_data.js`
**Status**: ✅ COMPLETE (679 lines → 707 lines, added 28 lines)

**Changes**:
- Added `handleDataSourceToggle()` function
- Shows/hides appropriate dropdown based on radio selection
- Updated `initializeUniverseHandlers()` to handle source toggle
- Form validation for both sources

---

## ⏳ Remaining Work

### Step 1: Extend Backend Endpoint (REQUIRED)

**File**: `src/api/rest/admin_historical_data_redis.py`
**Function**: `trigger_universe_load()` starting at line 805
**Status**: ⏳ PENDING

**Current Behavior**: Only handles cached universes
**New Behavior**: Handle BOTH CSV files AND cached universes

**Required Changes**:

1. **Update function signature and docstring** (line 808-809):
```python
def trigger_universe_load():
    """Submit bulk load job for symbols from CSV file or cached universe (unified endpoint)."""
```

2. **Replace lines 810-862** with unified source detection:

```python
    try:
        # Get parameters
        csv_file = request.form.get('csv_file')
        universe_key_full = request.form.get('universe_key')
        years = request.form.get('years', 1, type=float)
        include_ohlcv = request.form.get('include_ohlcv', 'true') == 'true'

        symbols = []
        source_name = ''

        # Determine source: CSV file or cached universe
        if csv_file:
            # === CSV FILE MODE ===
            app.logger.info(f"CSV mode: {csv_file}, years={years}, OHLCV={include_ohlcv}")

            # Read symbols from CSV file
            import csv
            import os
            csv_path = os.path.join('data/universes', csv_file)

            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found: {csv_file}'}), 404

            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get('symbol', '').strip()
                    if symbol:
                        symbols.append(symbol)

            source_name = csv_file
            app.logger.info(f"Loaded {len(symbols)} symbols from CSV: {csv_file}")

        elif universe_key_full:
            # === CACHED UNIVERSE MODE ===
            app.logger.info(f"Cached mode: {universe_key_full}, years={years}")

            # Parse universe key (format: "etf_universe:etf_core")
            if ':' not in universe_key_full:
                return jsonify({'error': 'Invalid universe key format'}), 400

            universe_type, universe_key = universe_key_full.split(':', 1)

            # Get symbols from cache
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()

            if universe_type == 'etf_universe':
                for name, keys_dict in cache_control.cache.get('etf_universes', {}).items():
                    if universe_key in keys_dict:
                        value = keys_dict[universe_key]
                        symbols = value if isinstance(value, list) else value.get('symbols', [])
                        break

            elif universe_type == 'stock_etf_combo':
                for name, keys_dict in cache_control.cache.get('stock_etf_combos', {}).items():
                    if universe_key in keys_dict:
                        value = keys_dict[universe_key]
                        symbols = value if isinstance(value, list) else value.get('symbols', [])
                        break

            if not symbols:
                return jsonify({'error': f'No symbols found for: {universe_key}'}), 404

            source_name = universe_key_full
            app.logger.info(f"Found {len(symbols)} symbols from cache: {universe_key_full}")

        else:
            return jsonify({'error': 'Either csv_file or universe_key required'}), 400

        if not symbols:
            return jsonify({'error': f'No symbols found in {source_name}'}), 404

        app.logger.info(f"Total symbols to load: {len(symbols)} from {source_name}")
```

3. **Keep remaining code unchanged** (lines 863-920: job creation, Redis publish, status storage)
   - Job ID generation stays the same
   - Redis message stays the same
   - Job status storage stays the same
   - Return statement stays the same

**Expected Line Count**: ~950 lines (was ~920, added ~30 lines for CSV logic)

---

### Step 2: Remove Duplicate CSV Endpoint (OPTIONAL - CLEANUP)

**File**: `src/api/rest/admin_historical_data_redis.py`
**Function**: `admin_csv_universe_load()` at line 628-710
**Status**: ⏳ PENDING (optional cleanup)

**Action**: Can be removed since unified endpoint handles CSV files now.

**Note**: Not urgent - can be done later for cleanup.

---

### Step 3: Clear Old Redis Keys (REQUIRED BEFORE TESTING)

**Run this command** before testing:

```bash
cd C:/Users/McDude/TickStockAppV2
python scripts/util/clear_job_keys.py
```

**Purpose**: Remove old corrupted job status keys from previous testing

---

### Step 4: Restart Flask (REQUIRED)

**Stop Flask** (Ctrl+C)

**Start Flask**:
```bash
cd C:/Users/McDude/TickStockAppV2
python src/app.py
```

---

## Testing Instructions

### Test 1: CSV File Loading

1. Navigate to: http://localhost:5000/admin/historical-data
2. In "Universe Data Loading" section:
   - Select **"📋 CSV File"** radio button
   - CSV dropdown should appear, universe dropdown should hide
   - Select CSV file: `dow_30.csv`
   - Duration: `1 Day`
   - Include OHLCV: `Yes`
   - Click **"📊 Load Universe Data"**

**Expected**:
- Job submits successfully (200 OK)
- Toast notification: "Universe load submitted! Job ID: universe_load_..."
- Progress bar appears
- Status polling works without WRONGTYPE errors
- TickStockPL processes 30 symbols

### Test 2: Cached Universe Loading

1. In same "Universe Data Loading" section:
   - Select **"📦 Cached Universe"** radio button
   - Universe dropdown should appear, CSV dropdown should hide
   - Select universe: `Core ETFs (3 symbols)`
   - Duration: `1 Day`
   - Include OHLCV: `Yes`
   - Click **"📊 Load Universe Data"**

**Expected**:
- Job submits successfully (200 OK)
- Toast notification: "Universe load submitted! Job ID: universe_load_..."
- Progress bar appears
- Status polling works without WRONGTYPE errors
- TickStockPL processes 3 symbols

### Test 3: Toggle Behavior

1. Click back and forth between radio buttons
2. Verify dropdowns show/hide correctly
3. Verify no JavaScript errors in console

---

## Success Criteria

✅ Single unified form replaces two duplicate forms
✅ CSV files and cached universes both load via same endpoint
✅ Include OHLCV option works for both sources
✅ Job submission returns 200 OK
✅ Job status polling works without WRONGTYPE errors
✅ TickStockPL processes symbols correctly
✅ No console errors
✅ Code reduction: 34+ duplicate lines removed

---

## Rollback Plan

If issues occur, revert these commits:
1. Template consolidation
2. JavaScript source toggle
3. Backend endpoint changes

**Git commands**:
```bash
git log --oneline -5
git revert <commit-hash>
```

---

## Files Modified Summary

| File | Lines Before | Lines After | Change | Status |
|------|--------------|-------------|--------|--------|
| `web/templates/admin/historical_data_dashboard.html` | 729 | 695 | -34 | ✅ Complete |
| `web/static/js/admin/historical_data.js` | 679 | 707 | +28 | ✅ Complete |
| `src/api/rest/admin_historical_data_redis.py` | ~920 | ~950 | +30 | ⏳ Pending |

**Total Code Reduction**: -4 net lines (removed duplication, added unified logic)

---

## Next Steps After Restart

1. Apply Step 1 changes to backend endpoint (copy-paste code above)
2. Run Step 3 (clear Redis keys)
3. Run Step 4 (restart Flask)
4. Execute Testing Instructions (Test 1, 2, 3)
5. Verify Success Criteria
6. If all tests pass: Mark consolidation COMPLETE ✅
7. Optional: Apply Step 2 cleanup (remove old CSV endpoint)

---

**Document Created**: 2025-11-29
**Sprint**: 55
**Issue**: Duplicate universe loading mechanisms
**Solution**: Unified loader with source toggle
**Status**: 66% Complete (2/3 major steps done)
