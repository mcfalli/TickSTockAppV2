# Sprint 57: Implementation Guide
## Cache-Based Universe Loading & Organization Tooling

**Detailed implementation instructions with code examples**

---

## Table of Contents

1. [Phase 1: Cache-Based Universe Loading](#phase-1-cache-based-universe-loading)
2. [Phase 2: Cache Organization Tooling](#phase-2-cache-organization-tooling)
3. [Phase 3: UI Updates](#phase-3-ui-updates)
4. [Testing Guide](#testing-guide)
5. [Deployment Steps](#deployment-steps)

---

## Phase 1: Cache-Based Universe Loading

### Step 1.1: Create Database Operations Module

**File**: `C:\Users\McDude\TickStockPL\src\database\cache_operations.py`

```python
"""
Database operations for cache_entries table.
Provides methods to query universe data stored in cache.
"""

import json
import logging
from typing import List, Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class CacheOperations:
    """Database operations for cache_entries table"""

    def __init__(self):
        """Initialize with database configuration"""
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')

    def _get_connection(self):
        """Get database connection"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def get_universe_symbols(self, universe_type: str, universe_key: str) -> List[str]:
        """
        Get symbols for a universe from cache_entries table.

        Args:
            universe_type: Type of universe ('etf_universe', 'stock_etf_combo')
            universe_key: Key for the specific universe (e.g., 'etf_core')

        Returns:
            List of symbol strings

        Raises:
            ValueError: If universe not found or invalid format
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT value
                    FROM cache_entries
                    WHERE type = %s AND key = %s
                    LIMIT 1
                """, (universe_type, universe_key))

                row = cursor.fetchone()

            conn.close()

            if not row:
                raise ValueError(
                    f"Universe not found: type={universe_type}, key={universe_key}"
                )

            # Extract symbols from JSONB value
            value = row['value']

            # Handle different JSONB formats
            if isinstance(value, list):
                symbols = value
            elif isinstance(value, dict) and 'symbols' in value:
                symbols = value['symbols']
            elif isinstance(value, dict) and isinstance(value.get('value'), list):
                symbols = value['value']
            else:
                raise ValueError(
                    f"Invalid value format in cache_entries: {type(value)}"
                )

            logger.info(
                f"Loaded {len(symbols)} symbols from cache: "
                f"{universe_type}:{universe_key}"
            )

            return symbols

        except psycopg2.Error as e:
            logger.error(f"Database error loading universe: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading universe from cache: {e}")
            raise

    def list_available_universes(self) -> List[Dict[str, Any]]:
        """
        List all available universes in cache.

        Returns:
            List of dicts with universe metadata
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        type,
                        name,
                        key,
                        CASE
                            WHEN jsonb_typeof(value) = 'array' THEN jsonb_array_length(value)
                            WHEN jsonb_typeof(value->'symbols') = 'array' THEN jsonb_array_length(value->'symbols')
                            ELSE 0
                        END as symbol_count,
                        updated_at
                    FROM cache_entries
                    WHERE type IN ('etf_universe', 'stock_etf_combo', 'stock_universe')
                    ORDER BY type, name, key
                """)

                results = cursor.fetchall()

            conn.close()

            universes = []
            for row in results:
                universes.append({
                    'type': row['type'],
                    'name': row['name'],
                    'key': row['key'],
                    'symbol_count': row['symbol_count'],
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                })

            logger.info(f"Found {len(universes)} universes in cache")
            return universes

        except Exception as e:
            logger.error(f"Error listing universes: {e}")
            return []

    def validate_universe_exists(self, universe_type: str, universe_key: str) -> bool:
        """Check if a universe exists in cache"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 1
                    FROM cache_entries
                    WHERE type = %s AND key = %s
                """, (universe_type, universe_key))

                exists = cursor.fetchone() is not None

            conn.close()
            return exists

        except Exception as e:
            logger.error(f"Error checking universe existence: {e}")
            return False
```

### Step 1.2: Update Data Load Handler

**File**: `C:\Users\McDude\TickStockPL\src\jobs\data_load_handler.py`

**Add import at top:**
```python
from src.database.cache_operations import CacheOperations
```

**Add instance variable in `__init__`:**
```python
class DataLoadJobHandler:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.loader = MassiveHistoricalLoader()
        self.pubsub = redis_client.pubsub()
        self.job_start_time = None
        self.cache_ops = CacheOperations()  # ADD THIS LINE
```

**Add new method to `DataLoadJobHandler` class:**
```python
def _load_symbols_from_cache(self, universe_type: str, universe_key: str) -> List[str]:
    """
    Load symbols from cache_entries table instead of CSV files.

    Args:
        universe_type: Type of universe ('etf_universe', 'stock_etf_combo')
        universe_key: Key for the specific universe

    Returns:
        List of symbol strings
    """
    try:
        logger.info(
            f"Loading symbols from cache: {universe_type}:{universe_key}"
        )

        symbols = self.cache_ops.get_universe_symbols(universe_type, universe_key)

        if not symbols:
            raise ValueError(f"No symbols found for {universe_type}:{universe_key}")

        logger.info(
            f"✓ Loaded {len(symbols)} symbols from cache: "
            f"{universe_type}:{universe_key}"
        )

        return symbols

    except Exception as e:
        logger.error(f"Failed to load symbols from cache: {e}")
        raise
```

**Update `_execute_csv_universe_load` method:**

Find the existing method (around line 220-250) and modify:

```python
def _execute_csv_universe_load(self, job: dict[str, Any]):
    """
    Execute CSV universe load job.
    Now supports both CSV files and cache-based loading.
    """
    job_id = job["job_id"]

    # NEW: Check if we have universe_key (cache-based) or csv_file (file-based)
    universe_key_full = job.get("universe_key")  # Format: "etf_universe:etf_core"
    csv_file = job.get("csv_file")

    symbols = []
    source_name = ""

    try:
        if universe_key_full:
            # === NEW: Cache-based loading ===
            logger.info(f"[CACHE MODE] Loading from cache: {universe_key_full}")

            # Parse universe key
            if ':' not in universe_key_full:
                raise ValueError(f"Invalid universe key format: {universe_key_full}")

            universe_type, universe_key = universe_key_full.split(':', 1)

            # Load symbols from cache
            symbols = self._load_symbols_from_cache(universe_type, universe_key)
            source_name = universe_key_full

            logger.info(
                f"✓ Cache load successful: {len(symbols)} symbols from {universe_key_full}"
            )

        elif csv_file:
            # === EXISTING: CSV file loading (backward compatibility) ===
            logger.info(f"[CSV MODE] Loading from file: {csv_file}")

            csv_path = os.path.join("data", "universes", csv_file)

            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"CSV file not found: {csv_path}")

            # Read CSV file (existing logic)
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get("symbol", "").strip()
                    if symbol:
                        symbols.append(symbol)

            source_name = csv_file
            logger.info(f"✓ CSV load successful: {len(symbols)} symbols from {csv_file}")

        else:
            raise ValueError("Either universe_key or csv_file required")

        if not symbols:
            raise ValueError(f"No symbols found in {source_name}")

        # Continue with existing logic for OHLCV loading
        years = job.get("years", 1)
        include_ohlcv = job.get("include_ohlcv", True)

        self._update_job_status(
            job_id, "running", 5, f"Starting load for {len(symbols)} symbols from {source_name}"
        )

        # ... rest of existing method continues unchanged ...

    except Exception as e:
        logger.error(f"CSV universe load failed: {e}")
        self._update_job_status(job_id, "failed", 0, str(e))
```

---

## Phase 2: Cache Organization Tooling

### Step 2.1: Create Maintenance Scripts Directory

```bash
mkdir -p C:\Users\McDude\TickStockAppV2\scripts\cache_maintenance
```

### Step 2.2: Cache Organization Script

**File**: `C:\Users\McDude\TickStockAppV2\scripts\cache_maintenance\organize_universes.py`

```python
"""
Cache Universe Organization Script

Organizes and rebuilds universe entries in cache_entries table.
Replaces the UI-based "Update and Organize Cache" button.

Usage:
    python scripts/cache_maintenance/organize_universes.py [options]

Options:
    --preserve    Preserve existing entries (append mode)
    --dry-run     Show what would be changed without making changes
    --verbose     Show detailed logging

Example:
    python scripts/cache_maintenance/organize_universes.py --preserve --verbose
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch

# Add parent directory to path for imports
sys.path.insert(0, 'C:\\Users\\McDude\\TickStockAppV2')

from src.core.services.config_manager import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UniverseOrganizer:
    """Organize and maintain universe entries in cache_entries"""

    def __init__(self, dry_run: bool = False):
        """Initialize organizer with database connection"""
        self.dry_run = dry_run
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.stats = {
            'added': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

    def get_connection(self):
        """Get database connection"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def organize_etf_universes(self, preserve_existing: bool = False):
        """
        Organize ETF universe entries using standardized structure.

        Organization:
        - master_* : Master lists (all ETFs)
        - index_*  : Broad market indexes
        - sector_* : Sector-based groupings
        - theme_*  : Thematic groupings
        """
        logger.info("Organizing ETF universes...")

        # Define universe structures with naming convention
        etf_universes = {
            # Master Lists
            'master_all_etfs': {
                'name': 'All ETFs',
                'description': 'Master list of all tracked ETFs',
                'symbols': ['SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'AGG', 'BND',
                           'XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE',
                           'VUG', 'VTV', 'SCHG', 'SCHV', 'TLT', 'IEF', 'IEFA', 'EEM', 'IBIT', 'FBTC']
            },

            # Index-based (Broad Market)
            'index_broad_market': {
                'name': 'Broad Market Index ETFs',
                'description': 'Major market index ETFs',
                'symbols': ['SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'MDY']
            },

            # Sector-based
            'sector_sector_etfs': {
                'name': 'Sector ETFs',
                'description': 'S&P Sector SPDR ETFs',
                'symbols': ['XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE']
            },
            'sector_bonds': {
                'name': 'Fixed Income ETFs',
                'description': 'Bond and fixed income ETFs',
                'symbols': ['AGG', 'BND', 'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'MUB']
            },
            'sector_international': {
                'name': 'International ETFs',
                'description': 'International and emerging market ETFs',
                'symbols': ['VEA', 'VWO', 'IEFA', 'EEM', 'EFA', 'IEMG']
            },

            # Theme-based
            'theme_growth_value': {
                'name': 'Growth & Value ETFs',
                'description': 'Growth and value style ETFs',
                'symbols': ['VUG', 'VTV', 'SCHG', 'SCHV', 'IWF', 'IWD', 'MTUM', 'QUAL', 'USMV']
            },
            'theme_crypto': {
                'name': 'Cryptocurrency ETFs',
                'description': 'Bitcoin and cryptocurrency ETFs',
                'symbols': ['IBIT', 'FBTC', 'GBTC', 'BITO']
            }
        }

        conn = self.get_connection()

        try:
            if not preserve_existing:
                # Delete existing ETF universes
                if not self.dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM cache_entries
                            WHERE type = 'etf_universe'
                        """)
                        deleted_count = cursor.rowcount
                        self.stats['deleted'] += deleted_count
                        logger.info(f"Deleted {deleted_count} existing ETF universe entries")

            # Insert/update universe entries
            for key, data in etf_universes.items():
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upsert: etf_universe:{key} ({len(data['symbols'])} symbols)")
                    continue

                with conn.cursor() as cursor:
                    # Upsert entry
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (type, key, environment)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    """, (
                        'etf_universe',
                        data['name'],
                        key,
                        json.dumps(data['symbols']),
                        'DEFAULT'
                    ))

                    if cursor.rowcount > 0:
                        self.stats['added' if preserve_existing else 'updated'] += 1
                        logger.info(
                            f"✓ Upserted etf_universe:{key} - {len(data['symbols'])} symbols"
                        )

            if not self.dry_run:
                conn.commit()
                logger.info("ETF universe organization complete")

        except Exception as e:
            logger.error(f"Error organizing ETF universes: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    def organize_stock_universes(self, preserve_existing: bool = False):
        """
        Organize stock universe entries using standardized structure.

        Organization:
        - master_* : Master lists (all stocks)
        - index_*  : Major indexes (SP500, NASDAQ100, DOW30, Russell3000)
        - sector_* : Sector-based groupings
        - theme_*  : Thematic groupings
        """
        logger.info("Organizing stock universes...")

        # Define universe structures with naming convention
        stock_universes = {
            # Master Lists
            'master_all_stocks': {
                'name': 'All Stocks',
                'description': 'Master list of all tracked stocks',
                'symbols': []  # Would contain all tracked stocks
            },

            # Index-based
            'index_sp500': {
                'name': 'S&P 500',
                'description': 'S&P 500 index components',
                'symbols': []  # Would load from CSV or API
            },
            'index_nasdaq100': {
                'name': 'NASDAQ 100',
                'description': 'NASDAQ 100 index components',
                'symbols': []  # Would load from CSV or API
            },
            'index_dow30': {
                'name': 'Dow Jones 30',
                'description': 'Dow Jones Industrial Average components',
                'symbols': []  # Would load from CSV or API
            },
            'index_russell3000': {
                'name': 'Russell 3000',
                'description': 'Russell 3000 index components',
                'symbols': []  # Would load from CSV or API
            },

            # Sector-based (example: top stocks in each sector)
            'sector_technology': {
                'name': 'Technology Sector',
                'description': 'Major technology stocks',
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'AVGO', 'ORCL', 'CRM', 'ADBE']
            },
            'sector_healthcare': {
                'name': 'Healthcare Sector',
                'description': 'Major healthcare stocks',
                'symbols': ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY']
            },
            'sector_financials': {
                'name': 'Financial Sector',
                'description': 'Major financial stocks',
                'symbols': ['JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'BLK', 'C', 'SPGI']
            },

            # Theme-based
            'theme_dividend': {
                'name': 'Dividend Stocks',
                'description': 'High-quality dividend-paying stocks',
                'symbols': []  # Would contain dividend aristocrats
            },
            'theme_growth': {
                'name': 'Growth Stocks',
                'description': 'High-growth stocks',
                'symbols': []  # Would contain high-growth stocks
            },
            'theme_value': {
                'name': 'Value Stocks',
                'description': 'Value-oriented stocks',
                'symbols': []  # Would contain undervalued stocks
            }
        }

        conn = self.get_connection()

        try:
            if not preserve_existing:
                # Delete existing stock universes
                if not self.dry_run:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            DELETE FROM cache_entries
                            WHERE type = 'stock_universe'
                        """)
                        deleted_count = cursor.rowcount
                        self.stats['deleted'] += deleted_count
                        logger.info(f"Deleted {deleted_count} existing stock universe entries")

            # Insert/update universe entries (only non-empty ones)
            for key, data in stock_universes.items():
                if not data['symbols']:
                    logger.info(f"Skipping {key}: No symbols defined (placeholder)")
                    continue

                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upsert: stock_universe:{key} ({len(data['symbols'])} symbols)")
                    continue

                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (type, key, environment)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    """, (
                        'stock_universe',
                        data['name'],
                        key,
                        json.dumps(data['symbols']),
                        'DEFAULT'
                    ))

                    if cursor.rowcount > 0:
                        self.stats['added' if preserve_existing else 'updated'] += 1
                        logger.info(
                            f"✓ Upserted stock_universe:{key} - {len(data['symbols'])} symbols"
                        )

            if not self.dry_run:
                conn.commit()
                logger.info("Stock universe organization complete")

        except Exception as e:
            logger.error(f"Error organizing stock universes: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            conn.close()

    # NOTE: stock_etf_combo type REMOVED in Sprint 57
    # Use stock_universe and etf_universe types only
    # Combo universes can be created by combining queries from both types

    def print_summary(self):
        """Print organization summary"""
        print("\n" + "="*60)
        print("CACHE ORGANIZATION SUMMARY")
        print("="*60)
        print(f"Added:   {self.stats['added']}")
        print(f"Updated: {self.stats['updated']}")
        print(f"Deleted: {self.stats['deleted']}")
        print(f"Errors:  {self.stats['errors']}")
        print("="*60)

        if self.dry_run:
            print("\n[DRY RUN MODE] No changes were made to the database")
        else:
            print("\n✓ Cache organization complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Organize universe entries in cache_entries table'
    )
    parser.add_argument(
        '--preserve',
        action='store_true',
        help='Preserve existing entries (append mode)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("Cache Universe Organization Script")
    print("="*60)
    print(f"Mode: {'Preserve existing' if args.preserve else 'Replace all'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print("="*60)

    if not args.dry_run and not args.preserve:
        confirm = input("\n⚠️  This will DELETE and replace all ETF/combo universes. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    organizer = UniverseOrganizer(dry_run=args.dry_run)

    try:
        organizer.organize_etf_universes(preserve_existing=args.preserve)
        organizer.organize_stock_universes(preserve_existing=args.preserve)
        organizer.print_summary()

    except Exception as e:
        logger.error(f"Organization failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## Phase 3: UI Updates

### Step 3.1: Comment Out Cache Organization Section

**File**: `C:\Users\McDude\TickStockAppV2\web\templates\admin\historical_data_dashboard.html`

Find lines 480-498 and replace with:

```html
<!-- Cache Management -->
<!-- COMMENTED OUT: Sprint 57 - Moved to maintenance scripts
     See: scripts/cache_maintenance/organize_universes.py
<div class="job-controls">
    <h3>🔧 Cache Organization</h3>
    <p>Rebuild cache entries to organize stocks and ETFs into logical groups (market cap, sectors, themes, etc.)</p>
    <div style="display: flex; flex-direction: column; gap: 20px;">
        <div class="form-group" style="max-width: 500px;">
            <label style="display: flex; align-items: center; cursor: pointer; font-weight: normal;">
                <input type="checkbox" id="preserve_existing" name="preserve_existing" value="1" style="margin-right: 10px; width: auto;">
                <span>Preserve existing entries (append mode)</span>
            </label>
            <small class="form-text">
                When unchecked, will delete and rebuild all stock/ETF cache entries (preserves app_settings)
            </small>
        </div>
        <div>
            <button onclick="rebuildCacheEntries()" class="btn btn-primary">🔧 Update and Organize Cache</button>
        </div>
    </div>
</div>
END COMMENTED OUT SECTION -->

<!-- Cache Organization Note -->
<div class="job-controls" style="background: #f0f8ff; border-left: 4px solid #007bff;">
    <h3>🔧 Cache Organization</h3>
    <p>Cache maintenance has been moved to command-line scripts for better automation and control.</p>
    <div style="background: white; padding: 15px; border-radius: 5px; margin-top: 15px;">
        <h4 style="margin-top: 0;">Run Maintenance Scripts:</h4>
        <pre style="background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;">
# Organize universes (replace all)
python scripts/cache_maintenance/organize_universes.py

# Organize universes (preserve existing)
python scripts/cache_maintenance/organize_universes.py --preserve

# Dry run (preview changes)
python scripts/cache_maintenance/organize_universes.py --dry-run --verbose

# Validate cache integrity
python scripts/cache_maintenance/validate_cache.py
        </pre>
        <p style="margin-bottom: 0;"><strong>Documentation:</strong> <code>scripts/cache_maintenance/README.md</code></p>
    </div>
</div>
```

### Step 3.2: Comment Out Backend Route

**File**: `C:\Users\McDude\TickStockAppV2\src\api\rest\admin_historical_data.py`

Find the `rebuildCacheEntries()` JavaScript function and related backend route. Add comment noting it's deprecated.

---

## Testing Guide

### Test 1: Cache-Based Universe Loading

**Setup:**
```python
# Run cache organization script first
python scripts/cache_maintenance/organize_universes.py --dry-run
python scripts/cache_maintenance/organize_universes.py
```

**Test Steps:**
1. Open Historical Data admin page
2. Select "Cached Universe" radio button
3. Choose "Core ETFs" from dropdown
4. Set duration to "1 Day"
5. Click "Load Universe Data"
6. Monitor job progress
7. Verify symbols loaded from cache (check logs)

**Expected Results:**
- Job submits successfully
- TickStockPL logs show "Loading from cache: etf_universe:core_etfs"
- 10 symbols loaded (SPY, QQQ, IWM, etc.)
- Historical data loads for all symbols
- Zero errors in logs

### Test 2: Validation Script

Create validation script to test cache integrity.

---

## Deployment Steps

### Pre-Deployment

1. **Backup database**:
   ```bash
   pg_dump tickstock > tickstock_backup_sprint57.sql
   ```

2. **Run organization script (dry-run)**:
   ```bash
   python scripts/cache_maintenance/organize_universes.py --dry-run --verbose
   ```

3. **Review changes**:
   - Check dry-run output
   - Verify expected universes
   - Confirm symbol counts

### Deployment

1. **Organize cache** (production):
   ```bash
   python scripts/cache_maintenance/organize_universes.py
   ```

2. **Restart TickStockPL**:
   ```bash
   # Restart data loader service
   ```

3. **Test cache-based loading**:
   - Load "Core ETFs" universe
   - Verify 1-day data loads successfully

4. **Monitor logs**:
   ```bash
   tail -f logs/tickstockpl.log | grep "Loading from cache"
   ```

### Post-Deployment

1. Verify universe dropdown still works
2. Test 2-3 different universes
3. Check database for new cache entries
4. Monitor error rates

---

**Documentation Complete**
**Next**: Create validation script and maintenance README

