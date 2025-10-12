# Sprint 42 Phase 1 - Validation Instructions

**Status**: ✅ TickStockPL Implementation Complete
**Next**: Validate integration before Phase 2

---

## Quick Validation (Manual)

### Step 1: Ensure Both Applications Running

**TickStockAppV2**:
```bash
cd C:\Users\McDude\TickStockAppV2
python app.py

# Should see: "Connected to data source with 70 tickers"
```

**TickStockPL**:
```bash
cd C:\Users\McDude\TickStockPL
python -m src.services.streaming_scheduler

# Should see:
# - "TICK-AGGREGATOR: Initialized"
# - "Completed bar for AAPL at ..."
```

**Wait 5 minutes** for data accumulation.

---

### Step 2: Run Validation Queries

**Option A - psql command line**:
```bash
psql -h localhost -p 5432 -U app_readwrite -d tickstock -f validate_phase1.sql
```

**Option B - DBeaver/pgAdmin** (copy-paste queries from `validate_phase1.sql`):

1. **Test 1: Verify bars created (CRITICAL)**
```sql
SELECT COUNT(*) as total_bars
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '5 minutes';
```
**Expected**: >= 200 bars
**Status**: PASS if >= 200, FAIL if < 200

2. **Test 2: Check pattern detections**
```sql
SELECT pattern_type, COUNT(*) as detections
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY pattern_type;
```
**Expected**: >0 patterns (optional - depends on data)
**Status**: PASS if any patterns, WARNING if 0 (acceptable)

3. **Test 3: Check duplicate bars (CRITICAL)**
```sql
SELECT symbol, timestamp, COUNT(*)
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY symbol, timestamp
HAVING COUNT(*) > 1;
```
**Expected**: 0 rows (no duplicates)
**Status**: PASS if 0 rows, FAIL if any rows

---

### Step 3: Verify Success Criteria

| Criterion | Test | Expected | Pass/Fail |
|-----------|------|----------|-----------|
| OHLCV bars created | Query 1 | >= 200 bars | [ ] |
| No duplicates | Query 3 | 0 rows | [ ] |
| Pattern detection functional | Query 2 | >0 patterns (optional) | [ ] |
| Bar distribution | Manual | ~70 symbols/minute | [ ] |

**If ALL critical tests PASS**: ✅ Proceed to Phase 2

**If ANY critical test FAILS**: ❌ Debug before Phase 2
- Check TickStockPL logs for errors
- Verify Redis connectivity
- Ensure synthetic data flowing from AppV2

---

## Phase 2 - Ready to Execute

**Once validation passes**, proceed to Phase 2:

### Phase 2 Overview
- **Task**: Remove OHLCVPersistenceService from TickStockAppV2
- **Duration**: 3-4 hours
- **Guide**: `IMPLEMENTATION_GUIDE.md` (Section: Phase 2)

### Phase 2 Steps Summary
1. Remove `src/infrastructure/database/ohlcv_persistence.py`
2. Update `src/core/services/market_data_service.py` (remove persistence integration)
3. Change database user to `app_readonly`
4. Run tests
5. Commit changes

**Detailed instructions**: See `IMPLEMENTATION_GUIDE.md` lines 245-504

---

## Troubleshooting

### Issue: No bars in database

**Debug**:
1. Check TickStockPL logs: `grep "TICK-AGGREGATOR" <logfile>`
2. Check Redis: `redis-cli monitor | grep "tickstock:market:ticks"`
3. Verify AppV2 running with synthetic data

### Issue: Duplicate bars

**Debug**:
1. Both AppV2 and TickStockPL are writing (expected until Phase 2)
2. After Phase 2, duplicates should stop
3. Clean up duplicates if needed (SQL in validation script)

---

## Confirmation Checklist

Before proceeding to Phase 2:

- [ ] TickStockAppV2 running with synthetic data
- [ ] TickStockPL streaming service running
- [ ] Test 1: >= 200 bars created (PASS)
- [ ] Test 3: 0 duplicate bars (PASS)
- [ ] Logs show "Completed bar for ..." messages
- [ ] No errors in TickStockPL logs

**All checked?** ✅ Proceed to Phase 2!

---

**Created**: October 10, 2025
**Sprint**: 42 - Architectural Realignment
**Phase**: 1 Validation → 2 Execution
