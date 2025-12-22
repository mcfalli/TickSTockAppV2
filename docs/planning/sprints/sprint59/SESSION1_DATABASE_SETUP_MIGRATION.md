# Session 1: Database Setup & Migration
## Sprint 59 - Relational Table Migration

**Estimated Time**: 1-2 hours
**Prerequisites**: Sprint 58 complete, PostgreSQL admin access
**Goal**: Create new tables and migrate all cache_entries data

---

## Overview

This session creates the new relational database structure and migrates all existing ETF-stock relationship data from `cache_entries` to the new `definition_groups` and `group_memberships` tables.

---

## Step 1: Create Table Creation SQL Script

**Action**: Create the SQL file for table creation

**File**: `scripts/sql/sprint59_create_tables.sql`

```sql
-- ============================================================
-- Sprint 59: Create definition_groups and group_memberships
-- ============================================================
-- Purpose: Migrate from JSONB cache_entries to relational structure
-- Created: 2025-12-20
-- ============================================================

-- Drop tables if exists (for clean re-run)
-- WARNING: Only use in development/test environments
-- DROP TABLE IF EXISTS public.group_memberships CASCADE;
-- DROP TABLE IF EXISTS public.definition_groups CASCADE;

-- Create the definition_groups table
CREATE TABLE IF NOT EXISTS public.definition_groups (
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

-- Create indexes for definition_groups
CREATE INDEX IF NOT EXISTS idx_definition_groups_type
    ON public.definition_groups(type);
CREATE INDEX IF NOT EXISTS idx_definition_groups_environment
    ON public.definition_groups(environment);
CREATE INDEX IF NOT EXISTS idx_definition_groups_name
    ON public.definition_groups(name);
CREATE INDEX IF NOT EXISTS idx_definition_groups_type_env
    ON public.definition_groups(type, environment);

-- Create the group_memberships table
CREATE TABLE IF NOT EXISTS public.group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);

-- Create indexes for group_memberships
CREATE INDEX IF NOT EXISTS idx_group_memberships_group_id
    ON public.group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_symbol
    ON public.group_memberships(symbol);
CREATE INDEX IF NOT EXISTS idx_group_memberships_symbol_group
    ON public.group_memberships(symbol, group_id);

-- Add comments for documentation
COMMENT ON TABLE public.definition_groups IS
    'Stores definitions for ETFs, themes, sectors, segments, and custom groupings';
COMMENT ON TABLE public.group_memberships IS
    'Many-to-many relationships between groups and stock symbols';

COMMENT ON COLUMN public.definition_groups.type IS
    'Group type: ETF, THEME, SECTOR, SEGMENT, or CUSTOM';
COMMENT ON COLUMN public.definition_groups.liquidity_filter IS
    'JSONB filters like {"min_volume": 1000000, "min_market_cap": 1000000000}';
COMMENT ON COLUMN public.group_memberships.weight IS
    'Optional weight/percentage (e.g., 0.0650 = 6.5% of ETF)';

-- Grant permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.definition_groups TO app_readwrite;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON public.group_memberships TO app_readwrite;
-- GRANT USAGE, SELECT ON SEQUENCE definition_groups_id_seq TO app_readwrite;
-- GRANT USAGE, SELECT ON SEQUENCE group_memberships_id_seq TO app_readwrite;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Tables created successfully: definition_groups, group_memberships';
END $$;
```

**Validation**:
```bash
# File should exist with ~90 lines
wc -l scripts/sql/sprint59_create_tables.sql
```

---

## Step 2: Backup Current Database

**Action**: Create a full database backup before any changes

```bash
# Set timestamp for backup file
BACKUP_FILE="backup_before_sprint59_$(date +%Y%m%d_%H%M%S).sql"

# Full database backup
pg_dump -h localhost -U postgres -d tickstock > "$BACKUP_FILE"

# Verify backup created
ls -lh $BACKUP_FILE

# Optional: Compress backup
gzip $BACKUP_FILE
```

**Expected Output**:
```
backup_before_sprint59_20251220_090000.sql (50-100 MB)
```

**Validation**:
```bash
# Check backup file is not empty
if [ -s "$BACKUP_FILE" ]; then
    echo "✅ Backup created successfully"
else
    echo "❌ Backup failed - STOP and investigate"
fi
```

---

## Step 3: Execute Table Creation

**Action**: Run the SQL script to create new tables

```bash
# Execute table creation script
psql -h localhost -U postgres -d tickstock -f scripts/sql/sprint59_create_tables.sql

# Alternative if using environment variables
# PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d tickstock -f scripts/sql/sprint59_create_tables.sql
```

**Expected Output**:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
...
NOTICE:  Tables created successfully: definition_groups, group_memberships
```

**Validation**:
```sql
-- Check tables exist
SELECT * FROM pg_tables
WHERE tablename IN ('definition_groups', 'group_memberships');

-- Check table structure
\d definition_groups
\d group_memberships
```

**Expected Results**:
- 2 tables found
- Correct columns and constraints
- Indexes created

---

## Step 4: Verify Tables Created

**Action**: Query database to confirm structure

```sql
-- Check definition_groups structure
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'definition_groups'
ORDER BY ordinal_position;

-- Check group_memberships structure
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'group_memberships'
ORDER BY ordinal_position;

-- Verify indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('definition_groups', 'group_memberships')
ORDER BY tablename, indexname;

-- Verify foreign key constraint
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'group_memberships';
```

**Expected Results**:
- ✅ definition_groups: 11 columns (id, name, type, description, metadata, liquidity_filter, environment, created_at, updated_at, last_update, CONSTRAINT unique_group)
- ✅ group_memberships: 7 columns (id, group_id, symbol, weight, metadata, added_at, updated_at)
- ✅ 7 indexes total (4 on definition_groups, 3 on group_memberships)
- ✅ Foreign key: group_memberships.group_id → definition_groups.id

---

## Step 5: Create Migration Script

**Action**: Create Python script to migrate cache_entries → new tables

**File**: `scripts/cache_maintenance/migrate_to_new_tables.py`

```python
"""
Data Migration Script: cache_entries → definition_groups + group_memberships

Migrates Sprint 58 data from JSONB-based cache_entries to relational structure.

Usage:
    python migrate_to_new_tables.py --dry-run   # Preview migration
    python migrate_to_new_tables.py             # Execute migration
    python migrate_to_new_tables.py --rollback  # Delete migrated data
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CacheEntriesMigration:
    """Migrate cache_entries to definition_groups + group_memberships"""

    def __init__(self, dry_run=False):
        """Initialize migration"""
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = self._get_connection()
        self.dry_run = dry_run
        self.environment = 'DEFAULT'

        # Migration stats
        self.stats = {
            'groups_created': 0,
            'memberships_created': 0,
            'etfs_migrated': 0,
            'themes_migrated': 0,
            'sectors_migrated': 0,
            'errors': []
        }

    def _get_connection(self):
        """Get database connection"""
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def migrate_etf_holdings(self):
        """Migrate etf_holdings → definition_groups (type='ETF')"""
        logger.info("Migrating ETF holdings...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'holdings' as holdings,
                value->>'total_holdings' as total_holdings,
                value->>'market_cap_threshold' as threshold,
                value->>'data_source' as source,
                value->>'last_updated' as last_updated
            FROM cache_entries
            WHERE type = 'etf_holdings'
            AND environment = %s
        """, (self.environment,))

        etfs = cursor.fetchall()
        logger.info(f"Found {len(etfs)} ETFs to migrate")

        for etf_key, etf_name, holdings_json, total_holdings, threshold, source, last_updated in etfs:
            try:
                # Parse holdings array from JSONB
                import json
                holdings = json.loads(holdings_json) if isinstance(holdings_json, str) else holdings_json

                if not holdings:
                    logger.warning(f"Skipping {etf_key}: no holdings")
                    continue

                # Create metadata JSON
                metadata = {
                    'total_holdings': int(total_holdings) if total_holdings else len(holdings),
                    'data_source': source,
                    'last_updated': last_updated
                }

                # Create liquidity filter JSON
                liquidity_filter = {
                    'market_cap_threshold': float(threshold) if threshold else None
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create ETF: {etf_key} with {len(holdings)} holdings")
                else:
                    # Insert into definition_groups
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, liquidity_filter, environment)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET metadata = EXCLUDED.metadata,
                            liquidity_filter = EXCLUDED.liquidity_filter,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        etf_key,
                        'ETF',
                        etf_name,
                        json.dumps(metadata),
                        json.dumps(liquidity_filter),
                        self.environment
                    ))

                    group_id = cursor.fetchone()[0]
                    self.stats['groups_created'] += 1

                    # Insert holdings into group_memberships
                    for symbol in holdings:
                        cursor.execute("""
                            INSERT INTO group_memberships (group_id, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (group_id, symbol) DO NOTHING
                        """, (group_id, symbol))
                        self.stats['memberships_created'] += 1

                    logger.info(f"✓ Migrated ETF: {etf_key} ({len(holdings)} holdings)")

                self.stats['etfs_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating ETF {etf_key}: {e}")
                self.stats['errors'].append(f"ETF {etf_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def migrate_theme_definitions(self):
        """Migrate theme_definition → definition_groups (type='THEME')"""
        logger.info("Migrating theme definitions...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'symbols' as symbols,
                value->>'description' as description,
                value->>'selection_criteria' as criteria,
                value->'related_themes' as related_themes
            FROM cache_entries
            WHERE type = 'theme_definition'
            AND environment = %s
        """, (self.environment,))

        themes = cursor.fetchall()
        logger.info(f"Found {len(themes)} themes to migrate")

        for theme_key, theme_name, symbols_json, description, criteria, related_themes in themes:
            try:
                import json
                symbols = json.loads(symbols_json) if isinstance(symbols_json, str) else symbols_json

                if not symbols:
                    logger.warning(f"Skipping {theme_key}: no symbols")
                    continue

                metadata = {
                    'selection_criteria': criteria,
                    'related_themes': related_themes
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create theme: {theme_key} with {len(symbols)} symbols")
                else:
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, environment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET description = EXCLUDED.description,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        theme_key,
                        'THEME',
                        description,
                        json.dumps(metadata),
                        self.environment
                    ))

                    group_id = cursor.fetchone()[0]
                    self.stats['groups_created'] += 1

                    for symbol in symbols:
                        cursor.execute("""
                            INSERT INTO group_memberships (group_id, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (group_id, symbol) DO NOTHING
                        """, (group_id, symbol))
                        self.stats['memberships_created'] += 1

                    logger.info(f"✓ Migrated theme: {theme_key} ({len(symbols)} symbols)")

                self.stats['themes_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating theme {theme_key}: {e}")
                self.stats['errors'].append(f"Theme {theme_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def migrate_sector_definitions(self):
        """Migrate sector_industry_map → definition_groups (type='SECTOR')"""
        logger.info("Migrating sector definitions...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'industries' as industries,
                value->'representative_stocks' as rep_stocks,
                value->>'description' as description
            FROM cache_entries
            WHERE type = 'sector_industry_map'
            AND environment = %s
        """, (self.environment,))

        sectors = cursor.fetchall()
        logger.info(f"Found {len(sectors)} sectors to migrate")

        for sector_key, sector_name, industries_json, rep_stocks_json, description in sectors:
            try:
                import json
                industries = json.loads(industries_json) if isinstance(industries_json, str) else industries_json
                rep_stocks = json.loads(rep_stocks_json) if isinstance(rep_stocks_json, str) else rep_stocks_json

                metadata = {
                    'industries': industries,
                    'representative_stocks': rep_stocks
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create sector: {sector_key}")
                else:
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, environment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET description = EXCLUDED.description,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        sector_key,
                        'SECTOR',
                        description,
                        json.dumps(metadata),
                        self.environment
                    ))

                    self.stats['groups_created'] += 1
                    logger.info(f"✓ Migrated sector: {sector_key}")

                self.stats['sectors_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating sector {sector_key}: {e}")
                self.stats['errors'].append(f"Sector {sector_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def print_summary(self):
        """Print migration summary"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"ETFs migrated:        {self.stats['etfs_migrated']}")
        logger.info(f"Themes migrated:      {self.stats['themes_migrated']}")
        logger.info(f"Sectors migrated:     {self.stats['sectors_migrated']}")
        logger.info(f"Groups created:       {self.stats['groups_created']}")
        logger.info(f"Memberships created:  {self.stats['memberships_created']}")
        logger.info(f"Errors:               {len(self.stats['errors'])}")

        if self.stats['errors']:
            logger.error("\nErrors encountered:")
            for error in self.stats['errors']:
                logger.error(f"  - {error}")

        logger.info("=" * 60)

    def validate_migration(self):
        """Validate migrated data"""
        logger.info("\nValidating migration...")

        cursor = self.conn.cursor()

        # Count groups by type
        cursor.execute("""
            SELECT type, COUNT(*)
            FROM definition_groups
            WHERE environment = %s
            GROUP BY type
        """, (self.environment,))

        logger.info("\nGroups by type:")
        for group_type, count in cursor.fetchall():
            logger.info(f"  {group_type}: {count}")

        # Count total memberships
        cursor.execute("""
            SELECT COUNT(*) FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.environment = %s
        """, (self.environment,))

        total_memberships = cursor.fetchone()[0]
        logger.info(f"\nTotal memberships: {total_memberships}")

        # Count unique symbols
        cursor.execute("""
            SELECT COUNT(DISTINCT gm.symbol) FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.environment = %s
        """, (self.environment,))

        unique_symbols = cursor.fetchone()[0]
        logger.info(f"Unique symbols: {unique_symbols}")

    def rollback(self):
        """Delete all migrated data"""
        logger.warning("Rolling back migration...")

        cursor = self.conn.cursor()

        if self.dry_run:
            logger.info("[DRY-RUN] Would delete all migrated data")
        else:
            # Delete all groups for this environment (cascade will delete memberships)
            cursor.execute("""
                DELETE FROM definition_groups
                WHERE environment = %s
            """, (self.environment,))

            deleted = cursor.rowcount
            self.conn.commit()
            logger.info(f"✓ Deleted {deleted} groups (and their memberships)")


def main():
    parser = argparse.ArgumentParser(description='Migrate cache_entries to new relational tables')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without changes')
    parser.add_argument('--rollback', action='store_true', help='Delete migrated data')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    args = parser.parse_args()

    migration = CacheEntriesMigration(dry_run=args.dry_run)

    if args.rollback:
        migration.rollback()
        return

    if args.validate_only:
        migration.validate_migration()
        return

    mode = "[DRY-RUN] " if args.dry_run else ""
    logger.info(f"{mode}Starting migration...")

    # Run migrations
    migration.migrate_etf_holdings()
    migration.migrate_theme_definitions()
    migration.migrate_sector_definitions()

    # Print summary
    migration.print_summary()

    # Validate if not dry-run
    if not args.dry_run:
        migration.validate_migration()

    logger.info("\n✅ Migration complete!")


if __name__ == '__main__':
    main()
```

**Validation**:
```bash
# Check script created
ls -lh scripts/cache_maintenance/migrate_to_new_tables.py

# Should be ~400-450 lines
wc -l scripts/cache_maintenance/migrate_to_new_tables.py
```

---

## Step 6: Test Migration with Dry-Run

**Action**: Run migration in dry-run mode to preview changes

```bash
cd C:\Users\McDude\TickStockAppV2

# Dry-run migration
python scripts/cache_maintenance/migrate_to_new_tables.py --dry-run
```

**Expected Output**:
```
[DRY-RUN] Starting migration...
Migrating ETF holdings...
Found 24 ETFs to migrate
[DRY-RUN] Would create ETF: SPY with 504 holdings
[DRY-RUN] Would create ETF: QQQ with 102 holdings
...
Migrating theme definitions...
Found 20 themes to migrate
[DRY-RUN] Would create theme: crypto_miners with 9 symbols
...
Migrating sector definitions...
Found 11 sectors to migrate
[DRY-RUN] Would create sector: information_technology
...

MIGRATION SUMMARY
ETFs migrated:        24
Themes migrated:      20
Sectors migrated:     11
Groups created:       0  (dry-run)
Memberships created:  0  (dry-run)
Errors:               0
```

**Validation**:
- ✅ Found expected counts (24 ETFs, 20 themes, 11 sectors)
- ✅ No errors
- ✅ Ready for actual migration

---

## Step 7: Run Full Migration

**Action**: Execute actual data migration

```bash
# Execute migration (no dry-run flag)
python scripts/cache_maintenance/migrate_to_new_tables.py
```

**Expected Output**:
```
Starting migration...
Migrating ETF holdings...
Found 24 ETFs to migrate
✓ Migrated ETF: SPY (504 holdings)
✓ Migrated ETF: QQQ (102 holdings)
✓ Migrated ETF: VTI (3513 holdings)
...
Migrating theme definitions...
Found 20 themes to migrate
✓ Migrated theme: crypto_miners (9 symbols)
...
Migrating sector definitions...
Found 11 sectors to migrate
✓ Migrated sector: information_technology
...

MIGRATION SUMMARY
ETFs migrated:        24
Themes migrated:      20
Sectors migrated:     11
Groups created:       55  (24 + 20 + 11)
Memberships created:  ~12,000+
Errors:               0

Validating migration...
Groups by type:
  ETF: 24
  THEME: 20
  SECTOR: 11

Total memberships: ~12,000
Unique symbols: ~3,700

✅ Migration complete!
```

**Validation**:
- ✅ All ETFs migrated
- ✅ All themes migrated
- ✅ All sectors migrated
- ✅ Zero errors
- ✅ Membership counts reasonable

---

## Step 8: Validate Migrated Data

**Action**: Run comprehensive validation queries

```sql
-- Check group counts by type
SELECT type, COUNT(*) as count
FROM definition_groups
WHERE environment = 'DEFAULT'
GROUP BY type;

-- Expected:
-- ETF: 24
-- THEME: 20
-- SECTOR: 11

-- Check total memberships
SELECT COUNT(*) as total_memberships
FROM group_memberships gm
JOIN definition_groups dg ON gm.group_id = dg.id
WHERE dg.environment = 'DEFAULT';

-- Expected: ~12,000+ (includes overlapping memberships)

-- Check unique symbols
SELECT COUNT(DISTINCT symbol) as unique_symbols
FROM group_memberships gm
JOIN definition_groups dg ON gm.group_id = dg.id
WHERE dg.environment = 'DEFAULT';

-- Expected: ~3,700

-- Test specific ETF query (SPY)
SELECT
    dg.name,
    dg.type,
    COUNT(gm.symbol) as holdings_count
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'SPY'
    AND dg.type = 'ETF'
    AND dg.environment = 'DEFAULT'
GROUP BY dg.name, dg.type;

-- Expected: SPY | ETF | 504

-- Test reverse lookup (AAPL memberships)
SELECT
    dg.name,
    dg.type
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE gm.symbol = 'AAPL'
    AND dg.environment = 'DEFAULT'
ORDER BY dg.type, dg.name;

-- Expected: Multiple ETFs containing AAPL

-- Check for orphan memberships (should be 0)
SELECT COUNT(*)
FROM group_memberships gm
WHERE NOT EXISTS (
    SELECT 1 FROM definition_groups dg
    WHERE dg.id = gm.group_id
);

-- Expected: 0

-- Check for groups with no memberships (sectors should have 0, ETFs/themes should have >0)
SELECT dg.name, dg.type, COUNT(gm.id) as membership_count
FROM definition_groups dg
LEFT JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.environment = 'DEFAULT'
GROUP BY dg.name, dg.type
HAVING COUNT(gm.id) = 0;

-- Expected: Only SECTOR types should appear (sectors don't have direct memberships)
```

**Validation Script**:
```bash
# Run validation using migration script
python scripts/cache_maintenance/migrate_to_new_tables.py --validate-only
```

---

## Success Criteria for Session 1

**Must Pass** ✅:
- [x] Tables created successfully (definition_groups, group_memberships)
- [x] Indexes created (7 total)
- [x] Foreign key constraint working
- [x] Database backup completed
- [x] Migration script created and tested
- [x] All 24 ETFs migrated
- [x] All 20 themes migrated
- [x] All 11 sectors migrated
- [x] ~3,700 unique symbols in memberships
- [x] Zero orphan memberships
- [x] Zero errors in migration

---

## Troubleshooting

### Issue: Table already exists
**Fix**:
```sql
-- Drop and recreate (development only!)
DROP TABLE IF EXISTS group_memberships CASCADE;
DROP TABLE IF EXISTS definition_groups CASCADE;
-- Then re-run creation script
```

### Issue: Migration shows 0 ETFs/themes/sectors found
**Fix**: Check environment variable
```python
# Verify environment in migration script
self.environment = 'DEFAULT'  # Should match cache_entries.environment
```

### Issue: Foreign key violation
**Fix**: Ensure definition_groups inserted before group_memberships
```python
# Correct order:
1. Insert into definition_groups (get group_id)
2. Insert into group_memberships (using group_id)
```

---

## Next Steps

Once Session 1 validation passes:
1. ✅ New tables created and populated
2. ✅ All data migrated successfully
3. → **Proceed to SESSION2_UPDATE_SCRIPTS.md**

---

**Session 1 Status**: □ Not Started | □ In Progress | □ Complete
**Completion Date**: _____________
**Validated By**: _____________
