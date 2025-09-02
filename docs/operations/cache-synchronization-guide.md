# Cache Synchronization Operations Guide

**Document Version**: 1.0  
**Created**: 2025-09-02  
**Sprint**: 14 Phase 3  

## Overview

The Cache Synchronization system provides automated daily maintenance of the `cache_entries` table, ensuring universe memberships remain current with market conditions and company changes.

## System Components

### CacheEntriesSynchronizer Service
**Location**: `src/core/services/cache_entries_synchronizer.py`

Core service class that performs:
- Market cap recalculation and universe membership updates
- Automatic IPO assignment to appropriate themes
- Delisted stock cleanup with historical preservation
- Theme rebalancing based on market conditions
- Redis pub-sub notifications for real-time updates

### Daily Execution Script
**Location**: `scripts/maintenance/run_cache_synchronization.py`

Standalone script for executing the daily synchronization job with options for:
- Production execution
- Dry-run mode for testing
- Verbose logging for debugging

## Daily Synchronization Process

### Step 1: Market Cap Recalculation
- Calculates current market caps using latest close prices from `ohlcv_daily`
- Updates `symbols.market_cap` for symbols with significant changes (>5%)
- Triggers universe membership updates based on new market cap ranges

### Step 2: IPO Detection and Assignment
- Identifies symbols added in the last 30 days
- Automatically assigns to appropriate theme universes based on:
  - Market capitalization thresholds
  - Sector classification
  - Exchange listing
- Supports themes: `large_cap_growth`, `small_cap_value`, `dividend_aristocrats`, `technology_leaders`

### Step 3: Delisted Stock Cleanup
- Removes inactive stocks from universe entries
- Preserves historical data by updating metadata
- Maintains audit trail of removed symbols with timestamps

### Step 4: Theme Rebalancing
- Applies market condition-based rebalancing rules
- Updates universe metadata with rebalancing statistics
- Future enhancement: sophisticated rebalancing based on performance metrics

### Step 5: Redis Notifications
- Publishes sync completion notifications to Redis channels:
  - `cache_updates` - General cache update notifications
  - `universe_updates` - Universe membership changes
  - `admin_notifications` - Administrative alerts

## Execution Instructions

### Via Admin Interface (Recommended)
1. Navigate to the Admin Historical Data dashboard: `/admin/historical-data`
2. Scroll to the **Cache Organization** section
3. Choose rebuild mode:
   - **Unchecked** (default): Replace all stock/ETF entries (preserves app_settings)
   - **Checked**: Preserve existing entries (append mode)
4. Click **"Update and Organize Cache"** button
5. View results in flash messages

### Command Line Execution
```bash
# Navigate to project root
cd /path/to/TickStockAppV2

# Full rebuild (replace existing)
python scripts/maintenance/run_cache_synchronization.py

# Preserve existing entries (append mode)
python scripts/maintenance/run_cache_synchronization.py --no-delete

# With verbose logging
python scripts/maintenance/run_cache_synchronization.py --verbose
```

### Scheduling
The script should be scheduled to run daily after EOD processing:

**Cron example** (Linux/Unix):
```bash
# Run daily at 6:00 AM after EOD processing completes
0 6 * * * /usr/bin/python3 /path/to/TickStockAppV2/scripts/maintenance/run_cache_synchronization.py >> /var/log/tickstock/cache_sync.log 2>&1
```

**Windows Task Scheduler**:
- Schedule daily execution after market close processing
- Recommended time: 6:00 AM following trading day
- Working directory: TickStockAppV2 project root

## Output and Logging

### Console Output
```
======================================================================
🚀 TickStock Cache Entries Synchronization
======================================================================
Started at: 2025-09-02 06:00:15
Mode: PRODUCTION

======================================================================
✅ SYNCHRONIZATION COMPLETED SUCCESSFULLY
======================================================================
Duration: 45.32 seconds

📊 Synchronization Statistics:
  • Market cap updates: 127
  • New IPOs assigned: 3
  • Delisted stocks cleaned: 8
  • Themes rebalanced: 5
  • Redis notifications sent: 3
```

### Log Files
- **Location**: `logs/cache_sync_YYYYMMDD.log`
- **Retention**: 30 days (recommend automated cleanup)
- **Format**: Structured logging with timestamps and component identification

### Database Verification Queries

#### Check Recent Sync Activity
```sql
SELECT 
    key, 
    universe_category,
    jsonb_extract_path_text(universe_metadata, 'last_updated') as last_updated,
    jsonb_extract_path_text(universe_metadata, 'last_cleanup') as last_cleanup,
    jsonb_extract_path_text(universe_metadata, 'last_rebalance') as last_rebalance
FROM cache_entries 
WHERE universe_metadata ? 'last_updated'
ORDER BY jsonb_extract_path_text(universe_metadata, 'last_updated') DESC
LIMIT 20;
```

#### Verify Market Cap Updates
```sql
SELECT 
    symbol, 
    market_cap, 
    last_updated
FROM symbols 
WHERE last_updated >= CURRENT_DATE
  AND market_cap IS NOT NULL
ORDER BY last_updated DESC
LIMIT 20;
```

#### Check Universe Counts
```sql
SELECT 
    key,
    universe_category,
    jsonb_array_length(value) as symbol_count,
    jsonb_extract_path_text(universe_metadata, 'last_updated') as last_updated
FROM cache_entries 
ORDER BY universe_category, key;
```

## Error Handling

### Common Issues

#### Database Connection Errors
- **Cause**: Invalid `DATABASE_URI` or connection timeout
- **Resolution**: Verify `.env` file configuration and database availability

#### Redis Connection Errors  
- **Cause**: Redis service unavailable or misconfigured
- **Resolution**: Check Redis service status and connection parameters

#### Market Cap Calculation Failures
- **Cause**: Missing `weighted_shares_outstanding` or price data
- **Resolution**: Review symbol data completeness, may require manual correction

### Recovery Procedures

#### Partial Sync Failure
1. Review error logs for specific component failure
2. Run with `--dry-run --verbose` to identify issues
3. Execute manual corrections if needed
4. Re-run synchronization

#### Complete Sync Failure
1. Check database and Redis connectivity
2. Verify all required environment variables are set
3. Review recent schema changes or data corruption
4. Contact system administrator if infrastructure issues

## Performance Considerations

### Expected Performance Metrics
- **Execution Time**: 30-60 seconds for typical universe sizes
- **Database Load**: Moderate during execution, minimal impact on real-time operations
- **Memory Usage**: <100MB peak for standard symbol counts

### Optimization Opportunities
- Batch processing for large symbol sets
- Parallel theme processing
- Incremental updates vs full recalculation
- Redis pipeline for bulk notifications

## Monitoring and Alerts

### Success Metrics
- Synchronization completion within expected timeframe
- Redis notifications published successfully
- Database consistency maintained

### Alert Conditions
- Sync execution time exceeds 5 minutes
- High number of market cap calculation failures (>10%)
- Redis notification publishing failures
- Significant universe membership changes (>20% in single sync)

## Integration with TickStock Services

### Real-time Updates
- Redis notifications trigger WebSocket broadcasts to connected clients
- Universe changes reflected in user interface immediately
- Admin dashboard shows sync status and statistics

### Data Consistency
- Synchronization runs during low-activity periods
- Database transactions ensure atomicity
- Rollback capability on critical errors

## Future Enhancements

### Planned Features
- Advanced theme rebalancing algorithms
- Machine learning-based IPO classification
- Performance-based universe optimization
- Historical trend analysis for membership decisions

### Scalability Improvements  
- Distributed processing for large datasets
- Real-time streaming updates vs batch processing
- Enhanced monitoring and observability
- Multi-region synchronization support