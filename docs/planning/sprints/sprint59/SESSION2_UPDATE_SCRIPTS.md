# Session 2: Update Scripts
## Sprint 59 - Relational Table Migration

**Estimated Time**: 2-3 hours
**Prerequisites**: Session 1 complete, new tables populated
**Goal**: Update all cache_maintenance scripts to use new relational tables

---

## Overview

This session modifies all 6 cache_maintenance scripts to use the new `definition_groups` and `group_memberships` tables instead of `cache_entries`. Each script will be updated, tested with dry-run, and validated.

---

## Step 9: Update load_etf_holdings.py

**Action**: Modify script to insert into new tables

**File**: `scripts/cache_maintenance/load_etf_holdings.py`

**Changes Required**:

1. Update the `_insert_to_database()` method (around line 380):

```python
def _insert_to_database(self, etf_symbol: str, etf_data: dict) -> bool:
    """
    Insert ETF holdings into definition_groups and group_memberships

    Args:
        etf_symbol: ETF ticker symbol
        etf_data: ETF data dict with holdings, metadata, etc.

    Returns:
        True if successful
    """
    try:
        cursor = self.conn.cursor()

        # Prepare metadata
        metadata = {
            'total_holdings': len(etf_data['holdings']),
            'data_source': etf_data.get('data_source', 'unknown'),
            'last_updated': datetime.now().isoformat()
        }

        # Prepare liquidity filter
        liquidity_filter = {
            'market_cap_threshold': etf_data.get('market_cap_threshold')
        }

        # Insert into definition_groups (or update if exists)
        cursor.execute("""
            INSERT INTO definition_groups
                (name, type, description, metadata, liquidity_filter, environment)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, type, environment)
            DO UPDATE SET
                metadata = EXCLUDED.metadata,
                liquidity_filter = EXCLUDED.liquidity_filter,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            etf_symbol,
            'ETF',
            etf_data.get('name', etf_symbol),
            json.dumps(metadata),
            json.dumps(liquidity_filter),
            self.environment
        ))

        group_id = cursor.fetchone()[0]

        # Delete existing memberships for this group (for clean reload)
        cursor.execute("""
            DELETE FROM group_memberships
            WHERE group_id = %s
        """, (group_id,))

        # Insert new memberships
        for symbol in etf_data['holdings']:
            cursor.execute("""
                INSERT INTO group_memberships (group_id, symbol)
                VALUES (%s, %s)
                ON CONFLICT (group_id, symbol) DO NOTHING
            """, (group_id, symbol))

        self.conn.commit()
        logger.info(f"✓ Inserted {etf_symbol}: {len(etf_data['holdings'])} holdings")
        return True

    except Exception as e:
        self.conn.rollback()
        logger.error(f"Database error inserting {etf_symbol}: {e}")
        return False
```

2. Update environment default (around line 45):
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')  # Changed from 'development'
```

**Test**:
```bash
python scripts/cache_maintenance/load_etf_holdings.py --dry-run --etf SPY
python scripts/cache_maintenance/load_etf_holdings.py --etf QQQ  # Load single ETF
```

**Validation**:
```sql
SELECT dg.name, COUNT(gm.symbol) as holdings
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.type = 'ETF' AND dg.name = 'QQQ'
GROUP BY dg.name;
-- Expected: QQQ | 102
```

---

## Step 10: Update build_stock_metadata.py

**Action**: Query from new tables instead of cache_entries

**File**: `scripts/cache_maintenance/build_stock_metadata.py`

**Changes Required**:

1. Update `collect_all_stocks_from_etfs()` method (around line 100):

```python
def collect_all_stocks_from_etfs(self) -> set:
    """
    Collect unique stock symbols from all ETF holdings in definition_groups

    Returns:
        Set of unique stock symbols
    """
    cursor = self.conn.cursor()

    # Query all symbols from ETF memberships
    cursor.execute("""
        SELECT DISTINCT gm.symbol
        FROM group_memberships gm
        JOIN definition_groups dg ON gm.group_id = dg.id
        WHERE dg.type = 'ETF'
        AND dg.environment = %s
        ORDER BY gm.symbol
    """, (self.environment,))

    stocks = {row[0] for row in cursor.fetchall()}
    logger.info(f"Collected {len(stocks)} unique stocks from ETFs")
    return stocks
```

2. Update `build_etf_membership_map()` method (around line 150):

```python
def build_etf_membership_map(self, stocks: set) -> dict:
    """
    Build reverse mapping: stock → [list of ETFs]

    Args:
        stocks: Set of stock symbols

    Returns:
        Dict mapping stock symbol to list of ETF names
    """
    cursor = self.conn.cursor()

    membership_map = {}

    for symbol in stocks:
        # Query all ETFs containing this symbol
        cursor.execute("""
            SELECT dg.name
            FROM definition_groups dg
            JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            AND gm.symbol = %s
            ORDER BY dg.name
        """, (self.environment, symbol))

        etfs = [row[0] for row in cursor.fetchall()]
        membership_map[symbol] = etfs

    logger.info(f"Built membership map for {len(membership_map)} stocks")
    return membership_map
```

3. Update environment default (around line 45):
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Note**: This script still writes to `cache_entries` for `stock_metadata` type. We can optionally create a `stock_metadata` table in a future sprint.

**Test**:
```bash
python scripts/cache_maintenance/build_stock_metadata.py --dry-run
python scripts/cache_maintenance/build_stock_metadata.py --rebuild
```

**Validation**:
```sql
-- Check stock_metadata entries created
SELECT COUNT(*) FROM cache_entries WHERE type = 'stock_metadata';
-- Expected: ~3700

-- Check sample stock has correct ETF memberships
SELECT value->'member_of_etfs' FROM cache_entries
WHERE type = 'stock_metadata' AND key = 'AAPL';
-- Expected: Array of ETF names
```

---

## Step 11: Update organize_sectors_industries.py

**Action**: Insert sectors into definition_groups

**File**: `scripts/cache_maintenance/organize_sectors_industries.py`

**Changes Required**:

1. Update `create_sector_entries()` method (around line 180):

```python
def create_sector_entries(self):
    """Create sector entries in definition_groups"""

    logger.info(f"Creating {len(self.sectors)} sector entries...")

    cursor = self.conn.cursor()
    created = 0

    for sector_key, sector_data in self.sectors.items():
        try:
            # Prepare metadata with industries and representative stocks
            metadata = {
                'industries': sector_data['industries'],
                'representative_stocks': sector_data['representative_stocks']
            }

            if self.dry_run:
                logger.info(f"[DRY-RUN] Would create sector: {sector_key}")
                created += 1
                continue

            # Insert into definition_groups
            cursor.execute("""
                INSERT INTO definition_groups
                    (name, type, description, metadata, environment)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name, type, environment)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                sector_key,
                'SECTOR',
                sector_data['description'],
                json.dumps(metadata),
                self.environment
            ))

            created += 1
            logger.info(f"✓ Created sector: {sector_key}")

        except Exception as e:
            logger.error(f"Error creating sector {sector_key}: {e}")

    if not self.dry_run:
        self.conn.commit()

    logger.info(f"Created {created} sector entries")
```

2. Update environment default:
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Test**:
```bash
python scripts/cache_maintenance/organize_sectors_industries.py --dry-run
python scripts/cache_maintenance/organize_sectors_industries.py
```

**Validation**:
```sql
SELECT name, type, jsonb_array_length(metadata->'industries') as industry_count
FROM definition_groups
WHERE type = 'SECTOR'
ORDER BY name;
-- Expected: 11 sectors with 4-5 industries each
```

---

## Step 12: Update organize_universe.py

**Action**: Insert themes into definition_groups

**File**: `scripts/cache_maintenance/organize_universe.py`

**Changes Required**:

1. Update `organize_theme_definitions()` method (around line 600):

```python
def organize_theme_definitions(self):
    """Create theme definition entries in definition_groups"""

    logger.info(f"Creating {len(self.themes)} theme entries...")

    cursor = self.conn.cursor()

    if not self.dry_run and not self.preserve:
        # Delete existing theme entries
        cursor.execute("""
            DELETE FROM definition_groups
            WHERE type = 'THEME'
            AND environment = %s
        """, (self.environment,))
        logger.info(f"Deleted {cursor.rowcount} existing themes")

    created = 0

    for theme_key, theme_data in self.themes.items():
        try:
            # Prepare metadata
            metadata = {
                'selection_criteria': theme_data.get('selection_criteria', ''),
                'related_themes': theme_data.get('related_themes', [])
            }

            if self.dry_run:
                logger.info(f"[DRY-RUN] Would create theme: {theme_key} ({len(theme_data['symbols'])} symbols)")
                created += 1
                continue

            # Insert into definition_groups
            cursor.execute("""
                INSERT INTO definition_groups
                    (name, type, description, metadata, environment)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name, type, environment)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                theme_key,
                'THEME',
                theme_data['description'],
                json.dumps(metadata),
                self.environment
            ))

            group_id = cursor.fetchone()[0]

            # Delete existing memberships
            cursor.execute("""
                DELETE FROM group_memberships
                WHERE group_id = %s
            """, (group_id,))

            # Insert theme memberships
            for symbol in theme_data['symbols']:
                cursor.execute("""
                    INSERT INTO group_memberships (group_id, symbol)
                    VALUES (%s, %s)
                    ON CONFLICT (group_id, symbol) DO NOTHING
                """, (group_id, symbol))

            created += 1
            logger.info(f"✓ Created theme: {theme_key} ({len(theme_data['symbols'])} symbols)")

        except Exception as e:
            logger.error(f"Error creating theme {theme_key}: {e}")

    if not self.dry_run:
        self.conn.commit()

    logger.info(f"Created {created} theme entries")
```

2. Update environment default:
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Test**:
```bash
python scripts/cache_maintenance/organize_universe.py --dry-run
python scripts/cache_maintenance/organize_universe.py --preserve
```

**Validation**:
```sql
SELECT dg.name, COUNT(gm.symbol) as symbol_count
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.type = 'THEME'
GROUP BY dg.name
ORDER BY symbol_count DESC;
-- Expected: 20 themes with 7-17 symbols each
```

---

## Step 13: Update query_relationships.py

**Action**: Query from new tables using JOINs

**File**: `scripts/cache_maintenance/query_relationships.py`

**Changes Required**:

1. Update `get_etf_holdings()` method (around line 58):

```python
def get_etf_holdings(self, etf_symbol: str) -> Optional[Dict[str, any]]:
    """
    Get holdings for an ETF from definition_groups

    Args:
        etf_symbol: ETF ticker symbol

    Returns:
        Dict with holdings data or None if not found
    """
    cursor = self.conn.cursor()

    # Get ETF info
    cursor.execute("""
        SELECT
            id,
            name,
            description,
            metadata,
            liquidity_filter
        FROM definition_groups
        WHERE type = 'ETF'
        AND name = %s
        AND environment = %s
    """, (etf_symbol.upper(), self.environment))

    row = cursor.fetchone()
    if not row:
        return None

    group_id, name, description, metadata, liquidity_filter = row

    # Get holdings
    cursor.execute("""
        SELECT symbol
        FROM group_memberships
        WHERE group_id = %s
        ORDER BY symbol
    """, (group_id,))

    holdings = [row[0] for row in cursor.fetchall()]

    return {
        'etf_symbol': etf_symbol.upper(),
        'name': description or name,
        'holdings': holdings,
        'total_holdings': len(holdings),
        'metadata': metadata or {},
        'liquidity_filter': liquidity_filter or {}
    }
```

2. Update `get_stock_etfs()` method (around line 96):

```python
def get_stock_etfs(self, stock_symbol: str) -> Optional[Dict[str, any]]:
    """
    Get ETFs containing a stock

    Args:
        stock_symbol: Stock ticker symbol

    Returns:
        Dict with ETF membership data or None if not found
    """
    cursor = self.conn.cursor()

    # Get all ETFs containing this symbol
    cursor.execute("""
        SELECT dg.name, dg.description
        FROM definition_groups dg
        JOIN group_memberships gm ON dg.id = gm.group_id
        WHERE dg.type = 'ETF'
        AND gm.symbol = %s
        AND dg.environment = %s
        ORDER BY dg.name
    """, (stock_symbol.upper(), self.environment))

    etfs = [(row[0], row[1]) for row in cursor.fetchall()]

    if not etfs:
        # Try stock_metadata from cache_entries (fallback)
        cursor.execute("""
            SELECT name, value->'member_of_etfs'
            FROM cache_entries
            WHERE type = 'stock_metadata'
            AND key = %s
            AND environment = %s
        """, (stock_symbol.upper(), self.environment))

        row = cursor.fetchone()
        if row:
            import json
            etf_list = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            return {
                'stock_symbol': stock_symbol.upper(),
                'name': row[0],
                'member_of_etfs': etf_list,
                'sector': None,  # Would need to query from stock_metadata
                'industry': None
            }
        return None

    return {
        'stock_symbol': stock_symbol.upper(),
        'member_of_etfs': [etf[0] for etf in etfs],
        'etf_details': etfs
    }
```

3. Update `get_theme_members()` method (around line 200):

```python
def get_theme_members(self, theme_key: str) -> Optional[Dict[str, any]]:
    """
    Get stocks in a theme

    Args:
        theme_key: Theme identifier

    Returns:
        Dict with theme data or None if not found
    """
    cursor = self.conn.cursor()

    # Get theme info
    cursor.execute("""
        SELECT
            id,
            name,
            description,
            metadata
        FROM definition_groups
        WHERE type = 'THEME'
        AND name = %s
        AND environment = %s
    """, (theme_key, self.environment))

    row = cursor.fetchone()
    if not row:
        return None

    group_id, name, description, metadata = row

    # Get theme members
    cursor.execute("""
        SELECT symbol
        FROM group_memberships
        WHERE group_id = %s
        ORDER BY symbol
    """, (group_id,))

    symbols = [row[0] for row in cursor.fetchall()]

    return {
        'theme_key': theme_key,
        'name': name,
        'description': description,
        'symbols': symbols,
        'metadata': metadata or {}
    }
```

4. Update environment default:
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Test**:
```bash
ENVIRONMENT=DEFAULT python scripts/cache_maintenance/query_relationships.py --etf SPY
ENVIRONMENT=DEFAULT python scripts/cache_maintenance/query_relationships.py --stock AAPL
ENVIRONMENT=DEFAULT python scripts/cache_maintenance/query_relationships.py --theme crypto_miners
```

**Expected Output**:
- SPY: 504 holdings listed
- AAPL: 10 ETF memberships
- crypto_miners: 9 symbols

---

## Step 14: Update validate_relationships.py

**Action**: Validate data in new tables

**File**: `scripts/cache_maintenance/validate_relationships.py`

**Changes Required**:

1. Update ETF holdings validation (around line 80):

```python
def validate_etf_holdings(self):
    """Validate ETF holdings in definition_groups"""
    logger.info("[1/5] Validating ETF holdings...")

    cursor = self.conn.cursor()

    # Count total ETFs
    cursor.execute("""
        SELECT COUNT(*)
        FROM definition_groups
        WHERE type = 'ETF'
        AND environment = %s
    """, (self.environment,))

    total_etfs = cursor.fetchone()[0]
    logger.info(f"  Total ETFs: {total_etfs}")

    # Find ETFs with no holdings
    cursor.execute("""
        SELECT dg.name
        FROM definition_groups dg
        LEFT JOIN group_memberships gm ON dg.id = gm.group_id
        WHERE dg.type = 'ETF'
        AND dg.environment = %s
        GROUP BY dg.id, dg.name
        HAVING COUNT(gm.id) = 0
    """, (self.environment,))

    empty_etfs = cursor.fetchall()
    logger.info(f"  Empty holdings: {len(empty_etfs)} {'(✓ PASS)' if len(empty_etfs) == 0 else '(✗ FAIL)'}")

    if empty_etfs:
        logger.warning(f"  Empty ETFs: {[e[0] for e in empty_etfs]}")
```

2. Update bidirectional validation (around line 150):

```python
def validate_bidirectional_relationships(self):
    """Validate ETF ↔ stock relationships"""
    logger.info("[3/5] Validating bidirectional relationships...")

    cursor = self.conn.cursor()

    # Count total relationships
    cursor.execute("""
        SELECT COUNT(*)
        FROM group_memberships gm
        JOIN definition_groups dg ON gm.group_id = dg.id
        WHERE dg.type IN ('ETF', 'THEME')
        AND dg.environment = %s
    """, (self.environment,))

    total_relationships = cursor.fetchone()[0]
    logger.info(f"  Total relationships: {total_relationships}")

    # Check forward integrity (group → membership)
    cursor.execute("""
        SELECT COUNT(*)
        FROM group_memberships gm
        WHERE NOT EXISTS (
            SELECT 1 FROM definition_groups dg
            WHERE dg.id = gm.group_id
        )
    """)

    forward_errors = cursor.fetchone()[0]
    logger.info(f"  Forward errors: {forward_errors}")

    # Check reverse integrity (membership → group)
    cursor.execute("""
        SELECT COUNT(DISTINCT gm.group_id)
        FROM group_memberships gm
        JOIN definition_groups dg ON gm.group_id = dg.id
        WHERE dg.environment = %s
    """, (self.environment,))

    valid_groups = cursor.fetchone()[0]

    integrity = 100.0 if forward_errors == 0 else 0.0
    logger.info(f"  Integrity: {integrity:.2f}% {'(✓ PASS)' if integrity == 100 else '(✗ FAIL)'}")
```

3. Update environment default:
```python
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Test**:
```bash
ENVIRONMENT=DEFAULT python scripts/cache_maintenance/validate_relationships.py
```

**Expected Output**:
```
[1/5] Validating ETF holdings...
  Total ETFs: 24
  Empty holdings: 0 (✓ PASS)

[2/5] Validating stock metadata...
  (still checks cache_entries)

[3/5] Validating bidirectional relationships...
  Total relationships: ~12,000
  Forward errors: 0
  Reverse errors: 0
  Integrity: 100.00% (✓ PASS)

Overall Status: ✓ ALL PASSED
```

---

## Step 15: Fix Environment Variable Issue

**Action**: Update all scripts to default to 'DEFAULT' environment

**Files to Update**:
1. `load_etf_holdings.py`
2. `build_stock_metadata.py`
3. `organize_sectors_industries.py`
4. `organize_universe.py`
5. `query_relationships.py`
6. `validate_relationships.py`

**Change** (in each file, around line 45):
```python
# OLD:
self.environment = os.getenv('ENVIRONMENT', 'development')

# NEW:
self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')
```

**Or Add to .env file**:
```bash
echo "ENVIRONMENT=DEFAULT" >> .env
```

**Test All Scripts**:
```bash
# Should work without ENVIRONMENT= prefix now
python scripts/cache_maintenance/query_relationships.py --etf SPY
python scripts/cache_maintenance/validate_relationships.py
```

---

## Success Criteria for Session 2

**Must Pass** ✅:
- [x] load_etf_holdings.py updated and tested
- [x] build_stock_metadata.py updated and tested
- [x] organize_sectors_industries.py updated and tested
- [x] organize_universe.py updated and tested
- [x] query_relationships.py updated and tested
- [x] validate_relationships.py updated and tested
- [x] Environment variable default fixed in all scripts
- [x] All dry-run tests pass
- [x] Sample queries return correct results
- [x] Zero errors in script execution

---

## Testing Checklist

Run each command and verify expected output:

```bash
# 1. Load ETF holdings (should use new tables)
python scripts/cache_maintenance/load_etf_holdings.py --dry-run --etf QQQ

# 2. Build stock metadata (should query from new tables)
python scripts/cache_maintenance/build_stock_metadata.py --dry-run

# 3. Organize sectors (should use new tables)
python scripts/cache_maintenance/organize_sectors_industries.py --dry-run

# 4. Organize themes (should use new tables)
python scripts/cache_maintenance/organize_universe.py --dry-run

# 5. Query ETF holdings (should use new tables)
python scripts/cache_maintenance/query_relationships.py --etf SPY

# 6. Query stock memberships (should use new tables)
python scripts/cache_maintenance/query_relationships.py --stock AAPL

# 7. Query theme (should use new tables)
python scripts/cache_maintenance/query_relationships.py --theme crypto_miners

# 8. Validate relationships (should validate new tables)
python scripts/cache_maintenance/validate_relationships.py
```

**All commands should execute without errors and return expected data.**

---

## Troubleshooting

### Issue: Script can't find new tables
**Symptoms**: `relation "definition_groups" does not exist`
**Fix**: Verify Session 1 completed - tables must exist first

### Issue: Environment mismatch (0 results)
**Symptoms**: Queries return 0 results even though data exists
**Fix**: Check environment variable matches data:
```sql
SELECT DISTINCT environment FROM definition_groups;
-- Should show 'DEFAULT'
```

### Issue: Foreign key violation
**Symptoms**: Cannot insert into group_memberships
**Fix**: Ensure group_id from definition_groups.id exists:
```python
# Get group_id first
cursor.execute("INSERT INTO definition_groups (...) RETURNING id")
group_id = cursor.fetchone()[0]

# Then use it
cursor.execute("INSERT INTO group_memberships (group_id, ...) VALUES (%s, ...)", (group_id,))
```

---

## Next Steps

Once Session 2 validation passes:
1. ✅ All scripts updated to use new tables
2. ✅ All dry-run tests pass
3. → **Proceed to SESSION3_TESTING_DOCUMENTATION.md**

---

**Session 2 Status**: □ Not Started | □ In Progress | □ Complete
**Completion Date**: _____________
**Validated By**: _____________
