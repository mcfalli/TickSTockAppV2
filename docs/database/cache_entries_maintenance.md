# Cache Entries Maintenance Procedures

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Maintained By**: TickStock Development Team
**Purpose**: Standard procedures for adding, updating, and maintaining cache_entries

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Model Reference](#2-data-model-reference)
3. [Adding New Universe Entries](#3-adding-new-universe-entries)
4. [Updating Existing Entries](#4-updating-existing-entries)
5. [Naming Conventions](#5-naming-conventions)
6. [Validation Procedures](#6-validation-procedures)
7. [Common Operations](#7-common-operations)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Overview

The `cache_entries` table stores application settings, universe definitions, and cached data for TickStockAppV2. Proper maintenance ensures:
- ✅ Consistent naming conventions
- ✅ Complete metadata tracking
- ✅ Data integrity across universe definitions
- ✅ Reliable ETF universe integration

**Key Principles**:
1. **Always set updated_at**: Every INSERT and UPDATE must include `updated_at = NOW()`
2. **Follow naming conventions**: Use Title Case for names
3. **Validate before commit**: Run validation queries before final INSERT/UPDATE
4. **Document changes**: Update this guide when adding new entry types

---

## 2. Data Model Reference

### Schema
```sql
CREATE TABLE cache_entries (
    id SERIAL PRIMARY KEY,
    type VARCHAR(100) NOT NULL,          -- Entry category (e.g., 'etf_universe')
    name VARCHAR(255) NOT NULL,          -- Display name (Title Case)
    key VARCHAR(255) NOT NULL,           -- Unique identifier within type
    value JSONB,                         -- Data payload (array or object)
    environment VARCHAR(50),             -- Environment scope (optional)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,                -- MUST be set on INSERT/UPDATE
    UNIQUE(type, key, environment)       -- Composite uniqueness
);
```

### Entry Types
| Type | Description | Value Format | Example Key |
|------|-------------|--------------|-------------|
| `etf_universe` | ETF symbol groups | Array or Object with symbols | `etf_core`, `etf_sector` |
| `stock_universe` | Stock symbol groups | Array or Object with symbols | `sp_500`, `nasdaq_100` |
| `stock_etf_combo` | Mixed universe | Array or Object with symbols | `stock_etf_group` |
| `setting` | Application config | Varies | `theme_mode`, `api_key` |
| `cache` | Temporary data | Varies | `last_sync_time` |

### Value Formats
```json
// Format 1: Simple array (preferred for small lists)
["AAPL", "NVDA", "TSLA"]

// Format 2: Object with metadata (preferred for large lists)
{
  "symbols": ["AAPL", "NVDA", "TSLA", ...],
  "count": 100,
  "last_updated": "2025-11-26T00:00:00Z"
}
```

---

## 3. Adding New Universe Entries

### Standard Procedure

**Step 1: Prepare Symbol List**
```python
# Example: Creating a new ETF universe
symbols = ["SPY", "QQQ", "IWM"]  # Your symbol list
universe_key = "etf_core"
universe_name = "Core ETFs"  # MUST be Title Case
```

**Step 2: INSERT with Complete Metadata**
```sql
-- Template for new universe entry
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
VALUES (
    'etf_universe',                              -- Type
    'Core ETFs',                                 -- Name (Title Case!)
    'etf_core',                                  -- Key (snake_case)
    '["SPY", "QQQ", "IWM"]'::jsonb,             -- Value (JSONB array)
    'production',                                -- Environment (optional)
    NOW(),                                       -- created_at
    NOW()                                        -- updated_at (REQUIRED!)
);
```

**Step 3: Verify Insertion**
```sql
SELECT * FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_core';
```

**Expected Output**:
- `id`: Auto-generated
- `updated_at`: Same as `created_at` (not NULL)
- `value`: Valid JSONB array

---

## 4. Updating Existing Entries

### Update Symbol List
```sql
-- Update universe symbols
UPDATE cache_entries
SET
    value = '["SPY", "QQQ", "IWM", "AGG"]'::jsonb,  -- New symbol list
    updated_at = NOW()                               -- CRITICAL: Update timestamp
WHERE
    type = 'etf_universe'
    AND key = 'etf_core';
```

### Update Name (Rare)
```sql
-- Rename universe display name
UPDATE cache_entries
SET
    name = 'Core Market ETFs',  -- New Title Case name
    updated_at = NOW()
WHERE
    type = 'etf_universe'
    AND key = 'etf_core';
```

### Bulk Update updated_at (Cleanup)
```sql
-- Fix missing updated_at timestamps
UPDATE cache_entries
SET updated_at = created_at
WHERE updated_at IS NULL;
```

---

## 5. Naming Conventions

### Rules
1. **Name Field**: Always Title Case
   - ✅ Correct: `"Core ETFs"`, `"S&P 500"`, `"Technology Sector"`
   - ❌ Wrong: `"core etfs"`, `"s&p 500"`, `"TECHNOLOGY SECTOR"`

2. **Key Field**: Always snake_case
   - ✅ Correct: `etf_core`, `sp_500`, `tech_sector`
   - ❌ Wrong: `ETF_CORE`, `S&P_500`, `techSector`

3. **Type Field**: Descriptive, snake_case
   - ✅ Correct: `etf_universe`, `stock_universe`, `stock_etf_combo`
   - ❌ Wrong: `ETFUniverse`, `stockUniverse`

### Validation Query
```sql
-- Check for naming convention violations
SELECT
    id,
    type,
    name,
    key,
    CASE
        WHEN name !~ '^[A-Z]' THEN 'Name not Title Case'
        WHEN key !~ '^[a-z_0-9]+$' THEN 'Key not snake_case'
        ELSE 'OK'
    END as validation_status
FROM cache_entries
WHERE name !~ '^[A-Z]' OR key !~ '^[a-z_0-9]+$';
```

---

## 6. Validation Procedures

### Pre-INSERT Checklist
Before adding a new entry, verify:
- [ ] `name` is Title Case (first letter of each word capitalized)
- [ ] `key` is snake_case (lowercase with underscores)
- [ ] `value` is valid JSONB (test with `'<your_json>'::jsonb`)
- [ ] `created_at` will be set (use NOW() or DEFAULT)
- [ ] `updated_at` will be set (use NOW())
- [ ] `type` and `key` combination is unique (or will replace existing)

### Post-INSERT Validation
```sql
-- Validate new entry was inserted correctly
SELECT
    id,
    type,
    name,
    key,
    jsonb_typeof(value) as value_type,
    CASE
        WHEN jsonb_typeof(value) = 'array' THEN jsonb_array_length(value)
        WHEN jsonb_typeof(value) = 'object' AND value ? 'symbols' THEN jsonb_array_length(value->'symbols')
        ELSE 0
    END as symbol_count,
    created_at,
    updated_at,
    CASE
        WHEN updated_at IS NULL THEN 'MISSING updated_at'
        WHEN name !~ '^[A-Z]' THEN 'Name not Title Case'
        ELSE 'OK'
    END as status
FROM cache_entries
WHERE id = <newly_inserted_id>;
```

### Comprehensive Table Health Check
```sql
-- Run periodically to ensure data quality
SELECT
    'Cache Entries Health Check' as report,
    COUNT(*) as total_entries,
    COUNT(*) FILTER (WHERE updated_at IS NULL) as missing_updated_at,
    COUNT(*) FILTER (WHERE name !~ '^[A-Z]') as non_titlecase_names,
    COUNT(*) FILTER (WHERE key !~ '^[a-z_0-9]+$') as invalid_keys,
    COUNT(DISTINCT type) as unique_types
FROM cache_entries;
```

**Expected Healthy State**:
- `missing_updated_at`: 0
- `non_titlecase_names`: 0
- `invalid_keys`: 0

---

## 7. Common Operations

### 7.1 Add New ETF Universe

**Scenario**: Add a new sector ETF universe (e.g., "Financial Sector ETFs")

```sql
-- Step 1: Verify key doesn't exist
SELECT * FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_financial';

-- Step 2: Insert new universe
INSERT INTO cache_entries (type, name, key, value, created_at, updated_at)
VALUES (
    'etf_universe',
    'Financial Sector ETFs',  -- Title Case
    'etf_financial',           -- snake_case
    '["XLF", "VFH", "FNCL", "IYF", "KBE", "KRE"]'::jsonb,
    NOW(),
    NOW()
);

-- Step 3: Verify
SELECT
    id, name, key,
    jsonb_array_length(value) as symbol_count,
    updated_at
FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_financial';
```

### 7.2 Update Universe Symbol List

**Scenario**: Add 2 new symbols to existing universe

```sql
-- Step 1: View current symbols
SELECT value FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_financial';

-- Step 2: Update with new symbols
UPDATE cache_entries
SET
    value = '["XLF", "VFH", "FNCL", "IYF", "KBE", "KRE", "KBWB", "IAT"]'::jsonb,
    updated_at = NOW()
WHERE type = 'etf_universe' AND key = 'etf_financial';

-- Step 3: Verify update
SELECT
    name,
    jsonb_array_length(value) as new_symbol_count,
    updated_at
FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_financial';
```

### 7.3 Delete Universe (Rare)

**Scenario**: Remove obsolete universe

```sql
-- Step 1: Verify entry exists and is correct one to delete
SELECT * FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_obsolete';

-- Step 2: Delete (CAREFUL - cannot undo!)
DELETE FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_obsolete';

-- Step 3: Verify deletion
SELECT COUNT(*) FROM cache_entries
WHERE type = 'etf_universe' AND key = 'etf_obsolete';
-- Expected: 0
```

### 7.4 Rename Universe Display Name

**Scenario**: Update "Core ETFs" to "Core Market ETFs"

```sql
UPDATE cache_entries
SET
    name = 'Core Market ETFs',  -- New Title Case name
    updated_at = NOW()
WHERE type = 'etf_universe' AND key = 'etf_core';
```

---

## 8. Troubleshooting

### Issue: "Duplicate key value violates unique constraint"

**Error Message**:
```
ERROR:  duplicate key value violates unique constraint "cache_entries_type_key_environment_key"
DETAIL:  Key (type, key, environment)=(etf_universe, etf_core, production) already exists.
```

**Cause**: Trying to INSERT an entry with same (type, key, environment).

**Solution**: Use UPDATE instead of INSERT, or use UPSERT:
```sql
-- UPSERT pattern (INSERT or UPDATE)
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
VALUES ('etf_universe', 'Core ETFs', 'etf_core', '["SPY"]'::jsonb, 'production', NOW(), NOW())
ON CONFLICT (type, key, environment)
DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();
```

### Issue: "Invalid JSON syntax"

**Error Message**:
```
ERROR:  invalid input syntax for type json
DETAIL:  Token "SPY" is invalid.
```

**Cause**: Missing quotes around strings or invalid JSON structure.

**Solution**: Ensure valid JSONB syntax:
```sql
-- ❌ Wrong
'[SPY, QQQ]'::jsonb

-- ✅ Correct
'["SPY", "QQQ"]'::jsonb
```

### Issue: "updated_at is NULL after INSERT"

**Cause**: Forgot to include `updated_at = NOW()` in INSERT.

**Solution**: Always include updated_at:
```sql
INSERT INTO cache_entries (type, name, key, value, created_at, updated_at)
VALUES (..., NOW(), NOW());  -- Both timestamps set
```

**Cleanup**:
```sql
UPDATE cache_entries
SET updated_at = created_at
WHERE updated_at IS NULL;
```

### Issue: "CacheControl not reflecting new universe"

**Cause**: CacheControl loads cache_entries once at application startup.

**Solution**: Restart Flask application to reload cache:
```bash
# Restart TickStockAppV2
# CacheControl will reload cache_entries from database on startup
```

**Alternative** (if refresh API exists):
```python
from src.infrastructure.cache.cache_control import CacheControl
cache_control = CacheControl()
cache_control.load_settings_from_db()  # Refresh cache
```

---

## Appendix A: Quick Reference

### Common Queries

```sql
-- List all ETF universes
SELECT id, name, key,
       jsonb_array_length(value) as symbol_count,
       updated_at
FROM cache_entries
WHERE type = 'etf_universe'
ORDER BY name;

-- List all stock universes
SELECT id, name, key,
       jsonb_array_length(value) as symbol_count,
       updated_at
FROM cache_entries
WHERE type = 'stock_universe'
ORDER BY name;

-- Find entries by symbol
SELECT type, name, key
FROM cache_entries
WHERE value @> '["AAPL"]'::jsonb;

-- Count entries by type
SELECT type, COUNT(*) as count
FROM cache_entries
GROUP BY type
ORDER BY count DESC;
```

### SQL Templates

**New ETF Universe**:
```sql
INSERT INTO cache_entries (type, name, key, value, created_at, updated_at)
VALUES ('etf_universe', '<Title Case Name>', '<snake_case_key>', '<JSONB_array>'::jsonb, NOW(), NOW());
```

**Update Universe Symbols**:
```sql
UPDATE cache_entries
SET value = '<new_JSONB_array>'::jsonb, updated_at = NOW()
WHERE type = 'etf_universe' AND key = '<key>';
```

**Fix Missing updated_at**:
```sql
UPDATE cache_entries SET updated_at = created_at WHERE updated_at IS NULL;
```

---

## Appendix B: Integration with Application Code

### Python Example: Adding Universe via CacheControl

```python
from src.infrastructure.cache.cache_control import CacheControl
from src.infrastructure.database.models.base import CacheEntry
from sqlalchemy.orm import Session

def add_etf_universe(session: Session, key: str, name: str, symbols: list):
    """
    Add new ETF universe to cache_entries.

    Args:
        session: SQLAlchemy session
        key: Universe key (snake_case)
        name: Display name (Title Case)
        symbols: List of ticker symbols
    """
    from datetime import datetime

    # Validate inputs
    if not name[0].isupper():
        raise ValueError(f"Name must be Title Case: {name}")

    if not key.islower() or ' ' in key:
        raise ValueError(f"Key must be snake_case: {key}")

    # Create entry
    entry = CacheEntry(
        type='etf_universe',
        name=name,
        key=key,
        value=symbols,  # SQLAlchemy handles JSONB conversion
        created_at=datetime.now(),
        updated_at=datetime.now()  # CRITICAL
    )

    session.add(entry)
    session.commit()

    # Reload CacheControl (if refresh method exists)
    # cache_control = CacheControl()
    # cache_control.load_settings_from_db()

    return entry
```

---

**Document Maintained By**: TickStock Development Team
**Last Reviewed**: 2025-11-26
**Next Review**: After Sprint 56 or when adding new entry types

**Related Documents**:
- `docs/database/cache_entries_audit_report_sprint55.md` - Audit findings
- `scripts/sql/cache_entries_cleanup_sprint55.sql` - Cleanup script
- `src/infrastructure/cache/cache_control.py` - CacheControl implementation
