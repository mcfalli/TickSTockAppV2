# Sprint 63 - TickStockPL Multi-Timeframe Support

**Status**: 🚧 In Progress
**Start Date**: December 23, 2025
**Owner**: TickStockPL Developer
**Dependencies**: Sprint 62 (TickStockAppV2 UI Complete)

---

## 🎯 **Sprint Goal**

Update TickStockPL's job handler to support multi-timeframe historical data loading as implemented in Sprint 62's admin UI.

---

## 📋 **Background**

**Sprint 62 Delivered (TickStockAppV2):**
- ✅ Admin UI with multi-timeframe checkboxes (1min, hour, day, week, month)
- ✅ Universe selection from RelationshipCache
- ✅ Job submission with `timeframes` array parameter
- ✅ Form validation and CSRF protection

**Current Problem (TickStockPL):**
- ❌ Job handler ignores `timeframes` parameter
- ❌ Only some timeframes load (weekly/monthly work, daily/hourly/1min fail)
- ❌ Test results show: 0% daily, 10% 1-min, 70% hourly data loaded

---

## 🎯 **Sprint 63 Objectives**

1. **Update Job Handler** to read and process `timeframes` array from job message
2. **Load Data for ALL Timeframes** specified in the request
3. **Insert into Correct Tables** (ohlcv_1min, ohlcv_hourly, ohlcv_daily, ohlcv_weekly, ohlcv_monthly)
4. **Report Progress Accurately** per symbol × timeframe combination
5. **Pass All Test Scenarios** (see requirements document)

---

## 📁 **Sprint 63 Documents**

| Document | Purpose | Status |
|----------|---------|--------|
| **[TICKSTOCKPL_MULTI_TIMEFRAME_REQUIREMENTS.md](./TICKSTOCKPL_MULTI_TIMEFRAME_REQUIREMENTS.md)** | Complete technical requirements | ✅ Ready |
| **README.md** (this file) | Sprint overview | ✅ Ready |
| **TESTING_RESULTS.md** | Test execution results | 🔜 Pending |
| **SPRINT63_COMPLETE.md** | Completion summary | 🔜 Pending |

---

## 🔑 **Key Changes Required**

### **1. Job Message Format (Input)**
```json
{
  "job_id": "uuid",
  "job_type": "csv_universe_load",
  "symbols": ["AAPL", "MSFT", ...],
  "timeframes": ["1min", "hour", "day", "week", "month"],  // NEW
  "years": 0.003
}
```

### **2. Timeframe-to-Table Mapping**
```python
{
  '1min': 'ohlcv_1min',
  'hour': 'ohlcv_hourly',
  'day': 'ohlcv_daily',
  'week': 'ohlcv_weekly',
  'month': 'ohlcv_monthly'
}
```

### **3. Processing Logic**
```python
for symbol in symbols:
    for timeframe in timeframes:  # Process ALL timeframes
        data = fetch_ohlcv(symbol, timeframe, start_date, end_date)
        table = get_table_name(timeframe)
        insert_ohlcv(table, symbol, data)
        update_progress(...)
```

---

## 🧪 **Test Scenarios**

| Test | Symbols | Timeframes | Duration | Expected Result |
|------|---------|------------|----------|-----------------|
| **Test 1** | AAPL (1) | day | 1 week | 5 daily rows |
| **Test 2** | AAPL, MSFT, INTC (3) | hour, day, week | 1 week | 105 hourly, 15 daily, 3 weekly |
| **Test 3** | DIA (30) | All 5 | 1 day | ~11,700 1min, ~195 hourly, 30 daily, 30 weekly, 30 monthly |

See [TICKSTOCKPL_MULTI_TIMEFRAME_REQUIREMENTS.md](./TICKSTOCKPL_MULTI_TIMEFRAME_REQUIREMENTS.md) for detailed test specifications.

---

## ✅ **Acceptance Criteria**

1. ✅ Job handler reads `timeframes` field from job message
2. ✅ All specified timeframes are loaded (not skipped)
3. ✅ Data inserted into correct tables based on timeframe
4. ✅ Progress updates show current symbol and timeframe
5. ✅ All 3 test scenarios pass with expected row counts
6. ✅ No data loss (100% of symbols × timeframes loaded)

---

## 📊 **Current Issues (From Testing)**

### **Issue #1: Daily Timeframe - 0 Rows ❌**
- **Symptom**: `SELECT COUNT(*) FROM ohlcv_daily` returns 0
- **Expected**: 30 rows for DIA 1-day load
- **Likely Cause**: Handler not processing `'day'` timeframe

### **Issue #2: 1-Minute Data - Only 3/30 Symbols ❌**
- **Symptom**: Only AAPL, MSFT, INTC have 1-min data
- **Expected**: All 30 DIA symbols
- **Likely Cause**: API rate limiting or early loop exit

### **Issue #3: Hourly Data - Missing 9/30 Symbols ⚠️**
- **Symptom**: 21/30 symbols loaded
- **Missing**: AMGN, CSCO, GS, HON, JNJ, MCD, MMM, TRV, WBA
- **Likely Cause**: Symbol-specific API failures not logged

---

## 🚀 **Implementation Workflow**

### **Phase 1: Code Updates**
1. Read requirements document
2. Update job handler to process `timeframes` array
3. Implement timeframe-to-table mapping
4. Update progress reporting logic

### **Phase 2: Testing**
1. Run Test 1 (single timeframe, single symbol)
2. Verify SQL results match expectations
3. Run Test 2 (multiple timeframes, 3 symbols)
4. Run Test 3 (all timeframes, 30 symbols)

### **Phase 3: Validation**
1. Verify all 5 OHLCV tables have data
2. Check row counts match expectations
3. Confirm job status updates correctly
4. Document results in TESTING_RESULTS.md

### **Phase 4: Completion**
1. All tests passing
2. Create SPRINT63_COMPLETE.md
3. Update BACKLOG.md with any deferred items
4. Coordinate with TickStockAppV2 for end-to-end testing

---

## 📞 **Communication**

**Questions/Issues**: Contact TickStockAppV2 Developer via project communication channel

**Testing Coordination**: Report test results after each test scenario

**Code Review**: Share implementation approach before starting Phase 2

---

## 📚 **Related Documentation**

- **Sprint 62**: [docs/planning/sprints/sprint62/SPRINT62_COMPLETE.md](../sprint62/SPRINT62_COMPLETE.md)
- **RelationshipCache**: [src/core/services/relationship_cache.py](../../../src/core/services/relationship_cache.py)
- **Admin UI**: [web/templates/admin/historical_data_dashboard.html](../../../web/templates/admin/historical_data_dashboard.html)

---

## 📈 **Success Metrics**

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Daily timeframe coverage | 100% | 0% | ❌ |
| 1-min timeframe coverage | 100% | 10% | ❌ |
| Hourly timeframe coverage | 100% | 70% | ⚠️ |
| Weekly timeframe coverage | 100% | 97% | ✅ |
| Monthly timeframe coverage | 100% | 97% | ✅ |
| **Overall data completeness** | **100%** | **~55%** | **❌** |

**Target**: All metrics at 100% after Sprint 63 completion

---

**Next Steps**: Developer to review TICKSTOCKPL_MULTI_TIMEFRAME_REQUIREMENTS.md and begin Phase 1 implementation.
