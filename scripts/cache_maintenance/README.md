# Cache Maintenance Scripts - Production Guide

**Sprint 60 - COMPLETE** | Last Updated: December 21, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Load Strategies](#load-strategies)
4. [Data Sources & Formats](#data-sources--formats)
5. [Scripts Reference](#scripts-reference)
6. [Maintenance Workflows](#maintenance-workflows)
7. [Database Schema](#database-schema)
8. [Troubleshooting](#troubleshooting)

---

## Overview

These scripts manage ETF-stock-sector-theme relationships stored in PostgreSQL tables:
- **`definition_groups`**: Group definitions (ETFs, sectors, themes, universes)
- **`group_memberships`**: Symbol membership in groups

**Migration Status**: ✅ Sprint 59 completed - All data migrated from JSONB `cache_entries` to relational tables

---

## Quick Start

### Initial Setup (Fresh Database)

```bash
# Complete setup in 6 steps (~15 seconds)
cd C:\Users\McDude\TickStockAppV2

# Step 1: Load ETF holdings from CSV files
python scripts/cache_maintenance/load_etf_holdings.py --mode full

# Step 2: Load stock universes (NASDAQ-100, S&P 500, Dow 30, Russell 3000)
python scripts/cache_maintenance/load_universes.py --mode full

# Step 3: Enrich sector classifications
python scripts/cache_maintenance/enrich_sectors.py --mode full

# Step 4: Validate everything
python scripts/cache_maintenance/validate_relationships.py

# Step 5: Generate data quality report
python scripts/cache_maintenance/generate_report.py --summary

# Step 6: Warm runtime cache
curl -X POST http://localhost:5000/admin/cache/warm
```

**Expected Results**:
- 24 ETFs loaded
- 3,757 stocks discovered
- 4 universes loaded (NASDAQ-100, S&P 500, Dow 30, Russell 3000)
- 15,834 total relationships
- 13.41% sector coverage (549 classified, 3,208 unknown)

---

## Load Strategies

### Strategy 1: FULL RELOAD (TRUNCATE + INSERT)

**When to Use**:
- ✅ Fresh database setup
- ✅ Corrupted data recovery
- ✅ Major structural changes
- ✅ Monthly comprehensive refresh

**What It Does**:
1. Deletes ALL existing data for the type
2. Inserts fresh data from CSV files
3. Rebuilds all relationships

**Command**:
```bash
# ETF Holdings - Full Reload
python scripts/cache_maintenance/load_etf_holdings.py --mode full

# Universes - Full Reload
python scripts/cache_maintenance/load_universes.py --mode full

# Sector Enrichment - Full Reload
python scripts/cache_maintenance/enrich_sectors.py --mode full
```

**Pros**:
- ✅ Clean slate (no stale data)
- ✅ Simple to understand
- ✅ Guaranteed consistency

**Cons**:
- ❌ Slower (reloads everything)
- ❌ Brief data unavailability
- ❌ Loses custom manual edits

**Runtime**: ~5-10 seconds for full ETF reload

---

### Strategy 2: INCREMENTAL UPDATE (UPSERT)

**When to Use**:
- ✅ Weekly ETF holdings updates
- ✅ Minor symbol additions/removals
- ✅ Preserving manual edits
- ✅ Fast updates needed

**What It Does**:
1. Compares CSV data with database
2. Updates only changed records
3. Inserts new records
4. Optionally removes deleted records

**Command**:
```bash
# ETF Holdings - Incremental Update
python scripts/cache_maintenance/load_etf_holdings.py --mode incremental

# Universes - Incremental Update
python scripts/cache_maintenance/load_universes.py --mode incremental

# Sector Enrichment - Incremental Update
python scripts/cache_maintenance/enrich_sectors.py --mode incremental
```

**Pros**:
- ✅ Fast (only processes changes)
- ✅ No data downtime
- ✅ Preserves custom edits

**Cons**:
- ❌ More complex logic
- ❌ Requires change detection
- ❌ May miss deletions

**Runtime**: ~1-2 seconds (only changed ETFs)

---

### Strategy 3: DRY-RUN (PREVIEW ONLY)

**When to Use**:
- ✅ Testing new CSV files
- ✅ Previewing changes before applying
- ✅ Debugging data issues
- ✅ Learning what script does

**What It Does**:
1. Reads CSV files
2. Shows what WOULD change
3. Does NOT modify database
4. Displays detailed preview

**Command**:
```bash
# Preview ETF load
python scripts/cache_maintenance/load_etf_holdings.py --dry-run

# Preview sector assignments
python scripts/cache_maintenance/build_stock_metadata.py --dry-run
```

**Output Example**:
```
[DRY RUN] Would load ETF: SPY (504 holdings)
[DRY RUN] Would load ETF: VOO (505 holdings)
[DRY RUN] Would create 1,009 new relationships
[DRY RUN] Would update 10,769 existing relationships
[DRY RUN] No changes written to database
```

---

### Decision Matrix: Which Strategy to Use?

| Scenario | Strategy | Command |
|----------|----------|---------|
| First-time setup | FULL RELOAD | `--rebuild` or default |
| Weekly CSV update | INCREMENTAL | `--mode incremental` (Sprint 60) |
| Monthly refresh | FULL RELOAD | `--rebuild` |
| Testing changes | DRY-RUN | `--dry-run` |
| Data corruption | FULL RELOAD | `--rebuild` |
| One ETF changed | INCREMENTAL | `--mode incremental` |
| Verify before prod | DRY-RUN first | `--dry-run`, then run normal |

---

## Data Sources & Formats

### 1. ETF Holdings CSV Files

**Location**: `scripts/cache_maintenance/holdings/*.csv`

**Format** (Required):
```csv
symbol,weight
AAPL,6.50
MSFT,5.80
NVDA,4.20
```

**Column Specifications**:
| Column | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| `symbol` | ✅ YES | VARCHAR | Stock ticker symbol | AAPL |
| `weight` | ❌ NO | DECIMAL | ETF weight % | 6.50 |

**Naming Convention**: `{etf_symbol}_holdings.csv` (lowercase)
- ✅ `spy_holdings.csv`
- ❌ `SPY_holdings.csv`
- ❌ `spy.csv`

**Current Files** (28 total):
```
holdings/
├── spy_holdings.csv      (504 stocks)
├── voo_holdings.csv      (505 stocks)
├── vti_holdings.csv      (3,508 stocks)
├── iwm_holdings.csv      (1,943 stocks)
├── qqq_holdings.csv      (102 stocks)
├── xlk_holdings.csv      (Sector: Technology)
├── xlv_holdings.csv      (Sector: Healthcare)
└── ... (21 more ETF files)
```

---

### 2. Universe CSV Files

**Location**: `scripts/cache_maintenance/holdings/*.csv`

**Format** (Simple symbol list):
```csv
symbol
AAPL
MSFT
NVDA
```

**OR** (No header - just symbols):
```
AAPL
MSFT
NVDA
```

**Column Specifications**:
| Column | Required | Type | Description |
|--------|----------|------|-------------|
| `symbol` | ✅ YES | VARCHAR | Stock ticker |

**Current Files**:
- `holdings/nasdaq100.csv` (102 symbols)
- `holdings/sp500.csv` (505 symbols)
- `holdings/dow30.csv` (30 symbols)
- `holdings/russell3000.csv` (3,000 symbols)

**Status**: ✅ Loader available (load_universes.py)

---

### 3. Sector Classification Method

**Method**: Sector ETF membership analysis

**How It Works**:
- Analyzes 11 sector ETF holdings (XLK, XLF, XLV, etc.)
- Maps each sector ETF to GICS sector classification
- Assigns stocks based on sector ETF membership

**Sector ETF Mapping**:
| ETF | Sector | Holdings |
|-----|--------|----------|
| XLK | Information Technology | 72 stocks |
| XLF | Financials | 60 stocks |
| XLV | Health Care | 60 stocks |
| XLE | Energy | 25 stocks |
| XLI | Industrials | 75 stocks |
| XLY | Consumer Discretionary | 55 stocks |
| XLP | Consumer Staples | 33 stocks |
| XLU | Utilities | 30 stocks |
| XLB | Materials | 30 stocks |
| XLRE | Real Estate | 30 stocks |
| XLC | Communication Services | 25 stocks |

**Status**: ✅ Enrichment available (enrich_sectors.py)

---

## Scripts Reference

### 1. load_etf_holdings.py

**Purpose**: Load ETF holdings from CSV files into database

**Usage**:
```bash
# Default: Load all ETFs (overwrites existing)
python scripts/cache_maintenance/load_etf_holdings.py

# Rebuild: Delete all + reload
python scripts/cache_maintenance/load_etf_holdings.py --rebuild

# Dry-run: Preview without changes
python scripts/cache_maintenance/load_etf_holdings.py --dry-run

# Specific ETF only
python scripts/cache_maintenance/load_etf_holdings.py --etf SPY

# Sprint 60: Incremental mode (only changed ETFs)
python scripts/cache_maintenance/load_etf_holdings.py --mode incremental
```

**What It Creates**:
```sql
-- Creates definition_groups entry (ETF)
INSERT INTO definition_groups (name, type, description, environment)
VALUES ('SPY', 'ETF', 'SPDR S&P 500 ETF Trust', 'DEFAULT');

-- Creates group_memberships entries (holdings)
INSERT INTO group_memberships (group_id, symbol)
VALUES (1, 'AAPL'), (1, 'MSFT'), (1, 'NVDA'), ...;
```

**Runtime**: ~5 seconds (28 ETFs, 11,778 relationships)

---

### 2. build_stock_metadata.py

**Purpose**: Assign stocks to SECTOR groups based on symbol patterns

**Usage**:
```bash
# Default: Assign all stocks
python scripts/cache_maintenance/build_stock_metadata.py

# Rebuild: Delete sector assignments + reassign
python scripts/cache_maintenance/build_stock_metadata.py --rebuild

# Dry-run: Preview assignments
python scripts/cache_maintenance/build_stock_metadata.py --dry-run
```

**Current Behavior**:
- Assigns ~51 stocks to known sectors (tech, healthcare, financials, consumer)
- Assigns 3,649 stocks to 'unknown' sector (98.6%)
- **Sprint 60 Goal**: Reduce 'unknown' to <500 stocks (<13.5%)

**What It Creates**:
```sql
-- Assigns AAPL to information_technology sector
INSERT INTO group_memberships (group_id, symbol, metadata)
VALUES (sector_id, 'AAPL', '{"industry": "Software"}');
```

**Runtime**: ~2 seconds (3,700 stocks)

---

### 3. load_universes.py

**Purpose**: Load stock universe definitions from CSV files (NASDAQ-100, S&P 500, Dow 30, Russell 3000)

**Usage**:
```bash
# Full load (TRUNCATE + INSERT)
python scripts/cache_maintenance/load_universes.py --mode full

# Incremental load (UPSERT only changed)
python scripts/cache_maintenance/load_universes.py --mode incremental

# Dry-run (preview)
python scripts/cache_maintenance/load_universes.py --mode dry-run
```

**What It Creates**:
```sql
-- Creates UNIVERSE definition_groups entries
INSERT INTO definition_groups (name, type, description, environment)
VALUES ('nasdaq100', 'UNIVERSE', 'NASDAQ-100 Index - 100 largest non-financial companies on NASDAQ', 'DEFAULT');

-- Creates group_memberships entries
INSERT INTO group_memberships (group_id, symbol)
VALUES (universe_id, 'AAPL'), (universe_id, 'MSFT'), ...;
```

**Universes Loaded**:
- nasdaq100: 102 stocks
- sp500: 505 stocks
- dow30: 30 stocks
- russell3000: 3,000 stocks

**Runtime**: ~3 seconds (4 universes, 3,637 relationships)

---

### 4. enrich_sectors.py

**Purpose**: Enrich stock sector classifications using sector ETF holdings data

**Usage**:
```bash
# Full enrichment
python scripts/cache_maintenance/enrich_sectors.py --mode full

# Incremental enrichment
python scripts/cache_maintenance/enrich_sectors.py --mode incremental

# Dry-run (preview)
python scripts/cache_maintenance/enrich_sectors.py --mode dry-run
```

**What It Does**:
1. Loads 11 sector ETF holdings (XLK, XLF, XLV, etc.)
2. Maps sector ETFs to GICS sectors
3. Assigns stocks to sectors based on ETF membership
4. Updates group_memberships for sector groups

**Results**:
- Before: 1.38% sector coverage (51 classified, 3,649 unknown)
- After: 13.41% sector coverage (549 classified, 3,208 unknown)
- Improvement: +446 stocks classified

**Runtime**: ~2 seconds (11 sector ETFs, 446 updates)

---

### 5. generate_report.py

**Purpose**: Generate data quality reports with summary/detail views

**Usage**:
```bash
# Summary report (console)
python scripts/cache_maintenance/generate_report.py --summary

# Detailed report (console)
python scripts/cache_maintenance/generate_report.py --detail

# Markdown report
python scripts/cache_maintenance/generate_report.py --detail --format markdown --output scripts/cache_maintenance/relationship_report.md

# JSON report
python scripts/cache_maintenance/generate_report.py --format json --output scripts/cache_maintenance/relationship_report.json
```

**Report Sections**:
1. **Summary Statistics**: Total ETFs, stocks, sectors, themes, universes, relationships
2. **Sector Distribution**: Stock count per sector with percentages
3. **Data Quality Metrics**: ETF holdings coverage, sector coverage, bidirectional integrity
4. **Detail View** (if --detail): ETF breakdowns with top 10 holdings, universe details

**Output Formats**:
- **console**: Formatted ASCII tables (default)
- **markdown**: GitHub-flavored markdown with tables
- **json**: Machine-readable JSON structure

**Runtime**: <1 second

---

### 6. organize_sectors_industries.py

**Purpose**: Create SECTOR group definitions (11 GICS sectors)

**Usage**:
```bash
# Create sectors (run once or when updating sector definitions)
python scripts/cache_maintenance/organize_sectors_industries.py

# Dry-run
python scripts/cache_maintenance/organize_sectors_industries.py --dry-run
```

**What It Creates**:
```sql
-- Creates 11 standard GICS sectors + 1 unknown
INSERT INTO definition_groups (name, type, description, metadata)
VALUES
  ('information_technology', 'SECTOR', 'Information Technology', ...),
  ('health_care', 'SECTOR', 'Health Care', ...),
  ('financials', 'SECTOR', 'Financials', ...),
  ...
  ('unknown', 'SECTOR', 'Unclassified Stocks', ...);
```

**Runtime**: <1 second (12 sectors)

---

### 7. organize_universe.py

**Purpose**: Create THEME group definitions

**Usage**:
```bash
# Create themes
python scripts/cache_maintenance/organize_universe.py

# Dry-run
python scripts/cache_maintenance/organize_universe.py --dry-run
```

**Themes Created** (20 total):
- crypto_miners (9 stocks)
- ev_manufacturers
- semiconductor_equipment
- cloud_infrastructure
- cybersecurity
- ... (15 more themes)

**Runtime**: ~1 second (20 themes)

---

### 8. validate_relationships.py

**Purpose**: Comprehensive data integrity validation

**Usage**:
```bash
# Run all validations
python scripts/cache_maintenance/validate_relationships.py

# Verbose output
python scripts/cache_maintenance/validate_relationships.py --verbose
```

**Validation Checks**:
1. ETF Holdings (no empty ETFs)
2. Stock Metadata (no orphan stocks)
3. Bidirectional Integrity (ETF ↔ stock consistency)
4. Sector Mappings (valid sector count)
5. Theme Definitions (no empty themes)

**Output**:
```
[1/5] Validating ETF holdings...       ✓ PASS (24 ETFs, 0 empty)
[2/5] Validating stock-to-sector...    ✓ PASS (3,700 stocks, 0 orphans)
[3/5] Validating bidirectional...      ✓ PASS (100% integrity)
[4/5] Validating sector mappings...    ⚠ WARN (12/11 sectors)
[5/5] Validating theme definitions...  ✓ PASS (20 themes, 0 empty)

Overall Status:     ✓ PASS (4/5 passed, 1 warning)
```

**Runtime**: ~1 second

---

### 9. query_relationships.py

**Purpose**: Query helper for relationship data

**Usage**:
```bash
# Stock info (all relationships)
python scripts/cache_maintenance/query_relationships.py --stock AAPL

# ETF holdings
python scripts/cache_maintenance/query_relationships.py --etf SPY

# Sector members
python scripts/cache_maintenance/query_relationships.py --sector information_technology

# Theme members
python scripts/cache_maintenance/query_relationships.py --theme crypto_miners

# Summary statistics
python scripts/cache_maintenance/query_relationships.py --stats

# JSON output
python scripts/cache_maintenance/query_relationships.py --stock AAPL --json
```

**Example Output** (--stock AAPL):
```
Stock: AAPL - AAPL
Sector: information_technology
Industry: Software

Member of 10 ETFs:
  - DIA
  - IWB
  - IWV
  - QQQ
  - SCHG
  - SPY
  - VOO
  - VTI
  - VUG
  - XLK
```

---

## Maintenance Workflows

### Workflow 1: Weekly ETF Holdings Update

**Frequency**: Weekly (every Monday)
**Duration**: 3 minutes
**Data Source**: Download fresh CSV files from data provider

```bash
# Step 1: Download latest CSV files
# Place in: scripts/cache_maintenance/holdings/

# Step 2: Backup current data (optional but recommended)
pg_dump -h localhost -U app_readwrite -d tickstock -t definition_groups -t group_memberships > backup_$(date +%Y%m%d).sql

# Step 3: Load ETF holdings (incremental - only changed ETFs)
python scripts/cache_maintenance/load_etf_holdings.py --mode incremental

# Step 4: Update universes (incremental)
python scripts/cache_maintenance/load_universes.py --mode incremental

# Step 5: Re-enrich sectors (picks up new stocks)
python scripts/cache_maintenance/enrich_sectors.py --mode incremental

# Step 6: Validate
python scripts/cache_maintenance/validate_relationships.py

# Step 7: Refresh runtime cache
curl -X POST http://localhost:5000/admin/cache/refresh -H "Content-Type: application/json" -d '{"warm": true}'

# Step 8: Generate report
python scripts/cache_maintenance/generate_report.py --summary
python scripts/cache_maintenance/generate_report.py --detail --format markdown --output scripts/cache_maintenance/weekly_$(date +%Y%m%d).md
```

**Expected Changes**:
- New stocks added to ETFs
- Removed stocks deleted
- Weight adjustments
- ~10-50 stocks added/removed per week
- Sector coverage may improve

---

### Workflow 2: Monthly Comprehensive Refresh

**Frequency**: Monthly (1st of month)
**Duration**: 8 minutes
**Purpose**: Full data refresh + quality check

```bash
# Step 1: Backup database
pg_dump -h localhost -U app_readwrite -d tickstock > backup_monthly_$(date +%Y%m%d).sql

# Step 2: Full reload - ETF Holdings
python scripts/cache_maintenance/load_etf_holdings.py --mode full

# Step 3: Full reload - Universes
python scripts/cache_maintenance/load_universes.py --mode full

# Step 4: Full reload - Sector Enrichment
python scripts/cache_maintenance/enrich_sectors.py --mode full

# Step 5: Comprehensive validation
python scripts/cache_maintenance/validate_relationships.py --verbose

# Step 6: Warm runtime cache
curl -X POST http://localhost:5000/admin/cache/warm

# Step 7: Generate monthly reports
python scripts/cache_maintenance/generate_report.py --summary
python scripts/cache_maintenance/generate_report.py --detail --format markdown --output scripts/cache_maintenance/monthly_$(date +%Y%m%d).md
python scripts/cache_maintenance/generate_report.py --format json --output scripts/cache_maintenance/monthly_$(date +%Y%m%d).json

# Step 8: Review data quality
python scripts/cache_maintenance/query_relationships.py --stats
```

---

### Workflow 3: Sector Enrichment Update

**Frequency**: As needed (when sector ETF holdings updated)
**Duration**: 2 minutes
**Purpose**: Improve sector classification coverage

```bash
# Step 1: Update sector ETF holdings CSVs (XLK, XLF, XLV, etc.)
# Files: scripts/cache_maintenance/holdings/{xlk,xlf,xlv,xle,xli,xly,xlp,xlu,xlb,xlre,xlc}_holdings.csv

# Step 2: Dry-run to preview changes
python scripts/cache_maintenance/enrich_sectors.py --mode dry-run

# Step 3: Apply sector enrichment
python scripts/cache_maintenance/enrich_sectors.py --mode full

# Step 4: Validate
python scripts/cache_maintenance/validate_relationships.py

# Step 5: Check improvement
python scripts/cache_maintenance/query_relationships.py --stats
python scripts/cache_maintenance/generate_report.py --summary
# Look for improved sector coverage percentage

# Step 6: Refresh cache
curl -X POST http://localhost:5000/admin/cache/refresh -d '{"warm": true}'
```

**Current Coverage**: 13.41% (549 classified, 3,208 unknown)
**Limitation**: Sector ETFs only contain large-cap stocks (~500 total)
**Future**: External API integration for full coverage

---

### Workflow 4: Emergency Rollback

**When**: Data corruption or critical errors
**Duration**: 2 minutes

```bash
# Option 1: Restore from backup
psql -h localhost -U app_readwrite -d tickstock < backup_YYYYMMDD.sql

# Option 2: Revert scripts to previous version
git checkout feature/sprint59-relational-migration -- scripts/cache_maintenance/
python scripts/cache_maintenance/load_etf_holdings.py --rebuild

# Step 3: Validate
python scripts/cache_maintenance/validate_relationships.py

# Step 4: Restart services
# Restart TickStockAppV2 and TickStockPL
```

---

## Database Schema

### Tables Overview

**definition_groups** - Group definitions
```sql
CREATE TABLE definition_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'ETF', 'THEME', 'SECTOR', 'UNIVERSE'
    description TEXT,
    metadata JSONB,
    environment VARCHAR(10) DEFAULT 'DEFAULT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, type, environment)
);
```

**group_memberships** - Symbol membership
```sql
CREATE TABLE group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, symbol)
);
```

### Common Queries

**Get ETF holdings**:
```sql
SELECT gm.symbol
FROM group_memberships gm
JOIN definition_groups dg ON gm.group_id = dg.id
WHERE dg.name = 'SPY' AND dg.type = 'ETF' AND dg.environment = 'DEFAULT'
ORDER BY gm.symbol;
```

**Get stock's ETF memberships**:
```sql
SELECT dg.name
FROM group_memberships gm
JOIN definition_groups dg ON gm.group_id = dg.id
WHERE gm.symbol = 'AAPL' AND dg.type = 'ETF'
ORDER BY dg.name;
```

**Get sector distribution**:
```sql
SELECT dg.name, COUNT(DISTINCT gm.symbol)
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.type = 'SECTOR' AND dg.environment = 'DEFAULT'
GROUP BY dg.name
ORDER BY count DESC;
```

---

## Troubleshooting

### Problem: "No SECTOR group found for 'unknown'"

**Error**:
```
WARNING - No SECTOR group found for 'unknown', skipping AAPL
```

**Cause**: Missing 'unknown' sector group

**Fix**:
```sql
INSERT INTO definition_groups (name, type, description, metadata, environment)
VALUES ('unknown', 'SECTOR', 'Unclassified Stocks', '{"industries": ["Unknown"]}'::jsonb, 'DEFAULT');
```

**Or run**:
```bash
python scripts/cache_maintenance/organize_sectors_industries.py
```

---

### Problem: Duplicate key errors

**Error**:
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
```

**Cause**: Trying to insert existing ETF/stock combination

**Fix**: Use `--rebuild` flag
```bash
python scripts/cache_maintenance/load_etf_holdings.py --rebuild
```

---

### Problem: Low sector coverage (98% unknown)

**Issue**: 3,649 of 3,700 stocks in 'unknown' sector

**Cause**: Hardcoded sector mapping only covers ~50 stocks

**Fix**: Wait for Sprint 60 Phase 1.3 (Sector Enrichment)
- Manual CSV mapping, OR
- API integration (Massive API, Yahoo Finance, etc.)

**Workaround**: Manually update sector assignments
```sql
UPDATE group_memberships gm
SET metadata = jsonb_set(metadata, '{industry}', '"Banking"')
FROM definition_groups dg
WHERE gm.group_id = dg.id
  AND dg.name = 'financials' AND dg.type = 'SECTOR'
  AND gm.symbol IN ('JPM', 'BAC', 'WFC', 'C');
```

---

### Problem: CSV file not found

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'holdings/spy_holdings.csv'
```

**Fix**:
1. Verify file exists: `ls scripts/cache_maintenance/holdings/spy_holdings.csv`
2. Check filename (lowercase): `spy_holdings.csv` not `SPY_holdings.csv`
3. Ensure correct working directory: `cd C:\Users\McDude\TickStockAppV2`

---

### Problem: Database connection failed

**Error**:
```
psycopg2.OperationalError: could not connect to server
```

**Fix**:
1. Verify database is running: `psql -U postgres -d tickstock -c "SELECT 1;"`
2. Check `.env` file for DATABASE_URI
3. Test connection:
   ```bash
   python -c "from src.core.services.config_manager import get_config; print(get_config().get('DATABASE_URI'))"
   ```

---

## Sprint 60 Status

### ✅ COMPLETE - All Phases Delivered

**Phase 1: Data Loading Procedures**
- ✅ load_etf_holdings.py - Smart update logic with --mode flags
- ✅ load_universes.py - Universe loading (NASDAQ-100, S&P 500, Dow 30, Russell 3000)
- ✅ enrich_sectors.py - Sector enrichment using sector ETFs
- ✅ Change detection with MD5 checksums
- ✅ Validation gates (pre-load + post-load)

**Phase 2: Runtime Caching Layer**
- ✅ RelationshipCache service (<1ms access times)
- ✅ Cache management API endpoints (/admin/cache/stats, /refresh, /warm, /test)
- ✅ Thread-safe singleton pattern
- ✅ TTL-based cache expiration
- ✅ Cache statistics tracking

**Phase 3: Data Quality Reporting**
- ✅ generate_report.py - Summary & detail views
- ✅ Multiple output formats (console, markdown, JSON)
- ✅ Sector distribution analysis
- ✅ Data quality metrics (coverage, integrity)
- ✅ <1 second report generation

**Phase 4: Documentation**
- ✅ Updated README.md (this file)
- ✅ Updated CLAUDE.md with Sprint 60 status
- ✅ Cache usage examples
- ✅ Maintenance workflow documentation

**Performance Achieved**:
- Database query: 37ms → 0.01ms (3,700x improvement on cache hit)
- Sector coverage: 1.38% → 13.41% (+446 stocks)
- Total relationships: 15,834
- Report generation: <1 second

---

## Support

**Questions or Issues?**
1. Review this README
2. Check Sprint 60 plan: `docs/planning/sprints/sprint60/SPRINT60_PLAN.md`
3. Run validation: `python scripts/cache_maintenance/validate_relationships.py`
4. Check CLAUDE.md for project guidelines

---

**Last Updated**: December 21, 2025 (Sprint 60 COMPLETE)
**Status**: All 4 phases delivered and documented
