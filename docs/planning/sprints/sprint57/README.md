# Sprint 57: Cache-Based Universe Loading & Organization Tooling

**Quick Reference Guide**

---

## Overview

**Type**: Architecture Enhancement + Tooling
**Priority**: MEDIUM-HIGH
**Estimated Effort**: 2-3 days
**Prerequisites**: Sprint 55 (ETF Universe Integration) + Sprint 56 (Historical Data Enhancement)

---

## What & Why

### The Goals

Sprint 57 addresses two critical improvements to universe management:

1. **Cache-Based Universe Loading**: Replace CSV file dependencies with database-driven universe loading
2. **Cache Organization Tooling**: Move cache management from UI to dedicated maintenance scripts
3. **Simplified Cache Architecture**: Standardize on two cache types only - `stock_universe` and `etf_universe`

### Why It Matters

- **Single Source of Truth**: `cache_entries` table becomes the authoritative source for all universes
- **Reduced File Dependencies**: Eliminates CSV file synchronization issues
- **Improved Maintainability**: Dedicated scripts for cache organization instead of ad-hoc UI operations
- **Better Scalability**: Database queries faster than CSV file parsing
- **Consistent Data**: All systems use same cache source
- **Cleaner Architecture**: Two types (`stock_universe`, `etf_universe`) instead of three, organized by indexes, sectors, and themes

---

## Quick Summary

### Changes Required

| Category | Current State | New State | Action |
|----------|--------------|-----------|--------|
| **CSV Loading** | TickStockPL reads CSV files | Query `cache_entries` table | Replace file reads with DB queries |
| **Universe Source** | `/data/universes/*.csv` | `cache_entries WHERE type IN ('stock_universe', 'etf_universe')` | Update loader logic |
| **Cache Types** | Multiple types (3+) | Two types only: `stock_universe`, `etf_universe` | Remove `stock_etf_combo` type |
| **Cache Organization** | Master lists, Indexes, Sectors, Themes | Organized hierarchy within two types | Structured naming conventions |
| **Cache Management** | UI button on Historical Data page | Standalone maintenance script | Move to `scripts/` directory |
| **Cache Maintenance** | Manual UI trigger | Scheduled/ad-hoc script execution | Create script tooling |

### What Stays the Same

- ✅ Redis job submission flow (`tickstock.jobs.data_load`)
- ✅ TickStockPL job processing architecture
- ✅ Historical data API calls (Massive API Custom Bars)
- ✅ Database insert operations (OHLCV tables)
- ✅ UI universe dropdown functionality

---

## Problem Statement

### 1. CSV File Dependencies

**Current Issues:**
- TickStockPL depends on physical CSV files in `data/universes/`
- CSV files must be synchronized across environments
- File parsing slower than database queries
- No versioning or audit trail for CSV changes
- Manual file updates required for universe changes

**Example Current Flow:**
```
User selects "curated-etfs.csv" in UI
  ↓
TickStockAppV2 publishes job to Redis
  ↓
TickStockPL receives job with csv_file="curated-etfs.csv"
  ↓
TickStockPL reads /data/universes/curated-etfs.csv
  ↓
Parses CSV file → Loads symbols
```

### 2. Cache Organization in UI

**Current Issues:**
- "Update and Organize Cache" button on Historical Data admin page
- UI-based operation should be in maintenance scripts
- No scheduled or automated cache organization
- Difficult to integrate into CI/CD pipelines
- No command-line interface for operations

**Current Location:**
- HTML: `web/templates/admin/historical_data_dashboard.html` (lines 481-498)
- Route: `/admin/historical-data/rebuild-cache`
- Function: `rebuildCacheEntries()` (JavaScript)

---

## Solution Overview

### 1. Cache-Based Universe Loading

**New Flow:**
```
User selects "ETF Core" universe in UI
  ↓
TickStockAppV2 publishes job with universe_key="etf_core"
  ↓
TickStockPL receives job
  ↓
Queries cache_entries table:
  SELECT value FROM cache_entries
  WHERE type='etf_universe' AND key='etf_core'
  ↓
Extracts symbols from JSONB value → Loads data
```

**Benefits:**
- ✅ No file I/O overhead
- ✅ Database query caching
- ✅ Audit trail via `updated_at` timestamps
- ✅ Easy universe updates via SQL
- ✅ Consistent across environments

### 2. Cache Organization Scripts

**New Architecture:**
```
scripts/cache_maintenance/
├── organize_universes.py       # Main organization script
├── load_symbols.py             # Bulk symbol loader
├── validate_cache.py           # Cache integrity checks
└── README.md                   # Usage documentation
```

**Operations:**
- Build/rebuild universe entries
- Validate cache integrity
- Generate cache statistics
- Export cache to JSON/CSV for backup
- Import cache from JSON/CSV

---

## Implementation Plan

### Phase 1: Cache-Based Universe Loading (Day 1)

**TickStockPL Changes:**
1. Update `src/jobs/data_load_handler.py`:
   - Add `_load_symbols_from_cache()` method
   - Replace CSV file reads with database queries
   - Maintain backward compatibility with CSV (optional)

2. Update `src/data/universe_manager.py` (if exists):
   - Add cache query methods
   - Handle JSONB value extraction

3. Add database connection to job handler:
   - Reuse existing connection pool
   - Add query methods for cache_entries

**Database Queries:**
```sql
-- Get ETF universe symbols
SELECT value FROM cache_entries
WHERE type = 'etf_universe' AND key = $1;

-- Get stock universe symbols
SELECT value FROM cache_entries
WHERE type = 'stock_universe' AND key = $1;

-- List all available universes (two types only)
SELECT type, name, key,
       CASE
           WHEN jsonb_typeof(value) = 'array' THEN jsonb_array_length(value)
           ELSE 0
       END as symbol_count
FROM cache_entries
WHERE type IN ('stock_universe', 'etf_universe')
ORDER BY type, name, key;
```

**Cache Organization Structure:**
```
stock_universe:
  ├── master_all_stocks          (All tracked stocks)
  ├── index_sp500                (S&P 500 index)
  ├── index_nasdaq100            (NASDAQ 100 index)
  ├── index_dow30                (Dow Jones 30 index)
  ├── index_russell3000          (Russell 3000 index)
  ├── sector_technology          (Tech sector stocks)
  ├── sector_healthcare          (Healthcare sector stocks)
  ├── sector_financials          (Financial sector stocks)
  ├── theme_dividend             (Dividend-focused stocks)
  ├── theme_growth               (Growth stocks)
  └── theme_value                (Value stocks)

etf_universe:
  ├── master_all_etfs            (All tracked ETFs)
  ├── index_broad_market         (SPY, QQQ, IWM, DIA, etc.)
  ├── sector_sector_etfs         (XLF, XLK, XLV, etc.)
  ├── sector_bonds               (AGG, BND, TLT, etc.)
  ├── sector_international       (VEA, VWO, IEFA, EEM, etc.)
  ├── theme_growth_value         (VUG, VTV, SCHG, SCHV, etc.)
  └── theme_crypto               (IBIT, FBTC, GBTC, BITO, etc.)
```

### Phase 2: Cache Organization Tooling (Day 2)

**Create Scripts:**
1. `scripts/cache_maintenance/organize_universes.py`:
   - Load symbols from various sources
   - Organize into logical groups
   - Update cache_entries table
   - Generate summary report

2. `scripts/cache_maintenance/validate_cache.py`:
   - Check cache integrity
   - Validate symbol counts
   - Identify missing/stale entries
   - Report inconsistencies

3. `scripts/cache_maintenance/README.md`:
   - Usage instructions
   - Examples for common operations
   - Scheduling guidance

**UI Changes:**
1. Comment out "Cache Organization" section in HTML template
2. Add note pointing to maintenance scripts
3. Keep section for future re-enable if needed

### Phase 3: Testing & Validation (Day 3)

**Test Scenarios:**
1. Load universe from cache (ETF, combo)
2. Verify symbols match expected lists
3. Test cache organization script
4. Validate cache integrity
5. Test backward compatibility (if maintained)

---

## File Changes

### TickStockPL

| File | Action | Purpose |
|------|--------|---------|
| `src/jobs/data_load_handler.py` | MODIFY | Add cache query methods |
| `src/data/universe_manager.py` | CREATE/MODIFY | Cache management functions |
| `src/database/cache_operations.py` | CREATE | Database operations for cache_entries |

### TickStockAppV2

| File | Action | Purpose |
|------|--------|---------|
| `web/templates/admin/historical_data_dashboard.html` | MODIFY | Comment out cache organization section |
| `src/api/rest/admin_historical_data.py` | MODIFY | Comment out `/rebuild-cache` route |
| `scripts/cache_maintenance/organize_universes.py` | CREATE | Main organization script |
| `scripts/cache_maintenance/validate_cache.py` | CREATE | Validation script |
| `scripts/cache_maintenance/load_symbols.py` | CREATE | Bulk symbol loader |
| `scripts/cache_maintenance/README.md` | CREATE | Documentation |

---

## Configuration Changes

### No Environment Variable Changes

All configuration uses existing settings:
- `DATABASE_URI`: Existing database connection
- `REDIS_HOST/PORT`: Existing Redis configuration

### Database Schema

**No schema changes required** - `cache_entries` table already exists with:
- `type`: Universe type (**two types only**: `stock_universe`, `etf_universe`)
- `name`: Human-readable category name (e.g., "S&P 500 Index", "Technology Sector")
- `key`: Structured lookup key (e.g., `index_sp500`, `sector_technology`, `theme_dividend`)
- `value`: JSONB containing symbols array
- `updated_at`: Last modification timestamp

**Key Naming Convention**:
- `master_*` - Master lists (all stocks, all ETFs)
- `index_*` - Major indexes (SP500, NASDAQ100, DOW30, Russell3000)
- `sector_*` - Sector-based groupings (technology, healthcare, financials)
- `theme_*` - Thematic groupings (dividend, growth, value, ESG)

---

## Success Criteria

### Must Pass

- ✅ Universe loading works without CSV files
- ✅ Cache queries return correct symbol lists
- ✅ Historical data loads complete successfully
- ✅ Cache organization script functional
- ✅ Cache validation script detects issues
- ✅ UI "Cache Organization" section commented out
- ✅ No regression in existing functionality
- ✅ Performance equal or better than CSV loading

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Cache Query | <10ms | Single universe lookup |
| Universe Load | Same as Sprint 56 | No performance degradation |
| Cache Organization | <60s | Full rebuild of all universes |
| Cache Validation | <30s | Check all entries |

---

## Testing Checklist

### Unit Tests
- [ ] `_load_symbols_from_cache()` returns correct symbols
- [ ] Database query handles missing keys gracefully
- [ ] JSONB value extraction works for all formats
- [ ] Error handling for database connection failures

### Integration Tests
- [ ] ETF universe loads from cache
- [ ] Stock+ETF combo loads from cache
- [ ] Historical data load completes (1-year test)
- [ ] Redis job flow unchanged

### Script Tests
- [ ] Cache organization script runs without errors
- [ ] Validation script detects test inconsistencies
- [ ] Symbol loader adds new universes correctly

### Manual Verification
- [ ] UI universe dropdown still works
- [ ] Load job completes with cache-sourced symbols
- [ ] Cache organization button hidden/commented
- [ ] Script execution via command line works

---

## Rollback Plan

**If critical issues arise:**

### Quick Revert (TickStockPL)
```python
# In data_load_handler.py - add feature flag
USE_CACHE_UNIVERSES = os.getenv('USE_CACHE_UNIVERSES', 'false') == 'true'

if USE_CACHE_UNIVERSES:
    symbols = self._load_symbols_from_cache(universe_key)
else:
    symbols = self._load_symbols_from_csv(csv_file)  # Existing code
```

### Full Rollback
1. Revert `data_load_handler.py` changes
2. Uncomment UI cache organization section
3. Restore CSV file dependencies
4. Set `USE_CACHE_UNIVERSES=false`

---

## Related Documentation

- **Sprint 55**: ETF Universe Integration (cache_entries usage)
- **Sprint 56**: Historical Data Enhancement (OHLCV loading architecture)
- **Cache Documentation**: `docs/architecture/cache-control.md`
- **Database Schema**: `docs/database/schema.md`

---

## Next Steps

After Sprint 57 completion:
1. Monitor cache-based loading performance
2. Consider removing CSV files entirely (Sprint 58?)
3. Add automated cache refresh jobs
4. Implement cache versioning/rollback
5. Add cache export/import for disaster recovery

---

**Status**: Ready for Implementation
**Last Updated**: 2025-12-02
**Next Sprint**: TBD

