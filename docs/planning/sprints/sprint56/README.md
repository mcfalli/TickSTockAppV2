# Sprint 56: Historical Data Load Enhancement

**Quick Reference Guide**

---

## Overview

**Type**: Bug Fix + Architecture Enhancement
**Priority**: CRITICAL
**Estimated Effort**: 2-3 days
**Status**: Ready for Implementation

---

## Problem

TickStockPL historical data load jobs register symbols but **fail to fetch and insert OHLCV data** for any timeframe.

**Example**: SCHG & VUG 2-day load resulted in:
- ✅ Symbols registered
- ❌ 0 hourly bars
- ❌ 0 daily bars
- ❌ 0 weekly bars
- ❌ 0 monthly bars

---

## Solution

Enhance existing job handler to:
1. Fetch **pre-aggregated bars** from Massive API Custom Bars endpoint
2. Insert data for **all 4 timeframes** (hourly, daily, weekly, monthly)
3. Eliminate manual aggregation (API handles it)

---

## Key Changes

| Component | Change Type | Description |
|-----------|-------------|-------------|
| API Integration | **NEW** | Add `fetch_custom_bars()` using Massive Custom Bars API |
| Database Operations | **NEW** | Add batch insert functions for all timeframes |
| Job Handler | **ENHANCE** | Add missing OHLCV fetch/insert logic |
| Aggregation | **REMOVE** | Delete manual weekly/monthly aggregation code |

---

## Quick Start

### 1. Read Main Document
📄 **[SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md](./SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md)**

Contains:
- Complete implementation plan
- Code examples (copy-paste ready)
- Testing instructions
- Success criteria

### 2. Implementation Checklist

**Day 1: API & Database**
- [ ] Add `src/api/massive_client.py` (API client + `fetch_custom_bars()`)
- [ ] Add `src/database/ohlcv_operations.py` (insert functions)
- [ ] Configure environment variables (API key, DB credentials)
- [ ] Test API calls independently

**Day 2: Job Handler**
- [ ] Enhance `src/jobs/universe_load_handler.py`
- [ ] Add imports for new functions
- [ ] Replace missing OHLCV logic with 4 Custom Bars API calls
- [ ] Add comprehensive logging

**Day 3: Testing**
- [ ] Test SCHG/VUG 2-day load (expect 13 hourly, 2 daily, 1 weekly, 1 monthly)
- [ ] Test SPY 90-day load (expect 13 hourly, 63 daily, 13 weekly, 3 monthly)
- [ ] Verify all SQL validation queries pass
- [ ] Check logs for successful API calls and inserts

### 3. Verification Queries

After running test loads:

```sql
-- Quick check: All timeframes populated?
SELECT
    'hourly' as timeframe,
    symbol,
    COUNT(*) as bars
FROM ohlcv_hourly
WHERE symbol IN ('SCHG', 'VUG', 'SPY')
  AND timestamp >= NOW() - INTERVAL '2 days'
GROUP BY symbol

UNION ALL

SELECT 'daily', symbol, COUNT(*)
FROM ohlcv_daily
WHERE symbol IN ('SCHG', 'VUG', 'SPY')
  AND date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY symbol

UNION ALL

SELECT 'weekly', symbol, COUNT(*)
FROM ohlcv_weekly
WHERE symbol IN ('SCHG', 'VUG', 'SPY')
  AND week_start >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY symbol

UNION ALL

SELECT 'monthly', symbol, COUNT(*)
FROM ohlcv_monthly
WHERE symbol IN ('SCHG', 'VUG', 'SPY')
  AND month_start >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '90 days')
GROUP BY symbol

ORDER BY timeframe, symbol;
```

**Expected Results**:
- SCHG: 13 hourly, 2 daily, 1 weekly, 1 monthly
- VUG: 13 hourly, 2 daily, 1 weekly, 1 monthly
- SPY: 13 hourly, 63 daily, 13 weekly, 3 monthly

---

## Architecture Improvement

### Before (Broken)
```
Redis Job → Job Handler
             ↓
          Register Symbols ✅
             ↓
          [MISSING: OHLCV fetch/insert] ❌
```

### After (Sprint 56)
```
Redis Job → Job Handler
             ↓
          Register Symbols ✅
             ↓
          Fetch Hourly (Custom Bars API) ✅
             ↓
          Fetch Daily (Custom Bars API) ✅
             ↓
          Fetch Weekly (Custom Bars API) ✅
             ↓
          Fetch Monthly (Custom Bars API) ✅
             ↓
          Insert All Timeframes ✅
```

---

## Success Criteria

### Must Pass
- ✅ All 4 timeframes populated for every symbol
- ✅ Bar counts within 90% of expected values
- ✅ No API errors for valid symbols
- ✅ No database insertion errors
- ✅ Logs show successful fetches and inserts
- ✅ SCHG/VUG test passes
- ✅ SPY test passes

---

## Important Notes

1. **Hourly Data Constraint**: Maximum 2 days regardless of timeframe
   - 1-day load: 24 hours of data
   - 2+ day load: 48 hours of data (always capped)
   - 1-year load: Still only 48 hours of hourly data

2. **API Aggregation**: Weekly and monthly bars come pre-aggregated from API
   - Week starts: Sunday 12:00 AM EST (Massive convention)
   - Month starts: 1st of month
   - No manual aggregation needed

3. **Batch Inserts**: Use `execute_batch()` for performance
   - Faster than individual inserts
   - Handles ON CONFLICT for upserts

4. **Rate Limits**: Retry logic handles 429 errors
   - Exponential backoff: 5s, 10s, 20s
   - Max 3 retries per API call

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/api/massive_client.py` | CREATE | Massive API integration |
| `src/database/ohlcv_operations.py` | CREATE | Database insert operations |
| `src/jobs/universe_load_handler.py` | ENHANCE | Add OHLCV fetch/insert logic |
| `.env` | UPDATE | Add MASSIVE_API_KEY |
| `requirements.txt` | UPDATE | Add requests, psycopg2 |

---

## Related Documentation

- **Sprint 55**: ETF Universe Integration (completed)
- **Massive API Docs**: https://massive.com/docs/rest/stocks/aggregates/custom-bars
- **TickStock Architecture**: `docs/architecture/README.md`

---

## Support

**Questions?** Review the main implementation document first:
- [SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md](./SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md)

**Blockers?** Common issues:
- API key not configured → Check `.env` file
- Database connection error → Verify DB credentials
- Rate limiting (429) → Retry logic handles this automatically
- Missing bars → Check if symbol exists in Massive API (try 404 response)

---

**Last Updated**: 2025-12-01
**Sprint Status**: Ready for Implementation
