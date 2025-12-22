# Sprint 58: Quick Start Guide
## ETF-Stock Relationship Management

**Get started in 10 minutes**

---

## What Is This Sprint?

Sprint 58 creates **comprehensive relationship mapping** between:
- ETFs and their holdings (SPY contains which stocks?)
- Stocks and their ETF memberships (Which ETFs contain AAPL?)
- Stocks and their sectors/industries
- Stocks and custom themes (crypto miners, robotics, drones)

---

## Quick Overview

### Before Sprint 58:
```
Universe Lists Only:
- index_sp500: [432 stock symbols]
- etf_universe: [56 ETF symbols]
❌ No ETF holdings data
❌ No stock-to-ETF relationships
❌ No sector/industry data
```

### After Sprint 58:
```
Complete Relationship System:
- SPY holdings: [503 specific stocks with metadata]
- AAPL memberships: [SPY, QQQ, VOO, VTI, ...]
- Tech sector: [450 stocks]
- Crypto miners theme: [9 specific stocks]
✅ Bidirectional lookups (ETF ↔ stock)
✅ Sector/industry classifications
✅ Custom themes
```

---

## For Developers: Quick Implementation

### 1. Review Documentation (15 min)
```bash
# Start here
docs/planning/sprints/sprint58/README.md

# Then checklist
docs/planning/sprints/sprint58/IMPLEMENTATION_CHECKLIST.md
```

### 2. Create Feature Branch
```bash
cd C:\Users\McDude\TickStockAppV2
git checkout -b feature/sprint58-etf-stock-relationships
```

### 3. Set Up Holdings Directory
```bash
mkdir scripts/cache_maintenance/holdings
mkdir scripts/cache_maintenance/holdings/themes
```

### 4. Collect ETF Holdings CSV Files

**Download holdings for major ETFs:**
- **Core Index**: SPY, QQQ, IWM, VOO, VTI
- **Sector**: XLF, XLK, XLV, XLE, XLI, XLP, XLY, XLU, XLB, XLC, XLRE
- **International**: VEA, VWO, IEFA, EEM

**Sources:**
- iShares ETFs: [https://www.ishares.com](https://www.ishares.com) → Search ETF → Holdings tab → Export CSV
- Vanguard ETFs: [https://investor.vanguard.com](https://investor.vanguard.com) → Search ETF → Portfolio → Download holdings
- SPDR ETFs: [https://www.ssga.com](https://www.ssga.com) → Search ETF → Holdings → Download

**Save to:**
```
scripts/cache_maintenance/holdings/
├── spy_holdings.csv
├── qqq_holdings.csv
├── iwm_holdings.csv
├── voo_holdings.csv
└── ... (20+ files)
```

### 5. Implement Phase 1: ETF Holdings Loader

**Create:** `scripts/cache_maintenance/load_etf_holdings.py`

**Key features:**
- Parse CSV files (multiple formats)
- Filter by market cap threshold
- Insert into cache_entries as `etf_holdings` type

**Run:**
```bash
python scripts/cache_maintenance/load_etf_holdings.py --dry-run
python scripts/cache_maintenance/load_etf_holdings.py
```

### 6. Implement Phase 2: Stock Metadata Builder

**Create:** `scripts/cache_maintenance/build_stock_metadata.py`

**Key features:**
- Aggregate all stocks from ETF holdings
- Add sector/industry metadata
- Build ETF membership (reverse mapping)
- Insert as `stock_metadata` type

**Run:**
```bash
python scripts/cache_maintenance/build_stock_metadata.py --dry-run
python scripts/cache_maintenance/build_stock_metadata.py
```

### 7. Implement Phase 3: Sector/Industry Organizer

**Create:** `scripts/cache_maintenance/organize_sectors_industries.py`

**Key features:**
- Define 11 GICS sectors
- Map industries to sectors
- Create sector hierarchy
- Insert as `sector_industry_map` type

**Run:**
```bash
python scripts/cache_maintenance/organize_sectors_industries.py
```

### 8. Implement Phase 4: Custom Themes

**Update:** `scripts/cache_maintenance/organize_universe.py`

**Add theme definitions:**
- Crypto miners
- Robotics & automation
- Drones & UAVs
- Gold miners
- Space technology
- Clean energy
- AI & machine learning
- Quantum computing

**Run:**
```bash
python scripts/cache_maintenance/organize_universe.py
```

### 9. Validation & Testing

**Create:** `scripts/cache_maintenance/validate_relationships.py`

**Run validation:**
```bash
python scripts/cache_maintenance/validate_relationships.py
```

**Expected output:**
```
ETF Holdings: 20+ entries ✓
Stock Metadata: 3,000+ entries ✓
Sectors: 11 entries ✓
Themes: 20+ entries ✓
Orphan Stocks: 0 ✓
Bidirectional Integrity: 100% ✓
```

---

## For Operators: Quick Usage

### Query ETF Holdings

```sql
-- Get all stocks in SPY
SELECT value->'holdings'
FROM cache_entries
WHERE type = 'etf_holdings' AND key = 'SPY';
```

### Query Stock's ETF Memberships

```sql
-- Find which ETFs contain AAPL
SELECT value->'member_of_etfs'
FROM cache_entries
WHERE type = 'stock_metadata' AND key = 'AAPL';
```

### Query by Sector

```sql
-- Get all tech sector stocks
SELECT key, value->>'sector', value->>'industry'
FROM cache_entries
WHERE type = 'stock_metadata'
  AND value->>'sector' = 'Information Technology';
```

### Query by Theme

```sql
-- Get all crypto mining stocks
SELECT value->'symbols'
FROM cache_entries
WHERE type = 'theme_definition' AND key = 'crypto_miners';
```

### Summary Statistics

```sql
-- Count entries by type
SELECT type, COUNT(*) as count
FROM cache_entries
WHERE type IN ('etf_holdings', 'stock_metadata', 'sector_industry_map', 'theme_definition')
GROUP BY type;

-- Count stocks per sector
SELECT
  value->>'sector' as sector,
  COUNT(*) as stock_count
FROM cache_entries
WHERE type = 'stock_metadata'
GROUP BY value->>'sector'
ORDER BY stock_count DESC;

-- Count stocks per ETF
SELECT
  key as etf_symbol,
  jsonb_array_length(value->'holdings') as holding_count
FROM cache_entries
WHERE type = 'etf_holdings'
ORDER BY holding_count DESC;
```

---

## For Users: What Changed?

### New Cache Entry Types

Sprint 58 adds **4 new types** to `cache_entries`:

1. **`etf_holdings`** - ETF constituents
   - Example: SPY → [503 stocks]

2. **`stock_metadata`** - Stock information
   - Example: AAPL → {sector, industry, ETF memberships}

3. **`sector_industry_map`** - Sector hierarchies
   - Example: Tech sector → [industries, stocks]

4. **`theme_definition`** - Custom themes
   - Example: Crypto miners → [9 stocks]

### No UI Changes (Yet)

Sprint 58 is **backend-only**. UI integration comes in Sprint 59.

---

## Data Structure Examples

### ETF Holdings Entry
```json
{
  "type": "etf_holdings",
  "key": "SPY",
  "name": "SPDR S&P 500 ETF Trust",
  "value": {
    "holdings": ["AAPL", "MSFT", "NVDA", "AMZN", ...],
    "total_holdings": 503,
    "market_cap_threshold": 5000000000,
    "last_updated": "2025-12-02"
  }
}
```

### Stock Metadata Entry
```json
{
  "type": "stock_metadata",
  "key": "AAPL",
  "name": "Apple Inc.",
  "value": {
    "market_cap": 3500000000000,
    "sector": "Information Technology",
    "industry": "Consumer Electronics",
    "member_of_etfs": ["SPY", "QQQ", "VOO", "VTI"],
    "member_of_themes": ["theme_technology", "theme_mega_cap"]
  }
}
```

### Sector Map Entry
```json
{
  "type": "sector_industry_map",
  "key": "information_technology",
  "name": "Information Technology",
  "value": {
    "industries": ["semiconductors", "software", "hardware"],
    "stock_count": 450,
    "representative_stocks": ["AAPL", "MSFT", "NVDA"]
  }
}
```

### Theme Definition Entry
```json
{
  "type": "theme_definition",
  "key": "crypto_miners",
  "name": "Bitcoin & Cryptocurrency Miners",
  "value": {
    "symbols": ["MARA", "RIOT", "CLSK", "HUT", "CIFR"],
    "description": "Companies primarily engaged in cryptocurrency mining",
    "selection_criteria": "Primary business: Bitcoin mining, Market cap > $500M"
  }
}
```

---

## Common Tasks

### Add New ETF Holdings

1. Download holdings CSV
2. Save to `scripts/cache_maintenance/holdings/{etf}_holdings.csv`
3. Run: `python load_etf_holdings.py --etf {ETF_SYMBOL}`

### Add New Custom Theme

1. Edit `organize_universe.py`
2. Add theme definition:
```python
'theme_new_theme': {
    'name': 'Theme Name',
    'description': 'Theme description',
    'symbols': ['SYM1', 'SYM2', 'SYM3']
}
```
3. Run: `python organize_universe.py`

### Update Stock Metadata

1. Modify source data (ETF holdings or metadata files)
2. Run: `python build_stock_metadata.py --rebuild`

---

## Troubleshooting

### Issue: CSV parsing fails

**Fix:**
- Check CSV format matches expected structure
- Verify column headers: "Ticker", "Name", "Sector", "Market Value"
- Ensure UTF-8 encoding: `--encoding utf-8`

### Issue: Orphan stocks found

**Fix:**
```sql
-- Find orphan stocks
SELECT key
FROM cache_entries
WHERE type = 'stock_metadata'
  AND jsonb_array_length(value->'member_of_etfs') = 0;

-- Delete orphans
DELETE FROM cache_entries
WHERE type = 'stock_metadata'
  AND jsonb_array_length(value->'member_of_etfs') = 0;
```

### Issue: Bidirectional relationship broken

**Fix:**
- Run: `python validate_relationships.py --fix`
- This will rebuild ETF membership arrays for all stocks

---

## File Locations

### TickStockAppV2
```
C:\Users\McDude\TickStockAppV2\
├── docs\planning\sprints\sprint58\
│   ├── README.md                       (Overview & vision)
│   ├── IMPLEMENTATION_CHECKLIST.md     (Progress tracker)
│   └── QUICK_START.md                  (You are here)
├── scripts\cache_maintenance\
│   ├── load_etf_holdings.py            (NEW - Phase 1)
│   ├── build_stock_metadata.py         (NEW - Phase 2)
│   ├── organize_sectors_industries.py  (NEW - Phase 3)
│   ├── validate_relationships.py       (NEW - Phase 5)
│   ├── query_relationships.py          (NEW - Phase 5)
│   ├── organize_universe.py            (UPDATED - Phase 4)
│   └── holdings\
│       ├── spy_holdings.csv
│       ├── qqq_holdings.csv
│       ├── ... (20+ ETF holdings files)
│       └── themes\
│           └── ... (theme CSV files if >50 symbols)
```

---

## Success Metrics

After Sprint 58:
- ✅ 20+ ETF holdings loaded
- ✅ 3,000+ stock metadata entries
- ✅ 11 sector classifications
- ✅ 20+ custom themes
- ✅ 0 orphan stocks
- ✅ 100% bidirectional relationship integrity
- ✅ Query performance <50ms

---

## Next Sprint

**Sprint 59: Real-time Relationship Queries** (Future)
- API endpoints for relationship lookups
- UI integration for ETF holdings display
- Dynamic filtering by sector/theme
- Real-time stock-ETF correlation

---

## Support Resources

**Documentation:**
- Full guide: `docs/planning/sprints/sprint58/README.md`
- Checklist: `docs/planning/sprints/sprint58/IMPLEMENTATION_CHECKLIST.md`
- Quick start: `docs/planning/sprints/sprint58/QUICK_START.md` (this file)

**Related Sprints:**
- Sprint 57: Cache-Based Universe Loading (prerequisite)

**Project Docs:**
- CLAUDE.md: Development guidelines
- Architecture: `docs/architecture/`

---

**Estimated Time**: 3-4 days for full implementation
**Priority**: High
**Status**: Ready to start

**Questions?** Review the full README.md for detailed information.

