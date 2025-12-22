# Sprint 60: Production-Ready Data Management & Caching

**Start Date**: December 21, 2025
**Status**: 📋 Planning
**Goal**: Operationalize the new relational structure with repeatable maintenance, runtime caching, and quality reporting

---

## Executive Summary

Sprint 60 transforms the Sprint 59 relational migration into a production-ready system with:
- **Repeatable CSV-based maintenance** workflows
- **Runtime caching layer** for sub-millisecond access
- **Data quality reporting** with detail/summary views
- **Sector classification improvement** (reduce 'unknown' from 3,649 to <500)
- **Admin UI integration** for data management

---

## Phase 1: Data Loading Procedures (Priority: HIGH)

### 1.1 ETF Holdings Loader Enhancement

**Current State**:
- ✅ 28 ETF CSV files in `scripts/cache_maintenance/holdings/`
- ✅ load_etf_holdings.py reads CSVs and inserts to definition_groups + group_memberships
- ❌ No clear documentation on load vs. update strategy
- ❌ No change detection (always full reload)

**Objectives**:
1. **Document Load Strategy**:
   - [ ] Create `scripts/cache_maintenance/README.md` with step-by-step instructions
   - [ ] Define when to TRUNCATE (full reload) vs UPDATE (incremental)
   - [ ] Document CSV file format requirements

2. **Implement Smart Update Logic**:
   - [ ] Add `--mode` flag to load_etf_holdings.py: `full`, `incremental`, `dry-run`
   - [ ] Detect changes: Compare CSV checksum/timestamp with database metadata
   - [ ] Only reload ETFs that changed (not all 28 every time)
   - [ ] Add `last_updated` tracking in definition_groups.metadata

3. **Add Validation Gates**:
   - [ ] Pre-load validation: Verify CSV format, detect duplicates
   - [ ] Post-load validation: Run validate_relationships.py automatically
   - [ ] Rollback capability: Store pre-load snapshot for emergency rollback

**Deliverables**:
- `scripts/cache_maintenance/README.md` - Maintenance procedures
- Updated `load_etf_holdings.py` with smart update logic
- `scripts/cache_maintenance/load_all.sh` - One-command full reload

---

### 1.2 Universe Definitions Loader

**Current State**:
- ✅ 4 universe CSV files: nasdaq100.csv, sp500.csv, dow30.csv, russell3000.csv
- ❌ No loader script (currently manual?)

**Objectives**:
1. **Create Universe Loader**:
   - [ ] New script: `scripts/cache_maintenance/load_universes.py`
   - [ ] Reads CSV files, creates definition_groups (type='UNIVERSE')
   - [ ] Maps symbols to group_memberships
   - [ ] Supports --mode: full, incremental, dry-run

2. **CSV File Standards**:
   ```csv
   symbol,name,weight,sector,market_cap
   AAPL,Apple Inc.,6.5,Information Technology,3000000000000
   ```
   - [ ] Document required vs optional columns
   - [ ] Add CSV validation (schema checking)

**Deliverables**:
- `scripts/cache_maintenance/load_universes.py`
- Universe CSV format specification

---

### 1.3 Sector Classification Improvement

**Current State**:
- ❌ 3,649 / 3,700 stocks (98.6%) in 'unknown' sector
- ✅ Hardcoded mapping covers only ~50 stocks
- ❌ No external sector data source integration

**Objectives**:
1. **Sector Data Enrichment**:
   - [ ] Option A: Manual CSV mapping (sector_classifications.csv)
   - [ ] Option B: Integrate Massive API sector data (if available)
   - [ ] Option C: Use Yahoo Finance / AlphaVantage sector lookup
   - [ ] Target: <500 stocks in 'unknown' (<13.5%)

2. **Create Sector Loader**:
   - [ ] New script: `scripts/cache_maintenance/enrich_sectors.py`
   - [ ] Reads sector_classifications.csv or API
   - [ ] Updates group_memberships for SECTOR groups
   - [ ] Logs coverage improvement

**Deliverables**:
- Sector classification data source (CSV or API integration)
- `scripts/cache_maintenance/enrich_sectors.py`
- Sector coverage report (before/after)

---

## Phase 2: Runtime Caching Layer (Priority: HIGH)

### 2.1 Cache Architecture Design

**Requirements** (similar to old cache_entries pattern):
```python
# Old pattern:
cache_manager.get('etf_holdings', 'SPY')  # Returns holdings list

# New pattern:
relationship_cache.get_etf_holdings('SPY')  # Same result, different backend
relationship_cache.get_stock_sectors('AAPL')  # Returns sector info
relationship_cache.get_theme_members('crypto_miners')  # Returns symbols
```

**Objectives**:
1. **Create Cache Module**:
   - [ ] New file: `src/core/services/relationship_cache.py`
   - [ ] Class: `RelationshipCache` with methods:
     - `get_etf_holdings(etf_symbol)` → List[str]
     - `get_stock_etfs(stock_symbol)` → List[str]
     - `get_stock_sector(stock_symbol)` → Dict[str, str]
     - `get_sector_stocks(sector_key)` → List[str]
     - `get_theme_members(theme_key)` → List[str]
     - `get_all_etfs()` → List[Dict]
     - `get_all_sectors()` → List[Dict]
     - `get_all_themes()` → List[Dict]

2. **Caching Strategy**:
   - [ ] In-memory cache with TTL (default: 1 hour)
   - [ ] Cache key format: `{type}:{identifier}` (e.g., `etf:SPY`)
   - [ ] Cache population: Lazy load on first access
   - [ ] Cache invalidation: Manual refresh or TTL expiry
   - [ ] Cache warming: Optional preload of common queries

3. **Performance Targets**:
   - Cache hit: <1ms (in-memory lookup)
   - Cache miss: <10ms (database query + cache population)
   - Cache size: <50MB for 3,700 stocks + 24 ETFs + 20 themes

**Deliverables**:
- `src/core/services/relationship_cache.py`
- Unit tests: `tests/unit/services/test_relationship_cache.py`
- Performance benchmark results

---

### 2.2 Cache Integration

**Objectives**:
1. **Update Existing Code**:
   - [ ] Identify all references to old cache_entries pattern
   - [ ] Replace with RelationshipCache API calls
   - [ ] Update API endpoints to use cache layer

2. **Add Cache Management**:
   - [ ] Admin endpoint: POST `/admin/cache/refresh` - Force cache reload
   - [ ] Admin endpoint: GET `/admin/cache/stats` - Cache hit/miss stats
   - [ ] Startup cache warming (optional)

**Deliverables**:
- Updated API endpoints using RelationshipCache
- Cache management endpoints

---

## Phase 3: Data Quality Reporting (Priority: MEDIUM)

### 3.1 Relationship Breakdown Report

**Objectives**:
1. **Create Report Generator**:
   - [ ] New script: `scripts/cache_maintenance/generate_report.py`
   - [ ] Flags: `--detail` (full listing) or `--summary` (counts only)

2. **Report Sections**:
   ```
   RELATIONSHIP BREAKDOWN REPORT
   Generated: 2025-12-21 10:30:00

   ========================================
   SUMMARY
   ========================================
   Total ETFs:           24
   Total Stocks:         3,700
   Total Sectors:        12
   Total Themes:         20
   Total Universes:      4 (NEW)

   Total Relationships:  11,778
   - ETF → Stock:        11,778
   - Stock → Sector:     3,700
   - Stock → Theme:      TBD
   - Stock → Universe:   TBD

   ========================================
   SECTOR DISTRIBUTION
   ========================================
   unknown:                   3,649 (98.6%) ❌ TARGET: <500
   information_technology:    18 (0.5%)
   financials:                12 (0.3%)
   health_care:               12 (0.3%)
   consumer_discretionary:    9 (0.2%)

   ========================================
   DATA QUALITY METRICS
   ========================================
   ETF Holdings Coverage:     100% ✅ (0 empty ETFs)
   Stock Sector Coverage:     1.4% ❌ (3,649 unknown)
   Bidirectional Integrity:   100% ✅ (0 orphans)
   Theme Coverage:            0% ❌ (not loaded yet)

   ========================================
   DETAIL VIEW (--detail flag)
   ========================================
   [ETF: SPY]
   - Holdings: 504 stocks
   - Top 10: AAPL (6.5%), MSFT (5.8%), NVDA (4.2%), ...

   [ETF: VTI]
   - Holdings: 3,508 stocks
   - Top 10: AAPL (5.2%), MSFT (4.6%), ...
   ```

3. **Output Formats**:
   - [ ] Console output (default)
   - [ ] Markdown file: `reports/relationship_breakdown_YYYYMMDD.md`
   - [ ] JSON file: `reports/relationship_breakdown_YYYYMMDD.json`
   - [ ] HTML report (optional, for web viewing)

**Deliverables**:
- `scripts/cache_maintenance/generate_report.py`
- Sample reports in `docs/planning/sprints/sprint60/sample_report.md`

---

## Phase 4: Documentation & Maintenance Procedures (Priority: HIGH)

### 4.1 Maintenance Runbook

**Objectives**:
1. **Create Step-by-Step Guides**:
   - [ ] `scripts/cache_maintenance/README.md` - Overview
   - [ ] `docs/guides/data_maintenance.md` - Detailed procedures

2. **Common Workflows**:
   ```markdown
   ### Weekly ETF Holdings Update
   1. Download latest CSV files from source
   2. Place in `scripts/cache_maintenance/holdings/`
   3. Run: `python load_etf_holdings.py --mode incremental`
   4. Verify: `python validate_relationships.py`
   5. Refresh cache: `curl -X POST /admin/cache/refresh`

   ### Monthly Sector Classification Update
   1. Update `sector_classifications.csv` with new stocks
   2. Run: `python enrich_sectors.py --dry-run` (verify)
   3. Run: `python enrich_sectors.py` (apply)
   4. Check report: `python generate_report.py --summary`

   ### Emergency Rollback
   1. Restore from backup: `psql -d tickstock < backup_YYYYMMDD.sql`
   2. Restart services
   3. Verify: `python validate_relationships.py`
   ```

**Deliverables**:
- `scripts/cache_maintenance/README.md`
- `docs/guides/data_maintenance.md`

---

### 4.2 Update CLAUDE.md

**Objectives**:
- [ ] Add Sprint 60 status and completion summary
- [ ] Update database quick reference queries
- [ ] Document RelationshipCache usage patterns
- [ ] Add maintenance script references

---

## Phase 5: Admin UI Integration (Priority: MEDIUM)

### 5.1 Data Management Dashboard

**Objectives**:
1. **Create Admin Page**:
   - [ ] Route: `/admin/relationships`
   - [ ] Sections:
     - Summary statistics (ETFs, stocks, sectors, themes)
     - Recent updates (last ETF reload, sector enrichment)
     - Data quality alerts (high 'unknown' count)
     - Quick actions (refresh cache, generate report)

2. **Manual Data Management**:
   - [ ] Upload CSV files via web UI (optional)
   - [ ] Trigger loads from UI
   - [ ] View validation results
   - [ ] Download reports

**Deliverables**:
- `web/templates/admin/relationships_dashboard.html`
- `src/api/rest/admin_relationships.py`

---

## Additional Enhancements (Optional)

### 6.1 API Endpoints for Relationships

**New Endpoints**:
```python
GET /api/relationships/etf/{symbol}/holdings
GET /api/relationships/stock/{symbol}/info
GET /api/relationships/sector/{sector_key}/stocks
GET /api/relationships/theme/{theme_key}/members
GET /api/relationships/stats
```

**Objectives**:
- [ ] Create RESTful API for relationship queries
- [ ] Use RelationshipCache for sub-10ms responses
- [ ] Add pagination for large result sets
- [ ] OpenAPI/Swagger documentation

---

### 6.2 Data Quality Monitoring

**Objectives**:
1. **Automated Alerts**:
   - [ ] Daily validation check (cron job)
   - [ ] Alert if sector 'unknown' count increases
   - [ ] Alert if bidirectional integrity drops below 100%
   - [ ] Email/Slack notifications

2. **Metrics Dashboard**:
   - [ ] Track coverage metrics over time
   - [ ] Graph sector classification improvements
   - [ ] Monitor cache hit/miss rates

---

### 6.3 Performance Optimization

**Objectives**:
- [ ] Review query performance (<50ms target)
- [ ] Add database indexes if needed (already have 7)
- [ ] Optimize cache warming strategy
- [ ] Benchmark: 10,000 requests/sec target

---

## Success Criteria

### Phase 1 (Data Loading):
- [ ] ETF holdings updatable via CSV in <5 minutes
- [ ] Sector coverage improved to >85% (3,145+ stocks classified)
- [ ] Zero manual database queries needed for updates

### Phase 2 (Caching):
- [ ] Cache hit rate >90% in production
- [ ] Average response time <5ms for cached queries
- [ ] Cache memory usage <50MB

### Phase 3 (Reporting):
- [ ] Report generation <10 seconds
- [ ] Summary view shows all key metrics
- [ ] Detail view available for debugging

### Phase 4 (Documentation):
- [ ] All maintenance procedures documented
- [ ] New team member can execute loads without assistance
- [ ] CLAUDE.md updated with Sprint 60 status

### Phase 5 (UI):
- [ ] Admin dashboard shows real-time statistics
- [ ] Manual cache refresh working
- [ ] Report viewable in browser

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1.1 ETF Loader Enhancement | 4 hours | None |
| 1.2 Universe Loader | 3 hours | None |
| 1.3 Sector Enrichment | 6 hours | Data source selection |
| 2.1 Cache Architecture | 8 hours | None |
| 2.2 Cache Integration | 4 hours | 2.1 complete |
| 3.1 Report Generator | 4 hours | None |
| 4.1 Maintenance Runbook | 2 hours | All above complete |
| 4.2 Update CLAUDE.md | 1 hour | All above complete |
| 5.1 Admin UI | 6 hours | Optional |
| **Total Core** | **32 hours** | **~4 days** |
| **With UI** | **38 hours** | **~5 days** |

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sector data source unavailable | HIGH | Fallback to manual CSV mapping |
| Cache memory overhead too high | MEDIUM | Implement selective caching (hot data only) |
| Load procedures too complex | MEDIUM | Simplify to single-command execution |
| Performance regression | LOW | Benchmark before/after, rollback if needed |

---

## Post-Sprint 60

**Sprint 61 Candidates**:
- Real-time ETF holdings API integration (auto-update from data provider)
- Advanced sector classification (ML/NLP-based)
- Historical tracking of relationship changes (audit log)
- Multi-environment support (DEV/TEST/PROD data isolation)

---

**Status**: 📋 Ready for Kickoff
**Next Action**: Review plan, prioritize phases, begin Phase 1.1
