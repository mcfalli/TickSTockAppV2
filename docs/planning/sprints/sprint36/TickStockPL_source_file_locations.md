# Source File Locations for Cache Reorganization Migration

**Sprint**: 36
**Date**: 2025-01-25
**Purpose**: Complete source file paths for TickStockPL developer to reference

## Primary Source Files to Copy/Reference

### 1. Main Implementation File (COPY THIS)
```
C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py
```
- 881 lines of Python code
- Contains the complete CacheEntriesSynchronizer class
- This is the main file to migrate to TickStockPL

### 2. Execution Script (REFERENCE)
```
C:\Users\McDude\TickStockAppV2\scripts\cache_management\run_cache_synchronization.py
```
- Shows how the synchronizer is currently executed
- Contains command-line argument handling

### 3. Admin Integration (REFERENCE - Lines 645-685)
```
C:\Users\McDude\TickStockAppV2\src\api\rest\admin_historical_data.py
```
- See how it's currently triggered from admin interface
- Lines 645-685 contain the cache sync trigger function

### 4. Documentation Files (REFERENCE)
```
C:\Users\McDude\TickStockAppV2\docs\operations\cache-synchronization-guide.md
C:\Users\McDude\TickStockAppV2\docs\operations\historical-data-and-cache-process-guide.md
```
- Operational documentation about the current implementation

### 5. Test Files (REFERENCE)

#### Primary Test File:
```
C:\Users\McDude\TickStockAppV2\tests\data_processing\sprint_14_phase3\test_cache_entries_synchronizer.py
```

#### Additional Test Files:
```
C:\Users\McDude\TickStockAppV2\tests\infrastructure\database\sprint_12\test_cache_entries_synchronizer_unit.py
C:\Users\McDude\TickStockAppV2\tests\infrastructure\database\sprint_12\test_cache_entries_synchronizer_integration.py
C:\Users\McDude\TickStockAppV2\tests\infrastructure\database\sprint_12\test_cache_entries_synchronizer_performance.py
C:\Users\McDude\TickStockAppV2\tests\infrastructure\database\sprint_12\test_cache_entries_synchronizer_error_handling.py
```

### 6. Related Sprint Documentation
```
C:\Users\McDude\TickStockAppV2\docs\planning\sprint_history\sprint14\cach_entries_directions.md
C:\Users\McDude\TickStockAppV2\docs\planning\sprint_history\sprint14\sprint14-phase3-implementation-plan.md
```

## Database Schema Reference

The job works with these tables (already exist in your database):

### cache_entries Table
```sql
-- This table already exists in the database
-- Location of schema reference:
C:\Users\McDude\TickStockAppV2\scripts\database\schema\cache_entries.sql
```

### symbols Table
```sql
-- Source of market cap and company data
-- The job reads from this table
```

### ohlcv_daily Table
```sql
-- Source of latest close prices for market cap calculation
-- The job reads from this table
```

## Key Functions to Migrate

From `C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py`:

| Function | Start Line | Description |
|----------|------------|-------------|
| `__init__` | 59 | Constructor with config |
| `daily_cache_sync` | 170 | Main entry point |
| `perform_synchronization` | 203 | Core sync logic |
| `market_cap_recalculation` | 268 | Market cap universe updates |
| `ipo_universe_assignment` | 378 | IPO detection and assignment |
| `delisted_cleanup` | 497 | Remove inactive stocks |
| `theme_rebalancing` | 596 | Theme universe updates |
| `rebuild_stock_cache_entries` | 700 | Full rebuild function |

## Configuration Values

From `C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py`:

Lines 69-75: Market Cap Thresholds
```python
self.market_cap_thresholds = {
    'mega_cap': 200e9,      # $200B+
    'large_cap': 10e9,      # $10B - $200B
    'mid_cap': 2e9,         # $2B - $10B
    'small_cap': 300e6,     # $300M - $2B
    'micro_cap': 50e6       # $50M - $300M
}
```

Lines 77-83: Universe Limits
```python
self.universe_limits = {
    'top_100': 100,
    'top_500': 500,
    'top_1000': 1000,
    'top_2000': 2000
}
```

Lines 86-91: Redis Channels
```python
self.channels = {
    'cache_sync_complete': 'tickstock.cache.sync_complete',
    'universe_updated': 'tickstock.universe.updated',
    'ipo_assignment': 'tickstock.cache.ipo_assignment',
    'delisting_cleanup': 'tickstock.cache.delisting_cleanup'
}
```

## Copy Command for TickStockPL

To copy the main file to TickStockPL:
```bash
# From TickStockPL directory
cp "C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py" src/jobs/daily_cache_sync_job.py
```

## Notes

1. The main file to migrate is `cache_entries_synchronizer.py` (881 lines)
2. All paths above are absolute Windows paths starting with `C:\Users\McDude\TickStockAppV2\`
3. The job should be integrated as Phase 2.5 in your daily processing pipeline
4. It runs AFTER data import (Phase 2) is complete because it needs updated OHLCV data
5. Expected runtime: 5-30 minutes depending on data size

## Questions?

If you need to examine any of these files, use the full path starting with:
```
C:\Users\McDude\TickStockAppV2\
```