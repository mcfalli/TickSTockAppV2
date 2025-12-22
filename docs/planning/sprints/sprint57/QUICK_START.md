# Sprint 57: Quick Start Guide
## Cache-Based Universe Loading & Organization

**Get started in 5 minutes**

---

## What Is This Sprint?

Sprint 57 modernizes universe management by:
1. **Eliminating CSV file dependencies**: Load universes from database cache instead
2. **Professionalizing cache maintenance**: Move from UI buttons to dedicated scripts

---

## Quick Reference

### Current State → New State

**Universe Loading:**
```
BEFORE (Sprint 56):
CSV File → Parse → Load → OHLCV Data

AFTER (Sprint 57):
Database Query → Load → OHLCV Data
```

**Cache Organization:**
```
BEFORE:
UI Button → Web Request → Database Update

AFTER:
Command Line Script → Database Update
```

---

## For Developers: Quick Implementation

### 1. Read Documentation (10 min)
```bash
# Start here
docs/planning/sprints/sprint57/README.md

# Then detailed guide
docs/planning/sprints/sprint57/IMPLEMENTATION_GUIDE.md

# Track progress
docs/planning/sprints/sprint57/IMPLEMENTATION_CHECKLIST.md
```

### 2. Create Feature Branch
```bash
cd C:\Users\McDude\TickStockAppV2
git checkout -b feature/sprint57-cache-based-loading
```

### 3. Implement Phase 1 (TickStockPL)

**Create**: `C:\Users\McDude\TickStockPL\src\database\cache_operations.py`
- Copy from IMPLEMENTATION_GUIDE.md

**Update**: `C:\Users\McDude\TickStockPL\src\jobs\data_load_handler.py`
- Add cache query methods
- Update `_execute_csv_universe_load()`

### 4. Implement Phase 2 (TickStockAppV2)

**Create**: `scripts/cache_maintenance/organize_universes.py`
- Copy from IMPLEMENTATION_GUIDE.md

**Run**:
```bash
python scripts/cache_maintenance/organize_universes.py --dry-run
python scripts/cache_maintenance/organize_universes.py
```

### 5. Update UI

**Edit**: `web/templates/admin/historical_data_dashboard.html`
- Comment out "Cache Organization" section
- Add script instructions

### 6. Test

**Test cache-based loading**:
1. Open Historical Data admin page
2. Select "Cached Universe" → "Core ETFs"
3. Load 1 day of data
4. Verify success in logs

**Verify**:
```bash
# TickStockPL logs should show:
tail -f logs/tickstockpl.log | grep "Loading from cache"
```

---

## For Operators: Quick Usage

### Run Cache Organization

```bash
cd C:\Users\McDude\TickStockAppV2

# Preview changes
python scripts/cache_maintenance/organize_universes.py --dry-run

# Execute
python scripts/cache_maintenance/organize_universes.py
```

### Verify Cache Entries

```sql
-- List all universes
SELECT type, name, key,
       jsonb_array_length(value) as symbol_count,
       updated_at
FROM cache_entries
WHERE type IN ('etf_universe', 'stock_etf_combo')
ORDER BY type, name;
```

### Test Universe Load

1. Open Historical Data admin dashboard
2. Data Source: **Cached Universe**
3. Select: **Core ETFs**
4. Duration: **1 Day**
5. Click: **Load Universe Data**
6. Monitor job completion

---

## For Users: What Changed?

### UI Changes

**Historical Data Admin Page:**
- "Cache Organization" button **removed** (commented out)
- **New section** shows how to run maintenance scripts
- Everything else works exactly the same

### Universe Loading

**No visible changes** - works the same way:
1. Select universe from dropdown
2. Choose duration
3. Click load
4. Job processes automatically

**Behind the scenes:**
- Faster loading (database query vs file read)
- No CSV file dependencies
- Easier to add/update universes

---

## Common Tasks

### Add New Universe

**Edit**: `scripts/cache_maintenance/organize_universes.py`

```python
'my_new_universe': {
    'name': 'My New Universe',
    'description': 'Custom universe description',
    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
}
```

**Run**:
```bash
python scripts/cache_maintenance/organize_universes.py --preserve
```

**Verify**:
```sql
SELECT * FROM cache_entries
WHERE key = 'my_new_universe';
```

### Update Existing Universe

**Option 1**: Edit script and re-run
```bash
python scripts/cache_maintenance/organize_universes.py
```

**Option 2**: Update via SQL
```sql
UPDATE cache_entries
SET value = '["SPY", "QQQ", "IWM", "DIA", "VOO"]'::jsonb,
    updated_at = NOW()
WHERE type = 'etf_universe' AND key = 'core_etfs';
```

### Check Universe Symbols

```sql
SELECT value
FROM cache_entries
WHERE type = 'etf_universe' AND key = 'core_etfs';
```

---

## Troubleshooting

### Issue: Universe not in dropdown

**Fix**:
1. Run organization script: `python scripts/cache_maintenance/organize_universes.py`
2. Restart Flask app to reload cache
3. Refresh browser

### Issue: Job fails with "Universe not found"

**Fix**:
```sql
-- Check if universe exists
SELECT * FROM cache_entries WHERE key = 'your_universe_key';

-- If missing, run organization script
```

### Issue: Wrong symbols loaded

**Fix**:
```sql
-- Check current symbols
SELECT value FROM cache_entries WHERE key = 'your_universe_key';

-- Update if incorrect
UPDATE cache_entries
SET value = '["CORRECT", "SYMBOLS", "HERE"]'::jsonb
WHERE key = 'your_universe_key';
```

---

## File Locations

### TickStockPL
```
C:\Users\McDude\TickStockPL\
├── src\
│   ├── database\
│   │   └── cache_operations.py         (NEW - Phase 1)
│   └── jobs\
│       └── data_load_handler.py        (MODIFIED - Phase 1)
```

### TickStockAppV2
```
C:\Users\McDude\TickStockAppV2\
├── docs\planning\sprints\sprint57\
│   ├── README.md                       (This sprint overview)
│   ├── IMPLEMENTATION_GUIDE.md         (Detailed code examples)
│   ├── IMPLEMENTATION_CHECKLIST.md     (Progress tracker)
│   └── QUICK_START.md                  (You are here)
├── scripts\cache_maintenance\
│   ├── organize_universes.py           (NEW - Phase 2)
│   ├── validate_cache.py               (TODO - Sprint 57.1)
│   └── README.md                       (Script documentation)
├── web\templates\admin\
│   └── historical_data_dashboard.html  (MODIFIED - Phase 3)
└── src\infrastructure\cache\
    └── cache_control.py                (UNCHANGED - existing)
```

---

## Success Metrics

After Sprint 57:
- ✅ Zero CSV file dependencies for universe loading
- ✅ Cache queries < 10ms
- ✅ Universe loading works identically to Sprint 56
- ✅ Cache organization via scripts (not UI)
- ✅ All existing features working

---

## Next Steps

After completing Sprint 57:
1. **Sprint 57.1**: Cache validation script
2. **Sprint 57.2**: Bulk symbol loader
3. **Sprint 58**: Remove CSV files entirely (optional)
4. **Sprint 59**: Automated cache refresh jobs

---

## Support Resources

**Documentation:**
- Full guide: `docs/planning/sprints/sprint57/README.md`
- Implementation: `docs/planning/sprints/sprint57/IMPLEMENTATION_GUIDE.md`
- Progress: `docs/planning/sprints/sprint57/IMPLEMENTATION_CHECKLIST.md`
- Scripts: `scripts/cache_maintenance/README.md`

**Related Sprints:**
- Sprint 55: ETF Universe Integration (cache_entries creation)
- Sprint 56: Historical Data Enhancement (OHLCV loading)

**Project Docs:**
- CLAUDE.md: Development guidelines
- Architecture docs: `docs/architecture/`

---

**Estimated Time**: 2-3 days for full implementation
**Priority**: Medium-High
**Status**: Ready to start

**Questions?** Review the full README.md or IMPLEMENTATION_GUIDE.md for detailed information.

