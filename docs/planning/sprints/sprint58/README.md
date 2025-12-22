# Sprint 58: ETF-Stock Relationship Management & Thematic Organization

**Quick Reference Guide**

---

## Overview

**Type**: Data Architecture & Relationship Mapping
**Priority**: HIGH
**Estimated Effort**: 3-4 days
**Prerequisites**: Sprint 57 (Cache-Based Universe Loading)

---

## What & Why

### The Vision

Sprint 58 establishes **comprehensive relationship mapping** between ETFs, stocks, sectors, industries, and custom themes in the `cache_entries` table. This creates a **single source of truth** for all symbol relationships, enabling:

- ETF holdings lookup (which stocks are in SPY?)
- Stock membership lookup (which ETFs contain AAPL?)
- Sector/industry classification
- Custom thematic groupings (crypto miners, robotics, drones, gold miners)
- Market cap filtering and validation
- **Zero orphan stocks** - only stocks that belong to tracked ETFs

### Why It Matters

**Current State (Sprint 57):**
- ✅ Universe lists for historical data loading
- ❌ No ETF-to-stock holdings data
- ❌ No bidirectional relationships (stock → ETFs)
- ❌ No sector/industry classifications
- ❌ No custom theme management

**Future State (Sprint 58):**
- ✅ Complete ETF holdings for all tracked ETFs
- ✅ Bidirectional lookups (ETF ↔ stocks)
- ✅ Sector/industry hierarchies
- ✅ Custom themes (robotics, crypto, drones, gold)
- ✅ Market cap filtering and validation
- ✅ Single source of truth in cache_entries

---

## Problem Statement

### 1. No ETF Holdings Data

**Current Issues:**
- Can't determine which stocks are in SPY, QQQ, or other ETFs
- No way to validate if a stock is part of a tracked universe
- Can't build portfolios based on ETF constituents
- No relationship between ETF universes and actual holdings

**Impact:**
- Limited analytics capabilities
- Can't correlate ETF performance with holdings
- Can't filter stocks by ETF membership

### 2. Missing Stock Metadata

**Current Issues:**
- No sector/industry classification for stocks
- No market cap data for validation
- No stock-to-ETF reverse mapping
- Can't query "which ETFs contain tech stocks?"

**Impact:**
- Limited filtering and search capabilities
- Can't build sector-based strategies
- No validation of stock quality (market cap threshold)

### 3. No Custom Theme Management

**Current Issues:**
- Theme definitions scattered (some in script, some in CSV)
- No systematic way to define custom themes
- Can't track emerging themes (AI, quantum computing, space)
- No relationship between themes and stock characteristics

**Impact:**
- Hard to maintain thematic universes
- Can't dynamically filter by themes
- Limited ability to track specialized sectors

---

## Solution Overview

### New Cache Entry Types

Sprint 58 introduces **4 new cache entry types** in `cache_entries`:

#### 1. `etf_holdings` - ETF → Stocks Mapping
```json
{
  "type": "etf_holdings",
  "key": "SPY",
  "name": "SPDR S&P 500 ETF Trust",
  "value": {
    "holdings": ["AAPL", "MSFT", "NVDA", ...],
    "total_holdings": 503,
    "market_cap_threshold": 1000000000,
    "last_updated": "2025-12-02",
    "data_source": "ishares_spy_holdings.csv"
  }
}
```

#### 2. `stock_metadata` - Stock Information + ETF Membership
```json
{
  "type": "stock_metadata",
  "key": "AAPL",
  "name": "Apple Inc.",
  "value": {
    "market_cap": 3500000000000,
    "sector": "Information Technology",
    "industry": "Consumer Electronics",
    "member_of_etfs": ["SPY", "QQQ", "VTI", "VOO"],
    "member_of_themes": ["theme_technology", "theme_mega_cap"],
    "is_validated": true
  }
}
```

#### 3. `sector_industry_map` - Hierarchical Classifications
```json
{
  "type": "sector_industry_map",
  "key": "information_technology",
  "name": "Information Technology Sector",
  "value": {
    "industries": [
      "semiconductors",
      "software",
      "hardware",
      "it_services"
    ],
    "stock_count": 450,
    "representative_stocks": ["AAPL", "MSFT", "NVDA"]
  }
}
```

#### 4. `theme_definition` - Custom Thematic Groupings
```json
{
  "type": "theme_definition",
  "key": "crypto_miners",
  "name": "Bitcoin & Cryptocurrency Miners",
  "value": {
    "description": "Companies primarily engaged in cryptocurrency mining",
    "symbols": ["MARA", "RIOT", "CLSK", "HUT", "CIFR"],
    "selection_criteria": "Primary business: Bitcoin mining, Market cap > $500M",
    "related_themes": ["theme_crypto", "theme_energy_intensive"],
    "last_updated": "2025-12-02"
  }
}
```

---

## Data Organization Strategy

### CSV vs. Inline String Rules

**Use CSV Files When:**
- ✅ Symbol count > 50
- ✅ Data changes frequently (ETF holdings)
- ✅ Data sourced from external files

**Use Inline Strings When:**
- ✅ Symbol count ≤ 50
- ✅ Curated/manual lists
- ✅ Rarely changes (custom themes)

**Examples:**

| Data Type | Symbol Count | Storage Method |
|-----------|--------------|----------------|
| SPY holdings | 503 | CSV: `spy_holdings.csv` |
| QQQ holdings | 103 | CSV: `qqq_holdings.csv` |
| Russell 3000 | 2,591 | CSV: `russell3000.csv` |
| Crypto miners | 9 | Inline: `["MARA", "RIOT", ...]` |
| Robotics theme | 15 | Inline: `["ABB", "FANUC", ...]` |
| Gold miners | 12 | Inline: `["NEM", "GOLD", ...]` |

---

## Implementation Phases

### Phase 1: ETF Holdings Extraction (Day 1-2)

**Goal:** Load ETF holdings from CSV files into `cache_entries`

**Activities:**
1. Download/collect holdings CSV files for major ETFs:
   - Core Index: SPY, QQQ, IWM, DIA, VOO, VTI
   - Sector: XLF, XLK, XLV, XLE, XLI, XLP, XLY, XLU, XLB, XLC, XLRE
   - International: VEA, VWO, IEFA, EEM
   - Thematic: ARKK, BOTZ, ICLN, etc.

2. Create script: `scripts/cache_maintenance/load_etf_holdings.py`
   - Parse CSV files (handle different formats)
   - Filter by market cap threshold
   - Insert into `cache_entries` as `etf_holdings` type

3. Validation:
   - Verify all holdings loaded correctly
   - Check symbol counts match source data
   - Validate market cap filtering

**Deliverables:**
- `load_etf_holdings.py` script
- 20-30 ETF holdings loaded into cache_entries
- Validation report

### Phase 2: Stock Metadata & Relationships (Day 2-3)

**Goal:** Build stock metadata with sector, industry, and ETF membership

**Activities:**
1. Aggregate all stocks from ETF holdings
2. Enrich with metadata:
   - Sector (11 GICS sectors)
   - Industry (detailed classifications)
   - Market cap
   - ETF membership (reverse mapping)

3. Create script: `scripts/cache_maintenance/build_stock_metadata.py`
   - Collect unique stocks from all ETF holdings
   - Query existing data sources for metadata
   - Create bidirectional ETF ↔ stock mappings
   - Insert as `stock_metadata` type

4. Validation:
   - Ensure no orphan stocks
   - Verify all stocks have sector/industry
   - Check ETF membership accuracy

**Deliverables:**
- `build_stock_metadata.py` script
- 3,000+ stock metadata entries
- Stock-to-ETF relationship map

### Phase 3: Sector & Industry Hierarchies (Day 3)

**Goal:** Create hierarchical sector/industry classifications

**Activities:**
1. Define GICS sector structure (11 sectors)
2. Map industries to sectors
3. Associate stocks with industries

4. Create script: `scripts/cache_maintenance/organize_sectors_industries.py`
   - Define sector hierarchy
   - Map stocks to industries and sectors
   - Insert as `sector_industry_map` type

**Deliverables:**
- `organize_sectors_industries.py` script
- 11 sector mappings
- 50+ industry classifications

### Phase 4: Custom Theme Definitions (Day 3-4)

**Goal:** Create and manage custom thematic groupings

**Activities:**
1. Define custom themes:
   - **Crypto Ecosystem**: Miners, exchanges, blockchain companies
   - **Robotics & Automation**: Industrial robots, AI robotics
   - **Drones & UAVs**: Drone manufacturers, autonomous vehicles
   - **Gold Miners**: Gold mining companies
   - **Space Technology**: Satellite, launch, space exploration
   - **Clean Energy**: Solar, wind, battery storage
   - **AI & Machine Learning**: Pure-play AI companies
   - **Quantum Computing**: Quantum technology companies

2. Update `organize_universe.py`:
   - Add theme_definition cache entries
   - Link themes to stocks
   - Validate theme membership

**Deliverables:**
- 20+ custom theme definitions
- Theme-to-stock relationships
- Updated universe organization script

### Phase 5: Integration & Validation (Day 4)

**Goal:** Integrate all components and validate relationships

**Activities:**
1. Create validation script: `scripts/cache_maintenance/validate_relationships.py`
   - Verify ETF holdings completeness
   - Check stock metadata consistency
   - Validate sector/industry mappings
   - Confirm theme definitions

2. Create query helper: `scripts/cache_maintenance/query_relationships.py`
   - Query ETF holdings by symbol
   - Find all ETFs containing a stock
   - Filter stocks by sector/industry
   - Search stocks by theme

3. Documentation:
   - Relationship schema documentation
   - Query examples
   - Maintenance procedures

**Deliverables:**
- Validation report (100% relationship coverage)
- Query helper script
- Complete documentation

---

## Database Schema

### New Cache Entry Types Summary

| Type | Key | Purpose | Storage |
|------|-----|---------|---------|
| `etf_holdings` | ETF symbol | ETF → stocks mapping | CSV for large, inline for small |
| `stock_metadata` | Stock symbol | Stock info + memberships | Database |
| `sector_industry_map` | Sector/industry name | Hierarchical classifications | Inline |
| `theme_definition` | Theme key | Custom thematic groups | Inline for small lists |

### Key Queries

```sql
-- Find all stocks in SPY
SELECT value->'holdings'
FROM cache_entries
WHERE type = 'etf_holdings' AND key = 'SPY';

-- Find all ETFs containing AAPL
SELECT value->'member_of_etfs'
FROM cache_entries
WHERE type = 'stock_metadata' AND key = 'AAPL';

-- Get all tech sector stocks
SELECT key
FROM cache_entries
WHERE type = 'stock_metadata'
  AND value->>'sector' = 'Information Technology';

-- Find all crypto mining stocks
SELECT value->'symbols'
FROM cache_entries
WHERE type = 'theme_definition' AND key = 'crypto_miners';

-- Count stocks per sector
SELECT
  value->>'sector' as sector,
  COUNT(*) as stock_count
FROM cache_entries
WHERE type = 'stock_metadata'
GROUP BY value->>'sector';
```

---

## Market Cap Filtering Strategy

### Threshold Levels

| ETF Type | Market Cap Threshold | Rationale |
|----------|---------------------|-----------|
| Core Index (SPY, QQQ) | $5B | Large-cap quality filter |
| Broad Market (VTI, IWV) | $1B | Standard minimum |
| Small Cap (IWM) | $300M | Small-cap appropriate |
| Micro Cap | $50M | Speculative/thematic only |

### Validation Rules

1. **All stocks MUST**:
   - Belong to at least one tracked ETF
   - Meet minimum market cap threshold
   - Have valid sector/industry classification

2. **No orphan stocks**:
   - Stock must be in at least one ETF holdings list
   - Or explicitly added to a custom theme

3. **Quality filters**:
   - Market cap > threshold
   - Valid ticker symbol
   - Active trading (not delisted)

---

## File Structure

```
TickStockAppV2/
├── scripts/cache_maintenance/
│   ├── organize_universe.py          (Sprint 57 - EXISTS)
│   ├── load_etf_holdings.py          (Sprint 58 - NEW)
│   ├── build_stock_metadata.py       (Sprint 58 - NEW)
│   ├── organize_sectors_industries.py (Sprint 58 - NEW)
│   ├── validate_relationships.py     (Sprint 58 - NEW)
│   ├── query_relationships.py        (Sprint 58 - NEW)
│   ├── holdings/                     (Sprint 58 - NEW)
│   │   ├── spy_holdings.csv
│   │   ├── qqq_holdings.csv
│   │   ├── iwm_holdings.csv
│   │   ├── xlf_holdings.csv
│   │   └── ... (30+ ETF holdings files)
│   └── README.md                     (Updated with Sprint 58 info)
```

---

## Success Criteria

### Must Pass

- ✅ 20+ ETF holdings loaded with complete data
- ✅ 3,000+ stock metadata entries with sector/industry
- ✅ 100% stocks belong to at least one ETF
- ✅ 11 sector classifications complete
- ✅ 20+ custom theme definitions
- ✅ Bidirectional relationships (ETF ↔ stock) working
- ✅ Market cap filtering enforced
- ✅ No orphan stocks in database
- ✅ All queries return expected results

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Query ETF holdings | <10ms | Single ETF lookup |
| Find stock's ETFs | <10ms | Reverse lookup |
| Filter by sector | <50ms | Aggregation query |
| Theme member lookup | <5ms | Small result set |

---

## Integration with Sprint 57

Sprint 58 **builds on** Sprint 57's foundation:

**Sprint 57 Delivered:**
- Universe lists for historical data loading
- CSV loading infrastructure
- Cache organization framework
- 38 universe entries (16 ETF, 22 stock)

**Sprint 58 Adds:**
- ETF holdings (actual constituents)
- Stock metadata (sector, industry, market cap)
- Bidirectional relationships
- Custom theme management
- Sector/industry hierarchies

**Shared Infrastructure:**
- Same `cache_entries` table
- Same `organize_universe.py` base script
- Same CSV loading patterns
- Same validation approach

---

## Risks & Mitigations

### Risk 1: ETF Holdings Data Quality
**Risk:** CSV files may have inconsistent formats or missing data
**Mitigation:**
- Create robust CSV parser with format detection
- Validate all fields before insertion
- Manual review of first 5 ETF holdings

### Risk 2: Market Cap Data Availability
**Risk:** May not have market cap data for all stocks
**Mitigation:**
- Use multiple data sources (CSV files, Yahoo Finance API)
- Set default threshold for unknowns
- Manual review of top 500 stocks

### Risk 3: Data Maintenance Overhead
**Risk:** ETF holdings change daily; keeping current is manual work
**Mitigation:**
- Quarterly refresh schedule (not daily)
- Focus on top 20 ETFs only
- Automate where possible (future sprint)

---

## Next Steps After Sprint 58

**Sprint 59: Real-time Relationship Queries** (Future)
- API endpoints for relationship lookups
- UI integration for ETF holdings display
- Dynamic filtering by sector/theme

**Sprint 60: Automated Data Refresh** (Future)
- Scheduled ETF holdings updates
- Market cap refresh automation
- Sector classification updates

---

## Related Documentation

- **Sprint 57**: Cache-Based Universe Loading
- **Cache Architecture**: `docs/architecture/cache-control.md`
- **Database Schema**: `docs/database/schema.md`

---

**Status**: Ready for Planning Review
**Created**: 2025-12-02
**Next Steps**: Review vision → Build scripts → Test → Deploy

