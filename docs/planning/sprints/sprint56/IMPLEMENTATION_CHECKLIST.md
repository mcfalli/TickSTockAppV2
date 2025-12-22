# Sprint 56: Implementation Checklist

**Track progress as you implement the historical data load enhancement**

---

## Pre-Implementation Setup

### Environment Verification
- [ ] Massive API key obtained
- [ ] Massive API key added to `.env` file (`MASSIVE_API_KEY=...`)
- [ ] Database credentials verified in `.env`
- [ ] Redis connection verified in `.env`
- [ ] TickStockPL repository cloned/updated
- [ ] Python environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)

### Code Backup
- [ ] Current job handler backed up
- [ ] Git branch created for Sprint 56 (`sprint56/historical-data-enhancement`)
- [ ] Initial commit made

### Documentation Review
- [ ] Read `SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md` completely
- [ ] Understand Custom Bars API usage
- [ ] Review expected bar counts table
- [ ] Understand 2-day hourly constraint

---

## Day 1: API Integration & Database Operations

### API Client Implementation
- [ ] Create directory: `src/api/` (if not exists)
- [ ] Create file: `src/api/__init__.py`
- [ ] Create file: `src/api/massive_client.py`
- [ ] Copy `call_massive_api()` function
- [ ] Copy `fetch_custom_bars()` function
- [ ] Add necessary imports (`requests`, `datetime`, `logging`)
- [ ] Add docstrings and type hints
- [ ] Test API call independently:
  ```python
  from src.api.massive_client import fetch_custom_bars
  from datetime import date, timedelta

  # Test daily bars for AAPL
  end = date.today()
  start = end - timedelta(days=5)
  bars = fetch_custom_bars('AAPL', 1, 'day', start, end)
  print(f"Fetched {len(bars)} bars")
  # Expected: ~5 bars (1 week of trading days)
  ```
- [ ] Verify API response format matches expected structure
- [ ] Commit: `feat: Add Massive API Custom Bars client`

### Database Operations Implementation
- [ ] Create directory: `src/database/` (if not exists)
- [ ] Create file: `src/database/__init__.py`
- [ ] Create file: `src/database/ohlcv_operations.py`
- [ ] Copy `get_db_connection()` context manager
- [ ] Copy `insert_hourly_bars()` function
- [ ] Copy `insert_daily_bars()` function
- [ ] Copy `insert_weekly_bars()` function
- [ ] Copy `insert_monthly_bars()` function
- [ ] Add necessary imports (`psycopg2`, `execute_batch`)
- [ ] Test database insert independently:
  ```python
  from src.database.ohlcv_operations import insert_daily_bars
  from datetime import datetime

  # Test insert with sample data
  test_bars = [{
      'date': datetime(2023, 1, 3),
      'open': 100.0,
      'high': 105.0,
      'low': 99.0,
      'close': 103.0,
      'volume': 1000000
  }]

  inserted = insert_daily_bars('TEST', test_bars)
  print(f"Inserted {inserted} bars")
  # Expected: 1
  ```
- [ ] Verify ON CONFLICT works (re-run same insert, should update)
- [ ] Clean up test data: `DELETE FROM ohlcv_daily WHERE symbol = 'TEST'`
- [ ] Commit: `feat: Add batch OHLCV insert operations`

### Dependency Updates
- [ ] Add to `requirements.txt`:
  ```
  requests>=2.31.0
  psycopg2-binary>=2.9.9
  ```
- [ ] Run `pip install -r requirements.txt`
- [ ] Commit: `chore: Add API and database dependencies`

---

## Day 2: Job Handler Enhancement

### Code Preparation
- [ ] Locate existing job handler file (likely `src/jobs/universe_load_handler.py`)
- [ ] Review existing `handle_csv_universe_load()` function
- [ ] Identify where OHLCV fetch/insert should be added
- [ ] Backup original function

### Import Updates
- [ ] Add imports at top of file:
  ```python
  from src.api.massive_client import fetch_custom_bars
  from src.database.ohlcv_operations import (
      insert_hourly_bars,
      insert_daily_bars,
      insert_weekly_bars,
      insert_monthly_bars
  )
  from datetime import datetime, timedelta
  ```

### Hourly Data Logic
- [ ] Calculate hourly date range (max 2 days)
- [ ] Add hourly fetch logic:
  ```python
  hourly_bars = fetch_custom_bars(symbol, 1, 'hour', hourly_start, hourly_end)
  ```
- [ ] Add hourly insert logic:
  ```python
  inserted_hourly = insert_hourly_bars(symbol, hourly_bars)
  ```
- [ ] Add logging:
  ```python
  logger.info(f"✓ Fetched {len(hourly_bars)} hourly bars")
  logger.info(f"✓ Inserted {inserted_hourly} bars into ohlcv_hourly")
  ```
- [ ] Add to results tracking: `results['hourly_bars'] += inserted_hourly`

### Daily Data Logic
- [ ] Calculate daily date range (full timeframe)
- [ ] Add daily fetch logic:
  ```python
  daily_bars = fetch_custom_bars(symbol, 1, 'day', start_date, end_date)
  ```
- [ ] Add validation (fail if no daily data)
- [ ] Add daily insert logic:
  ```python
  inserted_daily = insert_daily_bars(symbol, daily_bars)
  ```
- [ ] Add logging
- [ ] Add to results tracking: `results['daily_bars'] += inserted_daily`

### Weekly Data Logic (NEW)
- [ ] Add weekly fetch logic:
  ```python
  weekly_bars = fetch_custom_bars(symbol, 1, 'week', start_date, end_date)
  ```
- [ ] Add weekly insert logic:
  ```python
  inserted_weekly = insert_weekly_bars(symbol, weekly_bars)
  ```
- [ ] Add logging
- [ ] Add to results tracking: `results['weekly_bars'] += inserted_weekly`
- [ ] Handle case where timeframe too short (0 bars expected)

### Monthly Data Logic (NEW)
- [ ] Add monthly fetch logic:
  ```python
  monthly_bars = fetch_custom_bars(symbol, 1, 'month', start_date, end_date)
  ```
- [ ] Add monthly insert logic:
  ```python
  inserted_monthly = insert_monthly_bars(symbol, monthly_bars)
  ```
- [ ] Add logging
- [ ] Add to results tracking: `results['monthly_bars'] += inserted_monthly`
- [ ] Handle case where timeframe too short (0 bars expected)

### Results Tracking
- [ ] Update `results` dict initialization:
  ```python
  results = {
      'symbols_loaded': 0,
      'symbols_failed': 0,
      'hourly_bars': 0,    # NEW
      'daily_bars': 0,
      'weekly_bars': 0,    # NEW
      'monthly_bars': 0,   # NEW
      'errors': []
  }
  ```
- [ ] Update final logging to show all 4 timeframe counts

### Error Handling
- [ ] Wrap each fetch/insert in try/except
- [ ] Log errors with symbol name and timeframe
- [ ] Continue processing other symbols on error
- [ ] Track errors in `results['errors']`

### Commit
- [ ] Review all changes
- [ ] Test syntax (no import errors)
- [ ] Commit: `feat: Enhance job handler with complete OHLCV data loading`

---

## Day 3: Testing & Validation

### Test Setup
- [ ] Clear old test data:
  ```sql
  DELETE FROM ohlcv_hourly WHERE symbol IN ('SCHG', 'VUG', 'SPY');
  DELETE FROM ohlcv_daily WHERE symbol IN ('SCHG', 'VUG', 'SPY');
  DELETE FROM ohlcv_weekly WHERE symbol IN ('SCHG', 'VUG', 'SPY');
  DELETE FROM ohlcv_monthly WHERE symbol IN ('SCHG', 'VUG', 'SPY');
  ```
- [ ] Verify TickStockPL services running
- [ ] Verify TickStockAppV2 admin UI accessible
- [ ] Monitor logs in separate terminal: `tail -f logs/tickstock.log`

### Test 1: SCHG & VUG 2-Day Load
- [ ] Navigate to TickStockAppV2 `/admin/historical-data`
- [ ] Enter symbols: `SCHG,VUG`
- [ ] Select duration: **2 days**
- [ ] Click "Load Universe Data"
- [ ] Watch logs for:
  - [ ] "Symbols in message: ['SCHG', 'VUG']"
  - [ ] "Fetching hourly bars via Custom Bars API"
  - [ ] "✓ API returned X hour bars"
  - [ ] "✓ Inserted X bars into ohlcv_hourly"
  - [ ] Same for daily, weekly, monthly
- [ ] Wait for job completion (~1-2 minutes)
- [ ] Run verification queries:
  ```sql
  -- Hourly: expect ~13 bars each
  SELECT symbol, COUNT(*) FROM ohlcv_hourly
  WHERE symbol IN ('SCHG', 'VUG')
  GROUP BY symbol;

  -- Daily: expect 2 bars each
  SELECT symbol, COUNT(*) FROM ohlcv_daily
  WHERE symbol IN ('SCHG', 'VUG')
  GROUP BY symbol;

  -- Weekly: expect 1 bar each
  SELECT symbol, COUNT(*) FROM ohlcv_weekly
  WHERE symbol IN ('SCHG', 'VUG')
  GROUP BY symbol;

  -- Monthly: expect 1 bar each
  SELECT symbol, COUNT(*) FROM ohlcv_monthly
  WHERE symbol IN ('SCHG', 'VUG')
  GROUP BY symbol;
  ```
- [ ] **PASS/FAIL**: All counts within ±10% of expected? _________

### Test 2: SPY 90-Day Load
- [ ] Navigate to `/admin/historical-data`
- [ ] Enter symbol: `SPY`
- [ ] Select duration: **3 months** (90 days)
- [ ] Click "Load Universe Data"
- [ ] Watch logs for successful fetches
- [ ] Wait for job completion
- [ ] Run verification queries:
  ```sql
  -- Hourly: expect ~13 bars (max 2 days)
  SELECT COUNT(*) FROM ohlcv_hourly WHERE symbol = 'SPY';

  -- Daily: expect ~63 bars
  SELECT COUNT(*) FROM ohlcv_daily
  WHERE symbol = 'SPY'
    AND date >= CURRENT_DATE - INTERVAL '90 days';

  -- Weekly: expect ~13 bars
  SELECT COUNT(*) FROM ohlcv_weekly
  WHERE symbol = 'SPY'
    AND week_start >= CURRENT_DATE - INTERVAL '90 days';

  -- Monthly: expect 3 bars
  SELECT COUNT(*) FROM ohlcv_monthly
  WHERE symbol = 'SPY'
    AND month_start >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '90 days');
  ```
- [ ] **PASS/FAIL**: All counts within ±10% of expected? _________

### Data Quality Validation
- [ ] Check OHLC logic (High ≥ Low):
  ```sql
  SELECT symbol, date, high, low
  FROM ohlcv_daily
  WHERE symbol IN ('SCHG', 'VUG', 'SPY')
    AND high < low;
  -- Expected: 0 rows
  ```
- [ ] Check for NULL values:
  ```sql
  SELECT symbol, date
  FROM ohlcv_daily
  WHERE symbol IN ('SCHG', 'VUG', 'SPY')
    AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR volume IS NULL);
  -- Expected: 0 rows
  ```
- [ ] Check for negative prices:
  ```sql
  SELECT symbol, date, open, high, low, close
  FROM ohlcv_daily
  WHERE symbol IN ('SCHG', 'VUG', 'SPY')
    AND (open <= 0 OR high <= 0 OR low <= 0 OR close <= 0);
  -- Expected: 0 rows
  ```

### Performance Validation
- [ ] Check job completion time (should be <5 minutes for 3 symbols)
- [ ] Check API call count in logs
- [ ] Verify no rate limiting errors (429)
- [ ] Verify no timeout errors

---

## Success Criteria Verification

### Minimum Requirements
- [ ] ✅ Symbols registered in `symbols` table
- [ ] ✅ Hourly bars inserted for all symbols
- [ ] ✅ Daily bars inserted for all symbols
- [ ] ✅ Weekly bars inserted (if timeframe ≥ 1 week)
- [ ] ✅ Monthly bars inserted (if timeframe ≥ 1 month)
- [ ] ✅ Logs show "Symbols in message: [...]"
- [ ] ✅ Logs show API fetch calls
- [ ] ✅ Logs show successful inserts
- [ ] ✅ No API errors (404, 500) for valid symbols
- [ ] ✅ No database insertion errors

### Full Requirements
- [ ] ✅ SCHG/VUG test passes (bar counts ±10%)
- [ ] ✅ SPY test passes (bar counts ±10%)
- [ ] ✅ All OHLC validation passes (no high < low)
- [ ] ✅ No NULL values in OHLCV data
- [ ] ✅ No negative prices
- [ ] ✅ Job status "completed" in Redis
- [ ] ✅ Performance acceptable (<5 min for 3 symbols)

---

## Post-Implementation

### Code Quality
- [ ] Code review completed
- [ ] All functions have docstrings
- [ ] Type hints added where appropriate
- [ ] No hardcoded credentials
- [ ] Error handling comprehensive
- [ ] Logging at appropriate levels

### Documentation
- [ ] Code comments added for complex logic
- [ ] This checklist completed
- [ ] Sprint completion notes added to `SPRINT56_COMPLETE.md`
- [ ] CLAUDE.md updated with Sprint 56 status

### Integration
- [ ] All commits pushed to repository
- [ ] Pull request created (if using PR workflow)
- [ ] CI/CD tests passing
- [ ] Merged to main branch
- [ ] Tagged: `sprint56-complete`

### Monitoring
- [ ] Verify logs show successful jobs
- [ ] Check for any unexpected errors in production
- [ ] Monitor API usage/costs
- [ ] Verify job completion metrics

---

## Issues Encountered

**Document any blockers or issues:**

| Issue | Resolution | Date |
|-------|------------|------|
| Example: Rate limiting on large universe | Reduced batch size, added delays | 2025-12-01 |
|  |  |  |
|  |  |  |

---

## Final Checklist

- [ ] All tests passing
- [ ] All success criteria met
- [ ] Documentation complete
- [ ] Code committed and merged
- [ ] Team notified of completion
- [ ] Sprint 56 marked complete
- [ ] Ready for production deployment

---

**Sprint Status**: ☐ In Progress  ☐ Complete  ☐ Blocked

**Completion Date**: _________________

**Completed By**: _________________

**Notes**:
```
[Add any final notes here]
```
