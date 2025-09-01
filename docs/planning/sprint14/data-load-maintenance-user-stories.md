# Data Load and Maintenance User Stories

**Date Created**: 2025-08-31  
**Sprint**: 14  
**Status**: Active Implementation  

## Executive Summary

Based on analysis of existing TickStock infrastructure, this document organizes user stories for three critical data management areas:

1. **Historical Data Load Job** - Production environment bulk historical data loading
2. **Development Historical Data Load Job** - Development environment subset data loading  
3. **Daily Maintenance Job** - End-of-day data maintenance and updates

**Current State**: Historical data loader is functional with web admin interface, scheduler, and CLI support. Cache entries system maintains stock universes and themes. Missing components include ETF integration, automated IPO or stock ticker change monitoring, and comprehensive daily maintenance jobs.

---

## 1. Historical Data Load Job User Stories

### Epic: Production Historical Data Management
**Goal**: Maintain comprehensive historical market data for production trading analysis and backtesting

#### Story 1.1: Enhanced ETF Integration
**As a** system administrator  
**I want** the historical data loader to support ETF data alongside equities as defined by equity_types table 
**So that** users can analyze and backtest ETF-based strategies with the same depth as stock analysis

**Acceptance Criteria:**
- [ ] Historical loader accepts ETF symbols from cache_entries universe definitions
- [ ] ETF data populates symbols table with proper type classification
- [ ] ETF historical data loads into ohlcv_daily and ohlcv_1min tables
- [ ] equity_types table define all the types of stocks and equities to be loaded into database
- [ ] equity_types table define stock groupsing in cache_entries along with ETF integration
- [ ] ETF symbols integrate with existing cache_entries theme system (e.g., "Sector ETFs", "Growth ETFs") identifying index relationships (e.g. "Correlates to SPY", "Correlates to IWM", etc.)
- [ ] Web admin interface displays ETF loading progress separately from stocks
- [ ] Handling for Polygon ETF-specific endpoints (e.g., AUM capture)
- [ ] Incorporate FMV as an optional field in ohlcv_daily for approximated intraday values during loads, leveraging FMV's low median errors (e.g., 1.3 cents for AMD as per FMV Whitepaper) for thinly traded ETFs
- [ ] Add resilience for API rate limits during bulk ETF loads

**Definition of Done:**
- ETF symbols can be loaded using `--universe etf_growth` or similar cache_entries key
- Test loads complete for 50+ major ETFs with 1 year of data
- Initial Load column added to symbols table to assist in detecting new stocks during end of day run
- Documentation updated with ETF-specific examples
- Python test script verifies ETF loads successfully
- ETF data feeds into pattern detection models for correlations (e.g., to SPY)

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! To load ETF data and tie it into pattern analysis, extend historical_loader.py with thematic grouping:
```python
import pandas as pd
from polygon import RESTClient  # Assuming we have Polygon API wrapper

def load_etf_universe(api_key, universe_key='etf_growth'):
    client = RESTClient(api_key)
    etfs = []  # Fetch from cache_entries or Polygon
    for symbol in get_cache_entries(universe_key):  # Custom func to pull from DB
        historical = client.get_aggs(symbol, 1, 'day', from_='2024-01-01', to='2025-08-31')
        df = pd.DataFrame(historical)
        df['type'] = 'ETF'  # Classify per equity_types
        # Insert to ohlcv_daily: your DB insert logic here
        etfs.append(df)
    return pd.concat(etfs)  # For pattern library input
```
This could feed into a pattern detector library, e.g., scanning for ETF correlations to SPY.

#### Story 1.2: Cache Entries Universe Expansion
**As a** data administrator  
**I want** cache_entries to include comprehensive ETF groupings  
**So that** historical data jobs can load thematic ETF collections efficiently

**Acceptance Criteria:**
- [ ] Cache entries system includes ETF-specific universe definitions
- [ ] ETF themes defined: "Sector ETFs", "Growth ETFs", "Value ETFs", "International ETFs", "Commodity ETFs"
- [ ] ETF symbols maintain relationship to underlying stock sectors where applicable
- [ ] Universe size management (e.g., top_etf_50, etf_sectors, etc.)
- [ ] ETF market cap and AUM data captured where available from Polygon.io
- [ ] Dynamic universe sizing based on liquidity (e.g., filter by avg daily volume >5m like VXX in FMV Whitepaper)

**Definition of Done:**
- Cache entries query returns 200+ ETF symbols across 5 major themes
- ETF universes testable via existing historical loader CLI interface
- ETF data integrates with stocks in cache_entries without conflicts
- Validation against Polygon's reference data

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For universe building and pattern libs for value vs. growth ETF comparisons:
```python
def expand_cache_entries(themes=['Sector ETFs', 'Growth ETFs']):
    universes = {}
    for theme in themes:
        # Query Polygon for ETFs, filter by AUM > $1B
        etfs = fetch_polygon_etfs(theme)  # Custom API call
        universes[theme] = [etf['ticker'] for etf in etfs if etf['aum'] > 1e9]
    update_db_cache_entries(universes)  # Insert to cache_entries table
    return universes
```

#### Story 1.3: Symbol Change and IPO Monitoring
**As a** system administrator  
**I want** automated detection of new IPOs and symbol changes  
**So that** the production system maintains current and accurate symbol data without manual intervention

**Acceptance Criteria:**
- [ ] Daily job detects new stock and ETF listings from Polygon.io  
- [ ] Symbol changes (ticker changes, delistings) identified and handled
- [ ] New IPOs automatically added to appropriate cache_entries universes
- [ ] Historical data backfill triggered for new symbols (last 90 days minimum or any available)
- [ ] Notification system alerts administrators of significant symbol changes
- [ ] Handling delistings (e.g., archive in symbols table)
- [ ] Integrate FMV for quick value checks on new IPOs to flag anomalies

**Definition of Done:**
- Automated daily scan identifies 90%+ of new IPOs within 24 hours of listing
- Symbol changes update both symbols table and cache_entries references
- Historical backfill jobs complete automatically for new symbols
- Test with simulated IPOs

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For daily scanner:
```python
from datetime import datetime, timedelta

def monitor_ipos(api_key):
    client = RESTClient(api_key)
    today = datetime.now().date()
    new_listings = client.get_tickers(types='CS,ET', date=today - timedelta(days=1))
    for listing in new_listings:
        if listing['active'] and not in_symbols_table(listing['ticker']):
            add_to_symbols(listing['ticker'], initial_load_date=today)
            backfill_historical(listing['ticker'], days=90)  # Load OHLCV
            assign_to_cache_entries(listing)  # Auto-theme based on sector
    notify_admins([l['ticker'] for l in new_listings])  # Email/Slack
```

#### Story 1.4: Advanced Production Load Scheduling
**As a** production administrator  
**I want** sophisticated scheduling options for historical data loads  
**So that** large production loads can be managed efficiently without impacting live trading systems

**Acceptance Criteria:**
- [ ] Time-based scheduling with market holiday awareness
- [ ] Load priority system (critical symbols first, then secondary)
- [ ] Resource throttling based on system load and trading hours
- [ ] Partial load resume capability for interrupted jobs
- [ ] Load balancing across multiple time ranges to minimize API impact
- [ ] Multi-threaded loads (e.g., via Python's concurrent.futures)

**Definition of Done:**
- Scheduler can load 5 years of data for 500 symbols with <5% API errors
- Interrupted jobs resume from last successful symbol/date combination  
- Holiday calendar prevents unnecessary processing on non-trading days
- Benchmark with large sets

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For scheduler extension:
```python
import schedule
from market_calendar import is_trading_day  # Custom or NYSE calendar lib

def schedule_loads():
    if is_trading_day():
        schedule.every().day.at("20:00").do(run_historical_load, priority='critical')
        # Throttle: Use queue for symbol batches
    schedule.run_pending()
```

---

## 2. Development Historical Data Load Job User Stories

### Epic: Development Environment Data Management
**Goal**: Provide flexible, fast data loading for development and testing environments

#### Story 2.1: Subset Universe Loading
**As a** developer  
**I want** to load specific subsets of stock and ETF data  
**So that** I can test features quickly without waiting for full production data loads

**Acceptance Criteria:**
- [ ] CLI accepts custom symbol lists: `--symbols AAPL,MSFT,NVDA,SPY,QQQ`
- [ ] Predefined development universes in cache_entries: "dev_top_10", "dev_sectors", "dev_etfs"
- [ ] Time range limitations: `--years 0.5` or `--months 3` for faster loads
- [ ] Development-specific database connection settings
- [ ] Progress reporting optimized for smaller datasets
- [ ] Caching subsets locally
- [ ] Use Polygon's delayed data for cost savings (15-min delay ~52% market share per Equities sheet)

**Definition of Done:**
- Development load of 10 stocks + 5 ETFs with 6 months data completes in <5 minutes
- All existing historical loader features work with subset loading
- Development universes maintainable through web admin interface
- <5 min benchmark achievable with Polygon's aggs endpoint

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For subset loader:
```python
def load_subset(symbols=['AAPL', 'SPY'], months=3):
    end = datetime.now()
    start = end - timedelta(days=30*months)
    for symbol in symbols:
        aggs = client.get_aggs(symbol, 1, 'minute', from_=start, to=end)
        insert_to_ohlcv_1min(pd.DataFrame(aggs))
```

#### Story 2.2: Feature Testing Data Scenarios
**As a** developer working on pattern detection  
**I want** specific historical data scenarios for testing  
**So that** I can validate event detection and backtesting features with known data patterns

**Acceptance Criteria:**
- [ ] Predefined test scenarios: "crash_2020", "growth_2021", "volatility_periods"
- [ ] Synthetic data generation for edge cases (gaps, splits, high volatility)
- [ ] Known pattern stocks: symbols with documented high/low events, trend changes
- [ ] Minute-level data for intraday pattern testing
- [ ] Data quality validation: missing days, price anomalies identified
- [ ] Integrating with libraries like ta-lib for pattern validation

**Definition of Done:**
- Test scenarios loadable via `--scenario crash_2020` command
- Synthetic data generator creates realistic OHLCV data with controllable patterns
- Documentation includes expected pattern outcomes for each test scenario

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For synthetic generator, inspired by FMV Whitepaper's methodology for predicting trades:
```python
import numpy as np

def generate_synthetic_ohlcv(length=100, pattern='crash'):
    if pattern == 'crash':
        prices = np.cumprod(1 + np.random.normal(0, 0.01, length))
        prices[50:] *= 0.8  # Simulate 20% drop
    return pd.DataFrame({'open': prices, 'high': prices*1.01, 'low': prices*0.99, 'close': prices})
```

#### Story 2.3: Rapid Development Refresh
**As a** developer  
**I want** fast incremental updates of development data  
**So that** I can test against recent market conditions without full reloads

**Acceptance Criteria:**
- [ ] Incremental updates: only load last N days of new data
- [ ] Smart detection of data gaps and selective backfill
- [ ] Development database reset/restore capabilities
- [ ] Configuration profiles for different development needs (patterns, backtesting, UI)
- [ ] Integration with development Docker containers
- [ ] Docker volume mounts for data isolation

**Definition of Done:**
- Daily development refresh completes in <2 minutes for 50 symbols
- Database reset restores to known baseline within 30 seconds
- Multiple developers can work with isolated data environments

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For incremental update:
```python
def incremental_refresh(symbols, days=7):
    last_date = get_last_ohlcv_date(symbols[0])
    if (datetime.now() - last_date).days > 1:
        backfill_gap(symbols, from_=last_date)
```

---

## 3. Daily Maintenance Job User Stories

### Epic: Automated End-of-Day Data Maintenance
**Goal**: Ensure all production data remains current, accurate, and optimized

#### Story 3.1: End-of-Day Market Data Updates
**As a** production system  
**I want** comprehensive end-of-day updates for all tracked symbols  
**So that** pattern detection and backtesting operate on complete, current market data

**Acceptance Criteria:**
- [ ] EOD job runs automatically after market close (4:30 PM ET + buffer)
- [ ] Updates all symbols in cache_entries universes with daily OHLCV data
- [ ] Processes both real-time monitored stocks and EOD-only equity_types
- [ ] Handles market holidays and abbreviated trading days
- [ ] Validates data completeness and flags missing data
- [ ] FMV integration in validation (low errors per FMV Whitepaper)
- [ ] Use Polygon's full market for 100% coverage if upgraded (per Equities sheet)

**Definition of Done:**
- 95% of tracked symbols updated with current day's data by 6:00 PM ET
- Missing data alerts generated for symbols with gaps >1 trading day
- EOD job logs provide complete processing summary

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For EOD runner:
```python
def eod_update():
    symbols = get_cache_symbols()
    for symbol in symbols:
        daily_agg = client.get_aggs(symbol, 1, 'day', from_=today-1, to=today)
        insert_and_validate(daily_agg)
```

#### Story 3.2: Equity Types Integration
**As a** system administrator  
**I want** the daily maintenance job to respect equity_types configuration  
**So that** different symbol categories receive appropriate update frequencies and processing

**Acceptance Criteria:**
- [ ] Equity types table defines update frequency per category (daily, real-time, etc.)
- [ ] Daily job processes only symbols marked for EOD updates
- [ ] Real-time monitored symbols receive EOD data validation/correction
- [ ] Category-specific processing rules (e.g., ETFs get additional AUM data)
- [ ] Update frequency compliance reporting

**Definition of Done:**
- Daily maintenance job processes 100% of equity_types="daily" symbols
- Real-time symbols receive EOD validation without duplication
- Equity types configuration drives all processing decisions

#### Story 3.3: Cache Entries Synchronization  
**As a** system administrator  
**I want** daily cache_entries updates to reflect current market conditions  
**So that** application users see current stock universes and market data

**Acceptance Criteria:**
- [ ] Daily refresh of cache_entries after stock_main updates
- [ ] Market cap recalculation updates stock universe memberships  
- [ ] New IPOs automatically assigned to appropriate cache_entries themes
- [ ] Delisted stocks removed from active universes but preserved in historical data
- [ ] Theme rebalancing based on updated market conditions
- [ ] Logging changes for market cap universe shifts

**Definition of Done:**
- Cache entries refreshed within 30 minutes of stock_main EOD updates
- Market cap universe changes logged and reported daily
- Theme assignments remain stable unless justified by significant market changes

#### Story 3.4: Data Quality and Monitoring
**As a** system administrator  
**I want** comprehensive daily data quality checks  
**So that** data issues are detected and resolved before affecting trading analysis

**Acceptance Criteria:**
- [ ] Daily validation reports for data completeness, accuracy, and consistency
- [ ] Price anomaly detection (>20% moves, splits, unusual volumes)
- [ ] Duplicate data detection and cleanup
- [ ] Historical data gap identification and backfill triggering
- [ ] Performance monitoring and optimization recommendations
- [ ] Auto-backfill for detected issues
- [ ] Anomaly detection aligned with FMV's accuracy stats (e.g., flag >20% moves)

**Definition of Done:**
- Daily quality report emails sent to administrators by 7:00 PM ET
- 99% of data quality issues auto-resolved or flagged for manual review
- Historical data gaps <0.1% of total expected records

**Implementation Ideas:**
Let's build some fantastic algorithmic pattern libraries in Python to add to TickStock.ai! For anomaly detector:
```python
def detect_anomalies(df):
    returns = df['close'].pct_change()
    anomalies = returns[abs(returns) > 0.2]
    if not anomalies.empty:
        flag_for_review(anomalies)
```

#### Story 3.5: Holiday and Schedule Awareness
**As a** production system  
**I want** intelligent market calendar integration  
**So that** daily maintenance jobs operate efficiently without unnecessary processing on non-trading days

**Acceptance Criteria:**
- [ ] Market holiday calendar integration (NYSE, NASDAQ)
- [ ] Abbreviated trading day handling (early close days)
- [ ] International market schedule awareness for global ETFs
- [ ] Weekend and after-hours processing optimization
- [ ] Schedule adjustment notifications to administrators

**Definition of Done:**
- No processing attempts on confirmed market holidays
- Early close days trigger maintenance 1 hour after market close
- International symbols processed according to their primary exchange schedule

---

## Implementation Priority and Dependencies

### Phase 1: Foundation Enhancement (Sprint 14)
1. **Story 1.1**: Enhanced ETF Integration
2. **Story 2.1**: Subset Universe Loading  
3. **Story 3.1**: End-of-Day Market Data Updates

**Dependencies**: Existing historical_loader.py, cache_entries system, symbols table

**Implementation Plan**: [`sprint14-phase1-implementation-plan.md`](sprint14-phase1-implementation-plan.md) - Complete implementation details with mandatory agent workflows, database schema changes, and success criteria

### Phase 2: Automation and Monitoring (Sprint 14)
1. **Story 1.3**: Symbol Change and IPO Monitoring
2. **Story 3.2**: Equity Types Integration
3. **Story 3.4**: Data Quality and Monitoring

**Dependencies**: Phase 1 completion, equity_types table schema

**Implementation Plan**: [`sprint14-phase2-implementation-plan.md`](sprint14-phase2-implementation-plan.md) - Automated IPO detection, equity type integration, and comprehensive data quality monitoring

### Phase 3: Advanced Features (Sprint 14) 
1. **Story 1.2**: Cache Entries Universe Expansion
2. **Story 2.2**: Feature Testing Data Scenarios
3. **Story 3.3**: Cache Entries Synchronization

**Dependencies**: Phase 2 completion, enhanced cache_entries schema

**Implementation Plan**: [`sprint14-phase3-implementation-plan.md`](sprint14-phase3-implementation-plan.md) - Universe expansion with ETF themes, development testing scenarios, and cache synchronization automation

### Phase 4: Production Optimization (Sprint 14)
1. **Story 1.4**: Advanced Production Load Scheduling
2. **Story 2.3**: Rapid Development Refresh
3. **Story 3.5**: Holiday and Schedule Awareness

**Dependencies**: All previous phases, production deployment infrastructure

**Implementation Plan**: [`sprint14-phase4-implementation-plan.md`](sprint14-phase4-implementation-plan.md) - Enterprise scheduling with market calendar integration, development environment optimizations, and production-grade automation

---

## Technical Implementation Notes

### Database Schema Changes Required
- **equity_types table**: Already exists, may need additional columns
- **symbols table**: Enhanced with ETF support (type, AUM, expense_ratio)
- **cache_entries**: New ETF universe types and themes
- **ohlcv_daily/ohlcv_1min**: No changes required, but add optional FMV field for approximated values
**Database Changes Scripted and passed to human to execute**

### API Integration Enhancements
- **Polygon.io ETF endpoints**: Add ETF-specific data fetching
- **IPO detection**: Daily scan of new listings endpoint.  At the time of running the end of day maintenance will update symbols load date. 
- **Symbol changes**: Reference data change tracking
- **FMV Integration**: Use FMV for dev subsets to mimic real-time without costs (FMV Whitepaper shows it's close to consolidated trades)
- **API Rate Limiting**: Enhanced throttling for larger data volumes, including multi-threaded loads

### Configuration Management
- **Environment-specific settings**: Dev vs. production data volumes
- **Market calendar**: Holiday and schedule awareness
- **Notification systems**: Email, Slack integration for alerts

### Performance Considerations
- **API rate limiting**: Enhanced throttling for larger data volumes
- **Database optimization**: Indexes for ETF queries, partition strategies
- **Monitoring**: Resource usage tracking, processing time optimization
- **Python Unit Tests**: Aim for 80%+ coverage across stories

---

## Success Metrics

### Production Metrics
- **Data Completeness**: >99% of trading days covered for all symbols
- **Processing Time**: Daily maintenance completes within 2-hour window
- **Error Rate**: <1% of daily symbol updates fail
- **System Availability**: Data ready for market open next day

### Development Metrics  
- **Load Speed**: Development environments load test data in <10 minutes
- **Data Freshness**: Development data <7 days behind production
- **Test Coverage**: All major market scenarios available for testing

### Quality Metrics
- **Data Accuracy**: <0.01% price discrepancies vs. authoritative sources
- **Gap Prevention**: >99% detection of missing data before EOD
- **Symbol Coverage**: 100% of cache_entries symbols tracked daily

---

## Related Documentation

- **[`../project-overview.md`](../project-overview.md)** - Complete system vision, requirements, and architecture principles
- **[`../architecture_overview.md`](../architecture_overview.md)** - Detailed role separation between TickStockApp and TickStockPL via Redis pub-sub
- **[`../database_architecture.md`](../database_architecture.md)** - Shared TimescaleDB database schema and optimization strategies
- **[`../tickstockpl-integration-guide.md`](../tickstockpl-integration-guide.md)** - Complete technical integration steps and Redis messaging patterns
- **[`../get_historical_data.md`](../get_historical_data.md)** - Technical details for seeding database with historical OHLCV data
- **[`sprint14-phase1-implementation-plan.md`](sprint14-phase1-implementation-plan.md)** - Phase 1 foundation enhancement implementation
- **[`sprint14-phase2-implementation-plan.md`](sprint14-phase2-implementation-plan.md)** - Phase 2 automation and monitoring implementation
- **[`sprint14-phase3-implementation-plan.md`](sprint14-phase3-implementation-plan.md)** - Phase 3 advanced features implementation
- **[`sprint14-phase4-implementation-plan.md`](sprint14-phase4-implementation-plan.md)** - Phase 4 production optimization implementation

---

*Document Status: Active Implementation - Sprint 14*  
*Implementation: Comprehensive 4-phase approach with mandatory agent workflows and quality gates*