# Sprint 57: Implementation Checklist
## Cache-Based Universe Loading & Organization Tooling

**Track your progress through implementation**

---

## Pre-Implementation

### Environment Preparation
- [ ] Review main guide: `README.md`
- [ ] Review implementation guide: `IMPLEMENTATION_GUIDE.md`
- [ ] Backup database: `pg_dump tickstock > backup_sprint57.sql`
- [ ] Create feature branch: `git checkout -b feature/sprint57-cache-based-loading`
- [ ] Python environment activated (both AppV2 and PL)
- [ ] All dependencies installed

### Discovery Phase
- [ ] Review `cache_entries` table structure and data
- [ ] Identify current CSV file dependencies in TickStockPL
- [ ] Document current cache organization flow
- [ ] List all affected files and routes

---

## Phase 1: Cache-Based Universe Loading (TickStockPL)

### File Creation
- [ ] Create `C:\Users\McDude\TickStockPL\src\database\cache_operations.py`
  - [ ] Implement `CacheOperations` class
  - [ ] Implement `get_universe_symbols()` method
  - [ ] Implement `list_available_universes()` method
  - [ ] Implement `validate_universe_exists()` method
  - [ ] Add error handling for all methods
  - [ ] Test database connection

### Data Load Handler Updates
- [ ] Open `C:\Users\McDude\TickStockPL\src\jobs\data_load_handler.py`
- [ ] Add import: `from src.database.cache_operations import CacheOperations`
- [ ] Add `self.cache_ops = CacheOperations()` to `__init__`
- [ ] Implement `_load_symbols_from_cache()` method
- [ ] Update `_execute_csv_universe_load()` method:
  - [ ] Add check for `universe_key` parameter
  - [ ] Add cache-based loading branch
  - [ ] Maintain backward compatibility with CSV files
  - [ ] Add logging for both modes
- [ ] Test syntax (no errors on import)

### Testing
- [ ] Unit test: `CacheOperations.get_universe_symbols()` returns correct symbols
- [ ] Unit test: Handles missing universe keys gracefully
- [ ] Unit test: Handles invalid JSONB format
- [ ] Integration test: Load small universe (3-5 symbols) from cache
- [ ] Integration test: Verify historical data loads correctly
- [ ] Performance test: Compare cache query vs CSV file read times

---

## Phase 2: Cache Organization Tooling (TickStockAppV2)

### Scripts Directory Setup
- [ ] Create `C:\Users\McDude\TickStockAppV2\scripts\cache_maintenance\` directory
- [ ] Create `.gitkeep` or README to ensure directory is tracked

### Main Organization Script
- [ ] Create `scripts/cache_maintenance/organize_universes.py`
- [ ] Implement `UniverseOrganizer` class
- [ ] Implement `organize_etf_universes()` method
  - [ ] Define ETF universe structures (core, sector, bond, etc.)
  - [ ] Implement upsert logic
  - [ ] Add preserve/replace modes
- [ ] Implement `organize_combo_universes()` method
  - [ ] Define combo universe structures
  - [ ] Implement upsert logic
- [ ] Add command-line argument parsing:
  - [ ] `--preserve` flag
  - [ ] `--dry-run` flag
  - [ ] `--verbose` flag
- [ ] Add confirmation prompt for destructive operations
- [ ] Implement summary statistics
- [ ] Test script execution: `python scripts/cache_maintenance/organize_universes.py --dry-run`

### Validation Script
- [ ] Create `scripts/cache_maintenance/validate_cache.py`
- [ ] Implement cache integrity checks:
  - [ ] Check for NULL values
  - [ ] Validate JSONB structure
  - [ ] Check symbol count consistency
  - [ ] Identify stale entries (old updated_at)
  - [ ] Check for duplicate keys
- [ ] Generate validation report
- [ ] Test validation: `python scripts/cache_maintenance/validate_cache.py`

### Maintenance Documentation
- [ ] Create `scripts/cache_maintenance/README.md`
- [ ] Document all available scripts
- [ ] Add usage examples
- [ ] Add scheduling guidance (cron jobs)
- [ ] Add troubleshooting section

---

## Phase 3: UI Updates (TickStockAppV2)

### HTML Template Updates
- [ ] Open `web/templates/admin/historical_data_dashboard.html`
- [ ] Find "Cache Organization" section (lines ~480-498)
- [ ] Comment out existing section with clear markers
- [ ] Add new informational section:
  - [ ] Header: "Cache Organization"
  - [ ] Description about script-based maintenance
  - [ ] Code examples for running scripts
  - [ ] Link to maintenance README
- [ ] Test HTML renders without errors

### Backend Route Updates (Optional)
- [ ] Open `src/api/rest/admin_historical_data.py`
- [ ] Find `/admin/historical-data/rebuild-cache` route
- [ ] Add deprecation comment
- [ ] Optionally: Return redirect to documentation
- [ ] Remove or comment out JavaScript function `rebuildCacheEntries()`

### JavaScript Updates
- [ ] Comment out `rebuildCacheEntries()` function if present
- [ ] Remove any event listeners for cache organization button
- [ ] Verify no broken JavaScript references

---

## Phase 4: Testing & Validation

### Unit Tests
- [ ] Test `CacheOperations.get_universe_symbols()`:
  - [ ] Valid universe returns symbols
  - [ ] Missing universe raises ValueError
  - [ ] Invalid JSONB format raises ValueError
  - [ ] Database connection error handled
- [ ] Test `_load_symbols_from_cache()`:
  - [ ] Returns correct symbol list
  - [ ] Logs appropriately
  - [ ] Error handling works

### Integration Tests
- [ ] **Cache-Based Load Test** (Small Universe):
  - [ ] Run organize script: `python scripts/cache_maintenance/organize_universes.py`
  - [ ] Open Historical Data admin page
  - [ ] Select "Cached Universe" → "Core ETFs"
  - [ ] Duration: 1 Day
  - [ ] Click "Load Universe Data"
  - [ ] Verify job submission
  - [ ] Monitor TickStockPL logs for "Loading from cache"
  - [ ] Verify 10 symbols loaded
  - [ ] Check database for OHLCV data
  - [ ] Expected: SUCCESS ✅

- [ ] **Cache-Based Load Test** (Medium Universe):
  - [ ] Select "Sector ETFs" (11 symbols)
  - [ ] Duration: 1 Week
  - [ ] Load and verify
  - [ ] Expected: All 11 symbols loaded ✅

- [ ] **CSV Backward Compatibility Test**:
  - [ ] Select "CSV File" mode
  - [ ] Choose "curated-etfs.csv"
  - [ ] Duration: 1 Day
  - [ ] Verify CSV file still works
  - [ ] Expected: SUCCESS ✅ (backward compatibility maintained)

### Script Tests
- [ ] **Organization Script**:
  - [ ] Run with `--dry-run`: No changes made
  - [ ] Run without `--preserve`: Replaces all universes
  - [ ] Run with `--preserve`: Appends new universes
  - [ ] Check summary statistics
  - [ ] Verify database entries created

- [ ] **Validation Script**:
  - [ ] Run validation
  - [ ] Review report
  - [ ] Intentionally corrupt one entry (manual SQL)
  - [ ] Re-run validation
  - [ ] Verify error detection

### Performance Tests
- [ ] Measure cache query time:
  - [ ] Expected: <10ms per query
  - [ ] Compare to CSV file read time
  - [ ] Document results

- [ ] Measure full universe load time:
  - [ ] Cache-based: Record time
  - [ ] CSV-based: Record time
  - [ ] Expected: Similar or faster for cache

### Manual Verification
- [ ] UI renders correctly (no broken layouts)
- [ ] Universe dropdown still works (Sprint 55 feature)
- [ ] Cache organization section shows script instructions
- [ ] No JavaScript console errors
- [ ] Logs show appropriate messages

---

## Phase 5: Documentation & Cleanup

### Code Documentation
- [ ] Add docstrings to all new methods
- [ ] Update inline comments
- [ ] Add type hints where missing
- [ ] Review and improve error messages

### Sprint Documentation
- [ ] Update CLAUDE.md with Sprint 57 status
- [ ] Update BACKLOG.md with any deferred items
- [ ] Create Sprint 57 completion summary
- [ ] Document any gotchas or lessons learned

### Database Documentation
- [ ] Document cache_entries usage patterns
- [ ] Add example queries to docs
- [ ] Update schema documentation if needed

### User Documentation
- [ ] Update admin user guide (if exists)
- [ ] Document cache maintenance procedures
- [ ] Create runbook for common operations

---

## Phase 6: Deployment

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code reviewed (self-review or peer review)
- [ ] Database backup completed
- [ ] Deployment plan documented
- [ ] Rollback plan documented and tested

### Deployment Steps

**TickStockAppV2:**
- [ ] Run organization script in production:
  ```bash
  python scripts/cache_maintenance/organize_universes.py --dry-run
  python scripts/cache_maintenance/organize_universes.py
  ```
- [ ] Verify cache entries created:
  ```sql
  SELECT type, name, key, jsonb_array_length(value) as count
  FROM cache_entries
  WHERE type IN ('etf_universe', 'stock_etf_combo')
  ORDER BY type, name;
  ```
- [ ] Deploy code changes:
  - [ ] Pull latest code
  - [ ] Restart Flask application
- [ ] Verify UI updates (cache organization section)

**TickStockPL:**
- [ ] Deploy code changes:
  - [ ] Pull latest code
  - [ ] Restart data loader service
- [ ] Monitor logs for startup errors
- [ ] Test cache-based loading:
  ```bash
  tail -f logs/tickstockpl.log | grep "cache"
  ```

### Post-Deployment Verification
- [ ] **Smoke Test** (5 minutes):
  - [ ] Load "Core ETFs" universe (1 day)
  - [ ] Verify job completes successfully
  - [ ] Check database for new data
  - [ ] Review logs for errors

- [ ] **Full Test** (30 minutes):
  - [ ] Load "Sector ETFs" universe (1 month)
  - [ ] Load "Growth & Value ETFs" universe (1 week)
  - [ ] Verify CSV backward compatibility
  - [ ] Check error rates in logs

- [ ] **Monitoring** (24 hours):
  - [ ] Monitor job success rates
  - [ ] Check cache query performance
  - [ ] Watch for database connection issues
  - [ ] Track any user-reported issues

---

## Success Criteria Verification

### Must Pass (MANDATORY)
- [ ] ✅ Universe loading works from cache (not CSV files)
- [ ] ✅ Cache queries return correct symbol lists
- [ ] ✅ Historical data loads complete successfully
- [ ] ✅ Cache organization script executes without errors
- [ ] ✅ Validation script detects test issues
- [ ] ✅ UI "Cache Organization" section updated/commented
- [ ] ✅ CSV backward compatibility maintained (optional feature)
- [ ] ✅ No regression in existing functionality
- [ ] ✅ Performance equal or better than CSV loading

### Performance Verification
- [ ] ✅ Cache query: <10ms
- [ ] ✅ Universe load time: Similar to Sprint 56
- [ ] ✅ Cache organization: <60s for full rebuild
- [ ] ✅ Cache validation: <30s

### Documentation Verification
- [ ] ✅ All code documented with docstrings
- [ ] ✅ Maintenance README created
- [ ] ✅ Sprint completion summary created
- [ ] ✅ CLAUDE.md updated

---

## Rollback Procedures

### If Critical Issues Arise

**Quick Rollback (Feature Flag)**:
- [ ] Add environment variable: `USE_CACHE_UNIVERSES=false`
- [ ] Restart TickStockPL
- [ ] Verify CSV mode active in logs
- [ ] Test CSV-based loading

**Full Rollback (Code Revert)**:
- [ ] Revert TickStockPL changes: `git revert HEAD`
- [ ] Revert TickStockAppV2 UI changes: `git revert HEAD`
- [ ] Restart both services
- [ ] Verify CSV file loading works
- [ ] Document issues for investigation

**Database Rollback**:
- [ ] Restore from backup if needed:
  ```bash
  psql tickstock < backup_sprint57.sql
  ```

---

## Issues Log

**Document any problems encountered:**

| Issue | Component | Resolution | Date |
|-------|-----------|------------|------|
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

---

## Final Checklist

### Code Quality
- [ ] All files committed and pushed
- [ ] No uncommitted changes
- [ ] Feature branch merged to main
- [ ] Sprint tagged: `sprint57-complete`
- [ ] Code follows project style guidelines

### Testing
- [ ] All automated tests passing
- [ ] Manual tests completed
- [ ] Performance tests completed
- [ ] Regression testing complete

### Documentation
- [ ] All docs updated
- [ ] README reflects changes
- [ ] Sprint completion notes added
- [ ] CLAUDE.md updated

### Deployment
- [ ] Production deployed
- [ ] Services running
- [ ] Logs clean
- [ ] Monitoring active
- [ ] Team notified (if applicable)

---

## Sprint Completion

**Sprint Status**: ☐ In Progress  ☐ Complete  ☐ Blocked

**Completion Date**: _________________

**Completed By**: _________________

**Final Notes**:
```
[Add any final observations, lessons learned, or follow-up items]






```

---

**Definition of Done**: All checkboxes marked, all tests passing, production deployed, cache-based loading functional, scripts operational, no regressions.

