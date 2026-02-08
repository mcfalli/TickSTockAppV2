# Database Schema Documentation

## Stock Grouping System Overview

**TL;DR**: `definition_groups` and `group_memberships` are TickStock's **stock organization backbone**. They power universe loading, sector analysis, ETF tracking, and theme-based groupings across the entire platform.

### What These Tables Do

These two tables form a **many-to-many relationship system** that enables TickStock to:

1. **Universe Loading** - Subscribe to all 504 stocks in SPY with a single universe key (`SPY`)
2. **Sector Analysis** - Track which stocks belong to each GICS sector (e.g., `information_technology`)
3. **Theme Tracking** - Group stocks by investment themes (e.g., `crypto_miners`, `ev_manufacturers`)
4. **ETF Holdings** - Know exactly which stocks are in QQQ, SPY, IWM, etc.
5. **Multi-Dimensional Classification** - One stock can belong to multiple groups simultaneously:
   - **AAPL** belongs to: SPY (ETF), QQQ (ETF), VTI (ETF), information_technology (SECTOR), ai_leaders (THEME)

### Real-World Usage Examples

**Example 1: WebSocket Universe Subscription**
```python
# Instead of hardcoding 504 symbols (brittle, manual):
symbols = ['AAPL', 'MSFT', 'NVDA', ...]  # ❌ Hard to maintain

# Use RelationshipCache backed by these tables:
from src.core.services.relationship_cache import get_relationship_cache
cache = get_relationship_cache()
symbols = cache.get_universe_symbols('SPY')  # ✅ Returns all 504 SPY holdings
# → Automatically subscribes to correct symbol set for WebSocket streaming
```

**Example 2: Sector Rotation Dashboard**
```python
# Get all tech stocks for sector analysis
tech_stocks = cache.get_sector_stocks('information_technology')  # ~70 stocks
# → Powers "Sector Rotation" dashboard with real-time sector performance
```

**Example 3: Multi-Universe Loading**
```python
# Load distinct union of multiple universes for WebSocket connections
symbols = cache.get_universe_symbols('SPY:QQQ:dow30')  # ~522 distinct symbols
# → Used in multi-connection WebSocket routing (Sprint 61)
```

**Example 4: Stock Group Reverse Lookup**
```python
# "Which ETFs hold AAPL?"
etfs = cache.get_stock_etfs('AAPL')  # Returns: ['SPY', 'QQQ', 'VTI', 'IWM', ...]
# → Powers "Stock Groups Search" feature (Sprint 65)
```

### Architecture Context

**Sprint 59 Migration** (December 2025): Replaced JSONB `cache_entries` with normalized relational tables

**Before** (JSONB approach):
```json
{
  "type": "etf_holdings",
  "name": "SPY",
  "value": ["AAPL", "MSFT", "NVDA", ...],  // 504 symbols as JSON array
  "liquidity_filter": {...}
}
```

**After** (Relational approach):
```
definition_groups: (id=1, name='SPY', type='ETF')
group_memberships: 504 rows linking group_id=1 to each symbol
```

**Why Migrate?**
- ✅ **10-50x query performance** for complex queries (indexed joins vs JSONB scans)
- ✅ **Referential integrity** via foreign keys (CASCADE deletes)
- ✅ **Bidirectional lookups** (stock→ETFs and ETF→stocks equally fast)
- ✅ **Weight tracking** per membership (ETF holding percentages)
- ✅ **Metadata flexibility** per relationship (custom JSONB per membership)

**Current Scale** (as of Sprint 65):
- **24 ETFs** tracked (SPY, QQQ, IWM, XLK, XLF, XLE, XLV, XLI, XLB, XLP, XLY, XLU, XLRE, XLC, XLK, VTI, IWM, DIA, etc.)
- **20 Investment Themes** (crypto_miners, ev_manufacturers, ai_leaders, cloud_computing, etc.)
- **11 GICS Sectors** (information_technology, financials, health_care, consumer_discretionary, etc.)
- **11,778 Total Relationships** (stock-to-group memberships)

### How They Work Together

```
definition_groups                      group_memberships
┌──────────────────────────┐          ┌──────────────────────────┐
│ id: 1                    │          │ id: 1                    │
│ name: "SPY"              │◄─────────│ group_id: 1 (FK to SPY)  │
│ type: "ETF"              │          │ symbol: "AAPL"           │
│ description: "SPDR..."   │          │ weight: 0.0650 (6.5%)    │
│ environment: "DEFAULT"   │          ├──────────────────────────┤
└──────────────────────────┘          │ id: 2                    │
                                      │ group_id: 1 (FK to SPY)  │
┌──────────────────────────┐          │ symbol: "MSFT"           │
│ id: 2                    │          │ weight: 0.0550 (5.5%)    │
│ name: "crypto_miners"    │          ├──────────────────────────┤
│ type: "THEME"            │◄─────┐   │         ... (502 more)   │
│ description: "Bitcoin"   │      │   └──────────────────────────┘
└──────────────────────────┘      │
                                  └───┬──────────────────────────┐
                                      │ id: 505                  │
                                      │ group_id: 2 (crypto)     │
                                      │ symbol: "MARA"           │
                                      │ weight: NULL             │
                                      └──────────────────────────┘
```

**Query Pattern - "Give me all stocks in SPY":**
```sql
SELECT gm.symbol, gm.weight
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'SPY' AND dg.type = 'ETF' AND dg.environment = 'DEFAULT'
ORDER BY gm.weight DESC;
-- Returns: AAPL (6.5%), MSFT (5.5%), ..., 504 total stocks
-- Performance: <5ms with indexed join
```

**Query Pattern - "Which ETFs hold AAPL?" (Reverse Lookup):**
```sql
SELECT dg.name, dg.description, gm.weight
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE gm.symbol = 'AAPL' AND dg.type = 'ETF' AND dg.environment = 'DEFAULT'
ORDER BY gm.weight DESC;
-- Returns: SPY (6.5%), QQQ (12.3%), VTI (3.2%), etc.
-- Performance: <5ms with indexed join on symbol
```

### What This Enables in TickStock

| Feature | How It Uses These Tables | Sprint |
|---------|--------------------------|--------|
| **Admin Historical Data Import** | "Load SPY" → queries group_memberships for 504 symbols → bulk import | 55 |
| **WebSocket Universe Subscriptions** | Subscribe to `nasdaq100` → fetches 102 symbols from tables | 61 |
| **Threshold Bars Dashboard** | "Show tech sector performance" → queries sector memberships → aggregates | 64 |
| **Stock Groups Search** | "Which ETFs hold NVDA?" → reverse lookup via group_memberships | 65 |
| **RelationshipCache** | <1ms cache hits for all universe/sector/ETF queries (backed by these tables) | 60 |
| **Sector Rotation Analysis** | Fetch all stocks per sector → calculate sector-level metrics | - |
| **Multi-Universe WebSocket Loading** | `SPY:QQQ:dow30` → distinct union of 3 universes → subscribe | 61 |

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Query Speed** | <5ms | Indexed joins (group_id, symbol) |
| **Cache Hit Rate** | 56%+ | Via RelationshipCache (Sprint 60) |
| **Cache Miss Query** | 37ms → 0.01ms | Database query → cache hit |
| **Data Integrity** | 100% | Foreign keys enforce referential integrity |
| **Scalability** | 11,778 relationships (current)<br>100k+ capable | Indexed for growth |
| **Relationship Count** | 24 ETFs × ~500 stocks = ~11k<br>+ themes + sectors | Validated bidirectionally |

### Data Loading Process

**How data gets into these tables:**

1. **CSV Upload** (Admin UI in TickStockAppV2):
   - Navigate to `/admin/historical-data`
   - Upload CSV with format: `symbol,name,weight` (for ETFs) or `symbol,sector,industry` (for sectors)
   - Triggers Redis job on `tickstock.jobs.data_load` channel

2. **TickStockPL Processing** (Runs in separate service):
   - Listens to Redis job channel
   - Parses CSV data
   - Inserts/updates `definition_groups` (creates ETF/THEME/SECTOR entry)
   - Inserts `group_memberships` (creates stock-to-group links)
   - Fetches OHLCV data from Massive API
   - Populates `ohlcv_hourly`, `ohlcv_daily`, `ohlcv_weekly`, `ohlcv_monthly` tables

3. **RelationshipCache Refresh** (TickStockAppV2):
   - Cache invalidation triggers on data changes
   - Next query rebuilds cache from these tables
   - Subsequent queries served from cache (<1ms)

**See:**
- `docs/planning/sprints/sprint56/SPRINT56_HISTORICAL_DATA_ENHANCEMENT.md` - Historical import process
- `scripts/cache_maintenance/load_etf_holdings.py` - ETF loading script
- `scripts/cache_maintenance/enrich_sectors.py` - Sector enrichment script

### See Also

- **[Sprint 59 Complete](../planning/sprints/sprint59/SPRINT59_COMPLETE.md)** - Migration from cache_entries to relational tables
- **[Sprint 60 Plan](../planning/sprints/sprint60/SPRINT60_PLAN.md)** - RelationshipCache implementation
- **[Sprint 61 Plan](../planning/sprints/sprint61/SPRINT61_PLAN.md)** - WebSocket universe loading integration
- **[Sprint 65 Stock Groups](../planning/sprints/sprint65/stock-groups-search.md)** - Reverse lookup feature
- **[RelationshipCache](../../src/core/services/relationship_cache.py)** - Caching layer implementation
- **[Data Table Definitions](../data/data_table_definitions.md)** - Complete database schema
- **[CLAUDE.md](../../CLAUDE.md)** - RelationshipCache usage examples

---

## Sprint 59: Relationship Tables - Technical Schema

### definition_groups

**Purpose**: Store definitions for ETFs, themes, sectors, segments, and custom groupings

**Schema**:
```sql
CREATE TABLE definition_groups (
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

**Indexes**:
- `idx_definition_groups_type` ON (type)
- `idx_definition_groups_environment` ON (environment)
- `idx_definition_groups_name` ON (name)
- `idx_definition_groups_type_env` ON (type, environment)

**Example Data**:
| id | name | type | description | environment |
|----|------|------|-------------|-------------|
| 1 | SPY | ETF | SPDR S&P 500 ETF Trust | DEFAULT |
| 2 | crypto_miners | THEME | Bitcoin & Cryptocurrency Miners | DEFAULT |
| 3 | information_technology | SECTOR | Information Technology Sector | DEFAULT |

---

### group_memberships

**Purpose**: Many-to-many relationships between groups and stock symbols

**Schema**:
```sql
CREATE TABLE group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);
```

**Indexes**:
- `idx_group_memberships_group_id` ON (group_id)
- `idx_group_memberships_symbol` ON (symbol)
- `idx_group_memberships_symbol_group` ON (symbol, group_id)

**Example Data**:
| id | group_id | symbol | weight |
|----|----------|--------|--------|
| 1 | 1 | AAPL | 0.0650 |
| 2 | 1 | MSFT | 0.0550 |
| 3 | 2 | MARA | NULL |

---

### Common Queries

#### Get ETF Holdings
```sql
SELECT gm.symbol
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'SPY'
  AND dg.type = 'ETF'
  AND dg.environment = 'DEFAULT'
ORDER BY gm.symbol;
```

#### Get Stock's ETF Memberships
```sql
SELECT dg.name
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE gm.symbol = 'AAPL'
  AND dg.type = 'ETF'
  AND dg.environment = 'DEFAULT'
ORDER BY dg.name;
```

#### Get Theme Members
```sql
SELECT gm.symbol
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.name = 'crypto_miners'
  AND dg.type = 'THEME'
  AND dg.environment = 'DEFAULT'
ORDER BY gm.symbol;
```

#### Count Stocks by Sector
```sql
SELECT
    dg.name as sector,
    COUNT(DISTINCT gm.symbol) as stock_count
FROM definition_groups dg
JOIN group_memberships gm ON dg.id = gm.group_id
WHERE dg.type = 'SECTOR'
  AND dg.environment = 'DEFAULT'
GROUP BY dg.name
ORDER BY stock_count DESC;
```

---

## Performance Notes

- All JOIN queries use indexes for optimal performance (<5ms typical)
- Foreign key CASCADE ensures automatic cleanup of orphaned memberships
- UNIQUE constraints prevent duplicate memberships
- JSONB columns allow flexible metadata storage without schema changes
