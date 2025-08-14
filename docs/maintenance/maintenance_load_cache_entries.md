# Cache Entries Maintenance Documentation

## Overview

The Cache Entries maintenance process loads stock data from the `stock_main` table into the `cache_entries` table for efficient application access. This two-step process ensures fresh market data is available in a pre-computed, optimized format for the TickStock application.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Data Flow](#data-flow)
3. [Scripts Overview](#scripts-overview)
4. [Cache Structure](#cache-structure)
5. [Usage Instructions](#usage-instructions)
6. [Scheduling](#scheduling)
7. [Data Categories](#data-categories)
8. [Troubleshooting](#troubleshooting)
9. [Performance Considerations](#performance-considerations)
10. [Maintenance Schedule](#maintenance-schedule)

---

## Architecture

### Two-Step Process


Step 1: Polygon.io → stock_main (maint_get_stocks.py)
           ↓
Step 2: stock_main → cache_entries (maint_load_stock_cache_entries.py)
           ↓
Application: cache_entries → TickStock UI (cached data access)


### Benefits
- **Separation of Concerns**: API fetching separate from cache generation
- **Performance**: Pre-computed aggregations for fast access
- **Reliability**: Cache can be rebuilt from stock_main without API calls
- **Flexibility**: Different cache strategies without re-fetching data

---

## Data Flow

### Complete Pipeline

mermaid
graph TD
    A[Polygon.io API] -->|maint_get_stocks.py| B[stock_main table]
    B -->|maint_load_stock_cache_entries.py| C[cache_entries table]
    C --> D[TickStock Application]
    E[app_settings] --> C
    
    style A fill:#e1f5fe
    style B fill:#fff9c4
    style C fill:#c8e6c9
    style D fill:#f8bbd0
    style E fill:#d7ccc8


### Cache Loading Process

1. **Analysis Phase**
   - Read current cache_entries
   - Identify stock vs. non-stock entries
   - Compare with stock_main data

2. **Deletion Phase**
   - Remove all stock-related entries
   - Preserve app_settings and other non-stock data

3. **Loading Phase**
   - Generate market cap categories
   - Create sector leaders
   - Build theme collections
   - Compile industry groups
   - Calculate statistics

---

## Scripts Overview

### 1. maint_read_stock_cache_entries.py
**Purpose**: Analyze current cache state and provide recommendations


# Run analysis
python dev_tools/maint_read_stock_cache_entries.py


**Output**:
- Cache structure analysis
- Data freshness report
- Comparison with stock_main
- Recommendations for maintenance

### 2. maint_load_stock_cache_entries.py
**Purpose**: Load stock data from stock_main into cache_entries


# Run with prompts
python dev_tools/maint_load_stock_cache_entries.py

# Test mode first (recommended)
# Answer 'Y' when prompted for test mode


**Features**:
- Test mode for preview
- Preserves non-stock data
- Atomic transactions
- Progress reporting

---

## Cache Structure

### Entry Types

| Type | Purpose | Preserved on Reload | Description |
|------|---------|-------------------|-------------|
| `stock_universe` | Stock collections | No | Market cap groups, sectors, industries |
| `stock_stats` | Market statistics | No | Overall market statistics |
| `themes` | Thematic stock lists | No | AI, Biotech, Cloud, etc. |
| `priority_stocks` | Processing priority | No | High-priority stocks for throttling |
| `app_settings` | Application config | **Yes** | System configuration |

### Priority Stocks Structure

The `priority_stocks` type is used for processing prioritization when throttling is needed:

json
{
    "count": 100,
    "stocks": [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "rank": 1,
            "priority_level": "TOP",
            "priority_score": 95,
            "sector": "Technology",
            "industry": "Computer Hardware",
            "market_cap": 3000000000000,
            "exchange": "XNAS"
        }
    ],
    "top_priority_count": 50,
    "secondary_priority_count": 50,
    "criteria": "Most important stocks for processing prioritization",
    "last_updated": "2025-08-07T12:00:00Z"
}


### Data Schema

sql
CREATE TABLE cache_entries (
    id INTEGER PRIMARY KEY,
    type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    key VARCHAR NOT NULL,
    value JSONB NOT NULL,
    environment VARCHAR DEFAULT 'DEFAULT',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);


### JSON Value Structure

json
{
    "count": 500,
    "stocks": [
        {
            "name": "Company Name",
            "rank": 1,
            "sector": "Technology",
            "ticker": "TICK",
            "exchange": "XNAS",
            "industry": "Software",
            "market_cap": 1000000000
        }
    ]
}


---

## Usage Instructions

### Complete Refresh Process


# Step 1: Update stock_main from Polygon.io
python dev_tools/maint_get_stocks.py

# Step 2: Analyze current cache
python dev_tools/maint_read_stock_cache_entries.py

# Step 3: Load cache_entries
python dev_tools/maint_load_stock_cache_entries.py


### Interactive Prompts

1. **Test Mode Prompt**
   
   Do you want to run in TEST MODE first? [Y/n]:
   
   - Recommended: Always test first
   - Shows what would happen without changes

2. **Execution Confirmation**
   
   Test complete. Execute ACTUAL cache reload? [N/y]:
   
   - Review test results before proceeding

3. **Final Confirmation**
   
   Ready to reload cache? This will modify the database! [N/y]:
   
   - Last chance to cancel

---

## Scheduling

### Recommended Schedule

| Task | Frequency | Time | Command |
|------|-----------|------|---------|
| Stock Update | Daily | 4:00 AM | `maint_get_stocks.py` |
| Cache Reload | Daily | 4:30 AM | `maint_load_stock_cache_entries.py` |
| Full Refresh | Weekly | Sunday 3:00 AM | Both scripts with truncation |

### Cron Example


# Daily stock update and cache reload
0 4 * * * cd /app && python dev_tools/maint_get_stocks.py >> logs/stock_update.log 2>&1
30 4 * * * cd /app && python dev_tools/maint_load_stock_cache_entries.py >> logs/cache_load.log 2>&1

# Weekly full refresh
0 3 * * 0 cd /app && ./scripts/full_refresh.sh >> logs/full_refresh.log 2>&1


---

## Data Categories

### Market Cap Categories

| Category | Range | Stock Count |
|----------|-------|-------------|
| Mega Cap | > $200B | ~45 |
| Large Cap | $10B - $200B | ~500 |
| Mid Cap | $2B - $10B | ~500 |
| Small Cap | $300M - $2B | ~500 |
| Micro Cap | < $300M | ~500 |

### Priority Stocks

Priority stocks are used for processing prioritization during high-load situations:

| Priority Level | Stock Count | Purpose |
|---------------|-------------|---------|
| Top Priority | ~50 | Most liquid, highest volume stocks (AAPL, MSFT, etc.) |
| Secondary Priority | ~50 | Important growth and sector leaders |

### Themes

| Theme | Description | Example Tickers |
|-------|-------------|-----------------|
| AI | Artificial Intelligence | MSFT, NVDA, GOOGL |
| Biotech | Biotechnology | AMGN, GILD, VRTX |
| Cloud | Cloud Computing | MSFT, AMZN, GOOGL |
| Crypto | Cryptocurrency | MSTR, COIN, HOOD |
| Cybersecurity | Security Software | PANW, CRWD, FTNT |
| EV | Electric Vehicles | TSLA, GM, F |
| Fintech | Financial Technology | MELI, FI, PYPL |
| Semi | Semiconductors | NVDA, AVGO, AMD |

### Industry Groups

- Pharmaceuticals
- Banks
- Insurance
- Oil & Gas
- Software
- Aerospace
- Utilities
- Retail

---

## Troubleshooting

### Common Issues

#### 1. Cache Out of Sync
**Symptom**: Stock counts don't match between stock_main and cache

# Check sync status
python dev_tools/maint_read_stock_cache_entries.py

**Solution**: Run cache reload script

#### 2. Missing Themes
**Symptom**: Theme entries not appearing in cache
**Solution**: Check theme ticker definitions in script
python
THEME_DEFINITIONS = {
    'AI': ['MSFT', 'NVDA', ...],
    # Verify tickers exist in stock_main
}


#### 3. Performance Issues
**Symptom**: Cache loading takes too long
**Solution**: 
- Check database indexes
- Verify network connectivity
- Consider batch size adjustments

#### 4. Transaction Rollback
**Symptom**: "Error: current transaction is aborted"
**Solution**: 
sql
-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Reset connection
\q
psql -U app_readwrite -d tickstock


### Validation Queries

sql
-- Check cache freshness
SELECT 
    type,
    COUNT(*) as entries,
    MAX(updated_at) as last_update,
    EXTRACT(epoch FROM (NOW() - MAX(updated_at)))/3600 as hours_old
FROM cache_entries
GROUP BY type
ORDER BY type;

-- Verify stock coverage
SELECT 
    (SELECT COUNT(*) FROM stock_main WHERE type = 'CS') as stock_main_count,
    (SELECT jsonb_extract_path_text(value::jsonb, 'overview', 'total_stocks')::int 
     FROM cache_entries 
     WHERE type = 'stock_stats' AND key = 'summary') as cached_count;

-- Check for duplicates
SELECT type, name, key, COUNT(*) 
FROM cache_entries 
GROUP BY type, name, key 
HAVING COUNT(*) > 1;


---

## Performance Considerations

### Optimization Tips

1. **Batch Size**: Current implementation loads 500 stocks per category
2. **JSON Size**: Preview limited to top 3 stocks to reduce storage
3. **Indexing**: Ensure proper indexes on:
   sql
   CREATE INDEX idx_cache_type_name ON cache_entries(type, name);
   CREATE INDEX idx_cache_key ON cache_entries(key);
   CREATE INDEX idx_stock_main_market_cap ON stock_main(market_cap DESC);
   

4. **Transaction Management**: All operations in single transaction for atomicity

### Resource Usage

| Operation | Typical Duration | Database Load |
|-----------|-----------------|---------------|
| Analysis | 5-10 seconds | Low |
| Deletion | 1-2 seconds | Medium |
| Loading | 30-60 seconds | High |
| Total | ~2 minutes | Variable |

---

## Maintenance Schedule

### Daily Tasks
- Monitor cache freshness
- Check for loading errors in logs
- Verify stock counts match

### Weekly Tasks
- Full cache rebuild
- Performance analysis
- Theme definition updates

### Monthly Tasks
- Review and update market cap thresholds
- Add new themes based on market trends
- Archive old cache data
- Optimize database indexes

### Quarterly Tasks
- Review cache structure for improvements
- Update documentation
- Performance benchmarking
- Capacity planning

---

## Health Monitoring

### Key Metrics

sql
-- Cache health dashboard
WITH cache_stats AS (
    SELECT 
        COUNT(*) as total_entries,
        COUNT(DISTINCT type) as types,
        COUNT(CASE WHEN type = 'stock_universe' THEN 1 END) as universe_entries,
        COUNT(CASE WHEN type = 'themes' THEN 1 END) as theme_entries,
        MAX(updated_at) as last_update
    FROM cache_entries
),
stock_stats AS (
    SELECT 
        COUNT(*) as total_stocks,
        COUNT(DISTINCT sector) as sectors,
        MAX(last_updated_date) as last_stock_update
    FROM stock_main
    WHERE type = 'CS'
)
SELECT 
    cs.*,
    ss.*,
    CASE 
        WHEN cs.last_update < NOW() - INTERVAL '24 hours' THEN 'STALE'
        ELSE 'FRESH'
    END as cache_status
FROM cache_stats cs, stock_stats ss;


### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Cache Age | > 24 hours | > 48 hours |
| Entry Count | < 50 | < 20 |
| Load Time | > 5 minutes | > 10 minutes |
| Error Rate | > 5% | > 10% |

---

## Contact & Support

For issues or questions:
1. Check logs in `logs/cache_load.log`
2. Run analysis script for diagnostics
3. Review this documentation
4. Contact the TickStock development team

---

*Last Updated: August 7, 2025*
*Version: 1.0*