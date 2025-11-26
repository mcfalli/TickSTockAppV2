# Sprint 55: Historical Data Page ETF Integration & Cache Optimization

**Sprint Goal**: Enhance the Historical Data admin page with new ETF universe selections and optimize cache_entries data integrity.

**Status**: Planning
**Start Date**: TBD
**Target Completion**: TBD
**Priority**: Medium

---

## Overview

This sprint focuses on two key improvements to the Historical Data management system:

1. **ETF Universe Integration**: Add newly created ETF groups (Core, Sector, Equal Weight) to the historical data page symbol selection interface
2. **Cache Entries Audit**: Review and update cache_entries table to ensure data consistency and accuracy

---

## Task 1: Add ETF Universe Selection to Historical Data Page

### Current State

The Historical Data admin page (`/admin/historical-data`) currently allows loading historical data for symbols, but does not provide easy access to the newly created ETF universe groups:

**Existing Cache Entries (Recently Added)**:
- `etf_core` (3 symbols): SPY, QQQ, IWM
- `etf_sector` (21 symbols): XRT, KRE, GDX, XHB, XBI, XTL, IBB, LABU, KBE, XLB, XLV, SMH, XLF, XLK, XLE, XLI, XLP, XME, XOP, XLY, XLU
- `etf_equal_weight_sectors` (12 symbols): RSPT, RSPG, RSPR, RSP, RSPS, RSPU, RSPC, RSPD, RSPH, RSPF, RSPM, RSPN
- `stock_etf_group` (36 symbols): Combined list from all 3 categories above

**Current Page**: `src/api/rest/admin_historical_data.py`
**Current Template**: `web/templates/admin/historical_data.html` (or themed variant)

### Desired State

Add a dropdown/selection interface that allows users to:
1. Select from predefined ETF universe groups
2. Load all symbols in the selected group with one action
3. See preview of symbols that will be loaded before triggering
4. Track loading progress for bulk ETF universe loads

### Functional Requirements

**UI Components Needed**:
- Dropdown selector for ETF universe groups (`etf_core`, `etf_sector`, `etf_equal_weight_sectors`, `stock_etf_group`)
- "Load Universe" button that triggers historical data load for all symbols in selected group
- Symbol count preview (e.g., "This will load 21 symbols")
- Progress indicator for bulk loading operations
- Success/failure feedback for each symbol in the batch

**Backend Requirements**:
- Endpoint to fetch available universe groups from cache_entries
- Endpoint to expand universe key into full symbol list
- Batch loading support (iterate through symbols, trigger load for each)
- Job tracking for bulk universe loads
- Error handling for individual symbol failures within batch

**Data Flow**:
```
1. User selects "etf_sector" from dropdown
2. Frontend fetches symbol list from cache_entries (21 symbols)
3. User clicks "Load Universe"
4. Backend creates batch job for 21 symbols
5. Progress updates show N/21 completed
6. Final summary: "Loaded 20/21 symbols (1 failed: XBI)"
```

### Technical Specifications

**API Endpoints to Add/Update**:
```python
GET /admin/historical-data/universes
# Returns: [
#   {"key": "etf_core", "name": "Core ETFs", "count": 3},
#   {"key": "etf_sector", "name": "Sector ETFs", "count": 21},
#   ...
# ]

GET /admin/historical-data/universe/<universe_key>/symbols
# Returns: {"symbols": ["SPY", "QQQ", "IWM"], "count": 3}

POST /admin/historical-data/trigger-universe-load
# Body: {"universe_key": "etf_sector", "start_date": "2024-01-01", "end_date": "2024-12-31"}
# Returns: {"job_id": "uuid", "symbol_count": 21, "status": "queued"}
```

**Frontend Changes**:
- Add universe selector component to historical_data.html
- Add batch loading UI with progress tracking
- Update existing single-symbol loader to coexist with universe loader

**Database Queries**:
```sql
-- Fetch available universes
SELECT type, name, key, jsonb_array_length(value) as count
FROM cache_entries
WHERE type IN ('etf_universe', 'stock_etf_combo')
ORDER BY name;

-- Expand universe to symbols
SELECT value as symbols
FROM cache_entries
WHERE key = 'etf_sector';
```

### Acceptance Criteria

- [ ] User can view list of available ETF universes in dropdown
- [ ] User can see symbol count for each universe before loading
- [ ] User can trigger bulk load for entire universe with one click
- [ ] Progress indicator shows N/Total symbols loaded
- [ ] Failed symbol loads are reported individually
- [ ] Existing single-symbol load functionality remains unchanged
- [ ] Universe loads are tracked in job history

### Test Cases

1. **Happy Path**: Load etf_core (3 symbols), all succeed
2. **Partial Failure**: Load etf_sector (21 symbols), 1 fails due to missing data
3. **Empty Universe**: Attempt to load universe with 0 symbols (error handling)
4. **Concurrent Loads**: Load two different universes simultaneously
5. **Cancel Universe Load**: Cancel batch job mid-progress

---

## Task 2: Review and Update Cache Entries

### Current State

The `cache_entries` table contains various universe definitions, but may have:
- Duplicate entries with different keys
- Outdated symbol lists
- Inconsistent naming conventions
- Missing metadata fields
- Incorrect categorizations

**Current Schema**:
```sql
cache_entries (
  id SERIAL PRIMARY KEY,
  type VARCHAR NOT NULL,              -- 'etf_universe', 'stock_universe', etc.
  name VARCHAR NOT NULL,              -- Display name
  key VARCHAR NOT NULL,               -- Unique key for lookups
  value JSONB NOT NULL,               -- Symbol array or detailed object
  environment VARCHAR NOT NULL,       -- 'DEFAULT', 'PROD', etc.
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  universe_category VARCHAR,          -- Optional categorization
  liquidity_filter JSONB,             -- Optional filter criteria
  universe_metadata JSONB,            -- Optional metadata
  last_universe_update TIMESTAMP,
  UNIQUE(type, name, key, environment)
)
```

### Desired State

A clean, well-organized cache_entries table with:
- No duplicate or redundant entries
- Consistent naming conventions (snake_case keys, Title Case names)
- Current and accurate symbol lists
- Proper categorization using universe_category
- Documented metadata for each universe
- Regular update tracking

### Audit Areas

**1. Identify Duplicates**
```sql
-- Find potential duplicates by similar names
SELECT type, name, key, COUNT(*)
FROM cache_entries
GROUP BY type, name, key
HAVING COUNT(*) > 1;

-- Find similar keys with different symbols
SELECT a.key as key1, b.key as key2, a.value, b.value
FROM cache_entries a
JOIN cache_entries b ON a.type = b.type AND a.key < b.key
WHERE a.value::text = b.value::text;
```

**2. Check Symbol Validity**
```sql
-- Verify symbols exist in symbols table
SELECT
  ce.key,
  jsonb_array_elements_text(ce.value) as symbol,
  s.symbol as exists_in_symbols
FROM cache_entries ce
LEFT JOIN symbols s ON s.symbol = jsonb_array_elements_text(ce.value)
WHERE ce.type = 'etf_universe'
AND s.symbol IS NULL;
```

**3. Review Naming Consistency**
- Keys should follow pattern: `{type}_{category}` (e.g., `etf_core`, `stock_tech_leaders`)
- Names should be Title Case (e.g., "Core ETFs", "Tech Leaders")
- Types should be standardized (`etf_universe`, `stock_universe`, `stock_etf_combo`)

**4. Check for Outdated Data**
```sql
-- Find entries not updated in 6+ months
SELECT key, name, created_at, updated_at, last_universe_update
FROM cache_entries
WHERE last_universe_update < NOW() - INTERVAL '6 months'
OR last_universe_update IS NULL;
```

**5. Validate Metadata**
- Ensure critical universes have universe_category set
- Check liquidity_filter is valid JSONB where present
- Verify universe_metadata contains useful information

### Cleanup Actions

**Standardize Keys**:
```sql
-- Example: Rename inconsistent keys
UPDATE cache_entries
SET key = 'etf_broad_market'
WHERE key = 'broad_market_etfs'
AND type = 'etf_universe';
```

**Remove Duplicates**:
```sql
-- Keep most recently updated, delete others
DELETE FROM cache_entries
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
      PARTITION BY type, value::text
      ORDER BY updated_at DESC NULLS LAST
    ) as rn
    FROM cache_entries
  ) t WHERE rn > 1
);
```

**Add Missing Metadata**:
```sql
-- Add categories to ETF universes
UPDATE cache_entries
SET universe_category = 'broad_market'
WHERE key = 'etf_broad_market';

UPDATE cache_entries
SET universe_category = 'sector'
WHERE key IN ('etf_sector', 'etf_equal_weight_sectors');
```

**Update Symbol Lists**:
- Compare against current market listings
- Remove delisted symbols
- Add new relevant symbols
- Document changes in universe_metadata

### Acceptance Criteria

- [ ] All cache_entries follow consistent naming convention
- [ ] No duplicate universe definitions exist
- [ ] All symbols in universes exist in symbols table (or documented as expected missing)
- [ ] Critical universes have universe_category populated
- [ ] last_universe_update is current for actively used universes
- [ ] Documentation created for cache_entries structure and maintenance

### Deliverables

1. **Audit Report**: `docs/database/cache_entries_audit_report.md`
   - List of duplicates found and removed
   - Invalid symbols identified and actions taken
   - Naming inconsistencies corrected
   - Metadata gaps filled

2. **Cleanup SQL Scripts**: `scripts/sql/cache_entries_cleanup.sql`
   - Standardization queries
   - Duplicate removal
   - Metadata updates

3. **Maintenance Procedures**: `docs/database/cache_entries_maintenance.md`
   - How to add new universes
   - How to update existing universes
   - Validation checklist
   - Regular maintenance schedule

---

## Dependencies

**Task 1 Dependencies**:
- Task 2 should be completed first to ensure clean data
- Requires frontend framework knowledge (Jinja2, JavaScript)
- Requires understanding of existing historical data loading mechanism

**Task 2 Dependencies**:
- None (can be started immediately)
- Requires database write access
- May need coordination if universes are actively used

---

## Risk Assessment

**Task 1 Risks**:
- **Medium**: Bulk loading may overwhelm API rate limits → Mitigation: Add throttling
- **Low**: UI complexity for progress tracking → Mitigation: Use existing job tracking patterns

**Task 2 Risks**:
- **Medium**: Deleting duplicates may break existing references → Mitigation: Audit usage before deletion
- **Low**: Symbol validation may reveal missing symbols → Mitigation: Document and decide on case-by-case basis

---

## Success Metrics

**Task 1**:
- Users can load entire ETF universes in <5 clicks
- Bulk universe loads complete successfully >95% of the time
- Individual symbol failures within batch are clearly reported

**Task 2**:
- Zero duplicate entries in cache_entries
- 100% of symbols in universes exist in symbols table (or are documented exceptions)
- All actively used universes have complete metadata

---

## Related Documentation

- [Cache Entries Schema](../../database/database-architecture.md#cache_entries)
- [Historical Data API](../../api/admin-endpoints.md#historical-data)
- [WebSocket Integration](../../architecture/websockets-integration.md)
- [Sprint 54 Complete](../sprint54/SPRINT54_COMPLETE.md) - Standalone architecture

---

## Notes

- The 4 new ETF universes were created on November 25, 2025
- Current config uses: `SYMBOL_UNIVERSE_KEY=stock_etf_combo:stock_etf_group`
- Historical data page is at `/admin/historical-data`
- Existing route handler: `src/api/rest/admin_historical_data.py`
