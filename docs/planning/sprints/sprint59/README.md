# Sprint 59: Relational Table Migration
## ETF-Stock Relationships Database Redesign

**Type**: Database Architecture Refactoring
**Priority**: HIGH
**Estimated Effort**: 4-6 hours (across 3 sessions)
**Prerequisites**: Sprint 58 Complete

---

## Overview

Sprint 59 migrates the ETF-stock relationship system from JSONB-based `cache_entries` storage to a proper relational database structure using two new tables: `definition_groups` and `group_memberships`.

### Why This Migration?

**Current Issues with cache_entries**:
- ❌ Inefficient JSONB queries for large arrays
- ❌ No referential integrity (can't enforce FK constraints)
- ❌ Difficult to query many-to-many relationships
- ❌ No indexing on stock symbols within JSONB
- ❌ Complex aggregation queries

**Benefits of New Structure**:
- ✅ Proper relational schema with foreign keys
- ✅ Fast indexed queries on symbols
- ✅ Referential integrity enforcement
- ✅ Efficient JOIN operations
- ✅ Better query performance (10-50x faster for some queries)
- ✅ Standard SQL patterns (easier maintenance)

---

## New Database Schema

### Table 1: `definition_groups`

**Purpose**: Store ETF, theme, sector, and segment definitions

```sql
CREATE TABLE public.definition_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('ETF', 'THEME', 'SECTOR', 'SEGMENT', 'CUSTOM')),
    description TEXT,
    metadata JSONB,
    liquidity_filter JSONB,
    environment VARCHAR(10) NOT NULL CHECK (environment IN ('DEFAULT', 'TEST', 'UAT', 'PROD')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_group UNIQUE (name, type, environment)
);
```

### Table 2: `group_memberships`

**Purpose**: Many-to-many relationship between groups and stock symbols

```sql
CREATE TABLE public.group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);
```

### Key Relationships

```
definition_groups (1) ----< (many) group_memberships
     |                              |
     | - SPY (ETF)                  | - AAPL
     | - QQQ (ETF)                  | - MSFT
     | - crypto_miners (THEME)      | - NVDA
     | - information_technology     | - MARA
```

---

## Migration Data Mapping

### From cache_entries → To New Tables

| cache_entries Type | → | definition_groups Type | Example |
|-------------------|---|----------------------|---------|
| `etf_holdings` | → | `ETF` | SPY, QQQ, VTI |
| `theme_definition` | → | `THEME` | crypto_miners, ai_ml |
| `sector_industry_map` | → | `SECTOR` | information_technology |
| `stock_universe` | → | `CUSTOM` | market_leaders |
| `etf_universe` | → | `CUSTOM` | tracked_etfs |

**Stock Memberships** (from JSONB arrays):
- `value->'holdings'` → `group_memberships.symbol`
- `value->'symbols'` → `group_memberships.symbol`
- Array position → `group_memberships.weight` (optional)

---

## Sprint Sessions

### Session 1: Database Setup & Migration (1-2 hours)
**File**: `SESSION1_DATABASE_SETUP_MIGRATION.md`

- Create new tables in PostgreSQL
- Backup existing database
- Write migration script to transform cache_entries → new tables
- Validate migrated data

**Deliverables**:
- `scripts/sql/sprint59_create_tables.sql`
- `scripts/cache_maintenance/migrate_to_new_tables.py`
- Database backup
- Validation report

---

### Session 2: Update Scripts (2-3 hours)
**File**: `SESSION2_UPDATE_SCRIPTS.md`

- Update all cache_maintenance scripts to use new tables
- Modify load_etf_holdings.py
- Modify build_stock_metadata.py
- Modify organize_sectors_industries.py
- Modify organize_universe.py
- Update query_relationships.py
- Update validate_relationships.py

**Deliverables**:
- 6 updated Python scripts
- All scripts tested with dry-run mode

---

### Session 3: Testing & Documentation (1 hour)
**File**: `SESSION3_TESTING_DOCUMENTATION.md`

- Run comprehensive validation tests
- Execute integration tests
- Update documentation
- Create rollback plan
- Plan deprecation of old cache_entries

**Deliverables**:
- Test results report
- Updated documentation
- Rollback procedure
- Sprint completion summary

---

## Success Criteria

**Must Pass**:
- ✅ All cache_entries data migrated to new tables
- ✅ 24 ETFs in definition_groups (type='ETF')
- ✅ 20 themes in definition_groups (type='THEME')
- ✅ 11 sectors in definition_groups (type='SECTOR')
- ✅ ~3,700 unique symbols in group_memberships
- ✅ Zero orphan memberships (all group_id valid)
- ✅ All Sprint 58 functionality preserved
- ✅ Query performance same or better
- ✅ Integration tests pass

**Performance Targets**:
- ETF holdings query: <5ms (currently ~5ms)
- Stock memberships query: <5ms (currently ~5ms)
- Sector filter query: <20ms (currently <50ms)
- Validation script: <2s (currently ~1s)

---

## Rollback Strategy

**If Issues Arise**:
1. Keep old cache_entries data untouched during migration
2. Run both systems in parallel for validation period
3. Can revert scripts to use cache_entries if needed
4. Database restore from backup if catastrophic

**Deprecation Plan**:
- Week 1-2: Parallel operation (new tables + old cache_entries)
- Week 3: Validation period (new tables primary, old as backup)
- Week 4+: Archive old cache_entries data

---

## Risk Assessment

**Low Risk**:
- ✓ Data migration is one-way transform (no data loss)
- ✓ Old cache_entries preserved during migration
- ✓ Can run both systems in parallel
- ✓ Full database backup before changes

**Medium Risk**:
- ⚠️ Scripts need updates (6 Python files)
- ⚠️ Query patterns change (SQL rewrites)

**Mitigation**:
- Comprehensive dry-run testing
- Session-based execution (can pause between sessions)
- Validation checks at each step

---

## File Structure

```
docs/planning/sprints/sprint59/
├── README.md                              (This file - Overview)
├── SESSION1_DATABASE_SETUP_MIGRATION.md   (Steps 1-8)
├── SESSION2_UPDATE_SCRIPTS.md             (Steps 9-15)
└── SESSION3_TESTING_DOCUMENTATION.md      (Steps 16-22)

scripts/sql/
└── sprint59_create_tables.sql             (NEW - Table creation)

scripts/cache_maintenance/
└── migrate_to_new_tables.py               (NEW - Data migration)
```

---

## Quick Start

1. **Read**: Start with SESSION1_DATABASE_SETUP_MIGRATION.md
2. **Execute**: Follow numbered steps in sequence
3. **Validate**: Check success criteria after each session
4. **Continue**: Move to next session only after validation passes

---

## Questions & Decisions

**Before Starting Session 1**:
- [ ] Database backup location confirmed?
- [ ] PostgreSQL admin credentials available?
- [ ] Acceptable downtime window (if any)?
- [ ] Keep both systems parallel? (Recommended: YES)

**Before Starting Session 2**:
- [ ] Session 1 validation passed?
- [ ] All data migrated correctly?
- [ ] New tables indexed appropriately?

**Before Starting Session 3**:
- [ ] Session 2 scripts all updated?
- [ ] Dry-run tests passed?
- [ ] Ready to run integration tests?

---

**Status**: Ready for Session 1
**Created**: 2025-12-20
**Last Updated**: 2025-12-20
