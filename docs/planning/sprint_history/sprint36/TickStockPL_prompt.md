# Sprint 36: Cache Reorganization Job Migration to TickStockPL

## Background

The Cache Reorganization (also called Cache Synchronization) job currently lives in TickStockAppV2 but architecturally belongs in TickStockPL as it's a data processing task. This job manages the `cache_entries` database table, organizing 4000+ stocks into logical groupings (market cap categories, top rankings, sectors, themes, IPOs, etc.) that the UI uses for dropdowns and filtering.

Since you've completed Phase 2 (Data Import) of the daily processing pipeline, this cache reorganization fits perfectly as **Phase 2.5** - it needs the updated OHLCV data from Phase 2 to calculate current market caps, but should run before Phase 3 (Indicators).

## What You're Migrating

**Source File**: `C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py` (881 lines)

This job:
- Reads from `symbols` and `ohlcv_daily` tables
- Writes to `cache_entries` table
- Organizes stocks into universes: mega_cap, large_cap, top_100, top_500, sectors, themes, IPOs, etc.
- Takes 5-30 minutes to run
- Publishes Redis events for UI notification

## 📁 Migration Package Contents

This folder contains everything you need:

### 1. **TickStockPL_cache_reorganization_migration.md**
High-level migration instructions with architecture overview, what the job does, and integration points.

### 2. **TickStockPL_implementation_guide.md**
Detailed code implementation guide with:
- Function-by-function migration instructions
- Database operations needed
- Redis event publishing
- Integration with your daily processing coordinator
- API endpoints to expose

### 3. **TickStockPL_source_file_locations.md**
Complete list of source files with full `C:\Users\McDude\TickStockAppV2\` paths for reference.

### 4. **TickStockPL_RETURN_THIS_COMPLETED.md** ⚠️ **CRITICAL**
Template that you MUST complete and return. This contains:
- API endpoints you create
- Redis event formats
- Authentication details
- Integration code for TickStockAppV2

**We cannot update our admin interface or remove the old code until you return this completed!**

### 5. **TickStockPL_migration_summary.md**
Executive summary if you need a quick overview.

### 6. **test_cache_entries_synchronizer.py**
Reference test file showing expected behavior.

## 🔄 Implementation Steps

1. **Copy** the main source file to your project:
   ```bash
   cp "C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py" src/jobs/daily_cache_sync_job.py
   ```

2. **Follow** the implementation guide to refactor for TickStockPL architecture

3. **Integrate** as Phase 2.5 in your daily processing pipeline

4. **Create** API endpoints for manual triggering from our admin interface

5. **Test** the implementation

6. **Complete** and return `TickStockPL_RETURN_THIS_COMPLETED.md` as `TickStockAppV2_integration_callback.md`

## 🚨 Important Notes

- This job MUST run AFTER Phase 2 (Data Import) completes - it needs updated OHLCV prices
- The job should publish Redis events so TickStockAppV2 can show progress
- We need your API endpoint details to update our admin interface
- After you confirm it works, we'll remove 1000+ lines of code from TickStockAppV2

## Why This Migration?

This is a clean architectural improvement - moving data processing from the consumer layer (TickStockAppV2) to the producer layer (TickStockPL) where it belongs. It will:
- Simplify TickStockAppV2 (removing 881 lines)
- Centralize all data processing in TickStockPL
- Allow better scheduling and monitoring as part of your daily pipeline
- Maintain the same functionality with better architecture

## Questions?

The documentation includes all database schemas, configuration values, and implementation details. The main file to study is:
```
C:\Users\McDude\TickStockAppV2\src\data\cache_entries_synchronizer.py
```

Remember to return the completed callback document so we can finalize the integration!