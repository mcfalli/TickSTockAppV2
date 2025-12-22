# Sprint 58: Implementation Checklist
## ETF-Stock Relationship Management & Thematic Organization

**Track your progress through implementation**

---

## Pre-Implementation

### Environment Preparation
- [ ] Review Sprint 58 README.md
- [ ] Review Sprint 57 completion (prerequisite)
- [ ] Backup database: `pg_dump tickstock > backup_sprint58.sql`
- [ ] Create feature branch: `git checkout -b feature/sprint58-etf-stock-relationships`
- [ ] Create `scripts/cache_maintenance/holdings/` directory
- [ ] Python environment activated

### Data Collection Phase
- [ ] Download SPY holdings CSV
- [ ] Download QQQ holdings CSV
- [ ] Download IWM holdings CSV
- [ ] Download VOO holdings CSV
- [ ] Download VTI holdings CSV
- [ ] Download sector ETF holdings (XLF, XLK, XLV, XLE, XLI, XLP, XLY, XLU, XLB, XLC, XLRE)
- [ ] Download international ETF holdings (VEA, VWO, IEFA, EEM)
- [ ] Verify CSV format consistency
- [ ] Document data sources and dates

---

## Phase 1: ETF Holdings Extraction (Day 1-2)

### Script Creation
- [ ] Create `scripts/cache_maintenance/load_etf_holdings.py`
- [ ] Implement `ETFHoldingsLoader` class
- [ ] Add CSV format detection (handle different providers)
- [ ] Implement market cap filtering
- [ ] Add data validation (symbol format, required fields)
- [ ] Implement cache_entries insertion for `etf_holdings` type

### CSV Parsing
- [ ] Parse iShares format (SPY, IWM, IWV)
- [ ] Parse Vanguard format (VOO, VTI, VEA, VWO)
- [ ] Parse SPDR format (sector ETFs: XLF, XLK, etc.)
- [ ] Handle missing/null values gracefully
- [ ] Extract: symbol, market cap, sector, weight

### Market Cap Filtering
- [ ] Define threshold constants:
  - [ ] Core index: $5B
  - [ ] Broad market: $1B
  - [ ] Small cap: $300M
- [ ] Apply threshold per ETF type
- [ ] Log filtered stocks (below threshold)
- [ ] Validate filtered results

### Database Operations
- [ ] Create upsert logic for `etf_holdings` type
- [ ] Handle unique constraint (type, name, key, environment)
- [ ] Add timestamp tracking (created_at, updated_at)
- [ ] Implement rollback on error

### Testing
- [ ] Unit test: CSV parsing for each format
- [ ] Unit test: Market cap filtering
- [ ] Integration test: Load SPY holdings (dry-run)
- [ ] Integration test: Load all major ETFs
- [ ] Validate symbol counts match source data
- [ ] Check for duplicate symbols within ETF

### Validation
- [ ] Query loaded ETF holdings: `SELECT * FROM cache_entries WHERE type = 'etf_holdings'`
- [ ] Verify symbol counts: SPY (~503), QQQ (~103), IWM (~2000+)
- [ ] Check JSON structure validity
- [ ] Verify market cap threshold applied

---

## Phase 2: Stock Metadata & Relationships (Day 2-3)

### Script Creation
- [ ] Create `scripts/cache_maintenance/build_stock_metadata.py`
- [ ] Implement `StockMetadataBuilder` class
- [ ] Add method: `collect_all_stocks_from_etfs()`
- [ ] Add method: `enrich_with_metadata()`
- [ ] Add method: `build_etf_membership_map()`
- [ ] Add method: `create_stock_metadata_entries()`

### Stock Collection
- [ ] Aggregate unique stocks from all ETF holdings
- [ ] Remove duplicates
- [ ] Sort alphabetically
- [ ] Log total unique stock count (expect 3,000-4,000)

### Metadata Enrichment
- [ ] Add sector classification (11 GICS sectors)
- [ ] Add industry classification (detailed)
- [ ] Add market cap data
- [ ] Add company name
- [ ] Source metadata from existing CSV files or external API

### ETF Membership Mapping
- [ ] Build reverse index: stock → [list of ETFs]
- [ ] For each stock, find all ETFs containing it
- [ ] Store in `member_of_etfs` array
- [ ] Example: AAPL → ["SPY", "QQQ", "VOO", "VTI", etc.]

### Theme Membership (Initial)
- [ ] Identify stocks in custom themes
- [ ] Add `member_of_themes` array
- [ ] Link to theme_definition keys

### Database Operations
- [ ] Create upsert logic for `stock_metadata` type
- [ ] Insert all stock metadata entries
- [ ] Handle errors gracefully
- [ ] Commit in batches (500 stocks per batch)

### Validation Rules
- [ ] Ensure every stock belongs to at least one ETF
- [ ] Verify no orphan stocks
- [ ] Check all stocks have sector assignment
- [ ] Validate market cap > 0
- [ ] Verify `member_of_etfs` array not empty

### Testing
- [ ] Unit test: Stock collection from ETF holdings
- [ ] Unit test: Metadata enrichment
- [ ] Unit test: Reverse mapping (stock → ETFs)
- [ ] Integration test: Build metadata for 100 sample stocks
- [ ] Integration test: Full metadata build (all stocks)

### Validation Queries
- [ ] Count total stocks: `SELECT COUNT(*) FROM cache_entries WHERE type = 'stock_metadata'`
- [ ] Check AAPL metadata: `SELECT * FROM cache_entries WHERE type = 'stock_metadata' AND key = 'AAPL'`
- [ ] Find stocks with no ETF membership (should be 0)
- [ ] Verify sector distribution (all 11 sectors represented)

---

## Phase 3: Sector & Industry Hierarchies (Day 3)

### Script Creation
- [ ] Create `scripts/cache_maintenance/organize_sectors_industries.py`
- [ ] Implement `SectorIndustryOrganizer` class
- [ ] Define GICS sector hierarchy
- [ ] Map industries to sectors
- [ ] Create sector-to-stocks mappings

### Sector Definitions
Define 11 GICS sectors:
- [ ] Information Technology
- [ ] Health Care
- [ ] Financials
- [ ] Consumer Discretionary
- [ ] Communication Services
- [ ] Industrials
- [ ] Consumer Staples
- [ ] Energy
- [ ] Utilities
- [ ] Real Estate
- [ ] Materials

### Industry Mappings
- [ ] Define 50+ industries within sectors
- [ ] Map each industry to parent sector
- [ ] Example: "Semiconductors" → "Information Technology"
- [ ] Include representative stocks for each industry

### Database Operations
- [ ] Create `sector_industry_map` cache entries
- [ ] One entry per sector (11 entries)
- [ ] Include industry list in value JSON
- [ ] Add stock count per sector
- [ ] Add representative stocks (top 5 per sector)

### Validation
- [ ] Verify 11 sector entries created
- [ ] Check industry count per sector (5-10 industries per sector)
- [ ] Validate stock assignments match stock_metadata
- [ ] Query sector distribution: stock counts per sector

### Testing
- [ ] Unit test: Sector hierarchy definition
- [ ] Unit test: Industry to sector mapping
- [ ] Integration test: Create all sector entries
- [ ] Validation: Query stocks by sector

---

## Phase 4: Custom Theme Definitions (Day 3-4)

### Theme Identification
Define custom themes:
- [ ] Crypto Miners (Bitcoin mining companies)
- [ ] Robotics & Automation
- [ ] Drones & UAVs
- [ ] Gold Miners
- [ ] Silver Miners
- [ ] Space Technology
- [ ] Clean Energy (Solar, Wind)
- [ ] Battery & Energy Storage
- [ ] AI & Machine Learning
- [ ] Quantum Computing
- [ ] Genomics & Biotech
- [ ] Cloud Computing
- [ ] Cybersecurity
- [ ] 5G Infrastructure
- [ ] Electric Vehicles
- [ ] Autonomous Vehicles
- [ ] Water Technology
- [ ] Agriculture Technology
- [ ] Nuclear Energy
- [ ] Rare Earth Minerals

### Symbol Assignment (Inline for ≤50 symbols)
For each theme:
- [ ] Research and list member stocks
- [ ] Verify market cap threshold
- [ ] Add description and selection criteria
- [ ] Link to related themes

### CSV Files (For >50 symbols)
- [ ] Identify themes requiring CSV files
- [ ] Create CSV files in `holdings/themes/` directory
- [ ] Load CSV data into theme definitions

### Script Updates
- [ ] Update `organize_universe.py` to include theme_definition type
- [ ] Add theme definitions inline
- [ ] Implement CSV loading for large themes
- [ ] Insert into cache_entries

### Linking Themes to Stocks
- [ ] Update stock_metadata entries with `member_of_themes` array
- [ ] For each stock, identify applicable themes
- [ ] Update existing stock_metadata entries

### Database Operations
- [ ] Create `theme_definition` cache entries
- [ ] One entry per theme (20+ entries)
- [ ] Include symbol list, description, criteria
- [ ] Add last_updated timestamp

### Validation
- [ ] Verify 20+ theme entries created
- [ ] Check symbol counts per theme
- [ ] Validate stock-theme relationships bidirectional
- [ ] Query: stocks in multiple themes

### Testing
- [ ] Unit test: Theme definition creation
- [ ] Unit test: Stock-theme linking
- [ ] Integration test: Load all themes
- [ ] Validation: Query stocks by theme

---

## Phase 5: Integration & Validation (Day 4)

### Create Validation Script
- [ ] Create `scripts/cache_maintenance/validate_relationships.py`
- [ ] Implement validation checks:
  - [ ] ETF holdings completeness
  - [ ] Stock metadata consistency
  - [ ] Sector/industry mappings
  - [ ] Theme definitions
  - [ ] Bidirectional relationships

### Validation Checks

**ETF Holdings:**
- [ ] All tracked ETFs have holdings entries
- [ ] Symbol counts match source data
- [ ] No null/empty holdings arrays
- [ ] Market cap filtering applied correctly

**Stock Metadata:**
- [ ] All stocks have metadata entries
- [ ] No orphan stocks (all belong to ≥1 ETF)
- [ ] All have sector/industry assignments
- [ ] All have market cap > 0
- [ ] `member_of_etfs` arrays not empty

**Sector/Industry:**
- [ ] All 11 sectors defined
- [ ] All industries mapped to sectors
- [ ] Stock counts per sector > 0
- [ ] No stocks without sector assignment

**Themes:**
- [ ] All themes defined
- [ ] Symbol lists not empty
- [ ] Stock-theme relationships bidirectional
- [ ] No orphan theme references

**Bidirectional Relationships:**
- [ ] ETF → stocks: holdings list matches reality
- [ ] Stock → ETFs: membership list accurate
- [ ] Stock → themes: membership list accurate
- [ ] Theme → stocks: symbol list accurate

### Create Query Helper Script
- [ ] Create `scripts/cache_maintenance/query_relationships.py`
- [ ] Implement helper functions:
  - [ ] `get_etf_holdings(etf_symbol)`
  - [ ] `get_stock_etfs(stock_symbol)`
  - [ ] `get_stocks_by_sector(sector_name)`
  - [ ] `get_stocks_by_industry(industry_name)`
  - [ ] `get_stocks_by_theme(theme_key)`
  - [ ] `get_stock_metadata(stock_symbol)`

### Testing Query Helper
- [ ] Test: Get SPY holdings (expect 503 stocks)
- [ ] Test: Get AAPL ETF memberships (expect 10+ ETFs)
- [ ] Test: Get tech sector stocks (expect 400+ stocks)
- [ ] Test: Get crypto miner theme (expect 9 stocks)
- [ ] Test: Get stock full metadata (AAPL)

### Generate Validation Report
- [ ] Total ETFs loaded: ____ / 20+ target
- [ ] Total stocks with metadata: ____ / 3,000+ target
- [ ] Total sectors defined: ____ / 11 target
- [ ] Total themes defined: ____ / 20+ target
- [ ] Orphan stocks: ____ / 0 target
- [ ] Bidirectional relationship integrity: ____%

### Documentation
- [ ] Document cache_entries schema for new types
- [ ] Create query examples document
- [ ] Update `scripts/cache_maintenance/README.md`
- [ ] Add relationship diagram
- [ ] Document maintenance procedures

---

## Testing Checklist

### Unit Tests
- [ ] CSV parsing (multiple formats)
- [ ] Market cap filtering
- [ ] Stock aggregation from ETFs
- [ ] Metadata enrichment
- [ ] Reverse mapping (stock → ETFs)
- [ ] Sector/industry hierarchy
- [ ] Theme definition creation

### Integration Tests
- [ ] Load ETF holdings (single ETF)
- [ ] Load all ETF holdings (20+ ETFs)
- [ ] Build stock metadata (all stocks)
- [ ] Create sector/industry maps
- [ ] Create theme definitions
- [ ] Validate bidirectional relationships

### Performance Tests
- [ ] Query ETF holdings: <10ms
- [ ] Query stock's ETFs: <10ms
- [ ] Filter by sector: <50ms
- [ ] Theme member lookup: <5ms

### Data Quality Tests
- [ ] No orphan stocks
- [ ] No null sectors
- [ ] No empty ETF membership arrays
- [ ] Market cap thresholds enforced
- [ ] Symbol format validation

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Validation report shows 100% coverage
- [ ] Database backup completed
- [ ] Rollback plan documented

### Deployment Steps
1. [ ] Run ETF holdings loader: `python load_etf_holdings.py`
2. [ ] Run stock metadata builder: `python build_stock_metadata.py`
3. [ ] Run sector/industry organizer: `python organize_sectors_industries.py`
4. [ ] Update universe organizer with themes: `python organize_universe.py`
5. [ ] Run validation: `python validate_relationships.py`

### Post-Deployment Verification
- [ ] Query cache_entries counts:
  - [ ] `SELECT COUNT(*) FROM cache_entries WHERE type = 'etf_holdings'` (expect 20+)
  - [ ] `SELECT COUNT(*) FROM cache_entries WHERE type = 'stock_metadata'` (expect 3,000+)
  - [ ] `SELECT COUNT(*) FROM cache_entries WHERE type = 'sector_industry_map'` (expect 11)
  - [ ] `SELECT COUNT(*) FROM cache_entries WHERE type = 'theme_definition'` (expect 20+)
- [ ] Run sample queries (ETF holdings, stock memberships)
- [ ] Check for errors in logs
- [ ] Verify no orphan stocks

### Monitoring (24 hours)
- [ ] Monitor database performance
- [ ] Check query response times
- [ ] Verify data integrity
- [ ] Track any errors or inconsistencies

---

## Success Criteria Verification

### Must Pass (MANDATORY)
- [ ] ✅ 20+ ETF holdings loaded with complete data
- [ ] ✅ 3,000+ stock metadata entries with sector/industry
- [ ] ✅ 100% stocks belong to at least one ETF (0 orphans)
- [ ] ✅ 11 sector classifications complete
- [ ] ✅ 20+ custom theme definitions
- [ ] ✅ Bidirectional relationships working (ETF ↔ stock)
- [ ] ✅ Market cap filtering enforced
- [ ] ✅ All queries return expected results
- [ ] ✅ No regression in Sprint 57 functionality

### Performance Verification
- [ ] ✅ Query ETF holdings: <10ms
- [ ] ✅ Find stock's ETFs: <10ms
- [ ] ✅ Filter by sector: <50ms
- [ ] ✅ Theme member lookup: <5ms

### Data Quality Verification
- [ ] ✅ No orphan stocks in database
- [ ] ✅ All stocks have valid sectors
- [ ] ✅ All stocks have ≥1 ETF membership
- [ ] ✅ Market cap data present for all stocks
- [ ] ✅ Bidirectional integrity: 100%

---

## Rollback Procedures

### If Critical Issues Arise

**Quick Rollback (Feature Flag)**:
- [ ] Set environment variable: `USE_SPRINT58_FEATURES=false`
- [ ] Restart services
- [ ] Verify Sprint 57 functionality intact

**Full Rollback (Database)**:
- [ ] Restore from backup: `psql tickstock < backup_sprint58.sql`
- [ ] Delete new cache entry types:
  ```sql
  DELETE FROM cache_entries WHERE type IN ('etf_holdings', 'stock_metadata', 'sector_industry_map', 'theme_definition');
  ```
- [ ] Verify Sprint 57 entries intact

---

## Issues Log

**Document any problems encountered:**

| Issue | Component | Resolution | Date |
|-------|-----------|------------|------|
|  |  |  |  |
|  |  |  |  |

---

## Sprint Completion

**Sprint Status**: ☐ In Progress  ☐ Complete  ☐ Blocked

**Completion Date**: _________________

**Completed By**: _________________

**Final Notes**:
```
[Add any final observations, lessons learned, or follow-up items]




```

---

**Definition of Done**: All checkboxes marked, all tests passing, 20+ ETF holdings loaded, 3,000+ stock metadata entries, 0 orphan stocks, bidirectional relationships working, no regressions.

