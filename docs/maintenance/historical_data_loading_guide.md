# Historical Data Loading - Quick Reference Guide

## TL;DR - Most Common Commands

```bash
# 1. Load 1 year of daily data for top 50 stocks (most common use case)
export POLYGON_API_KEY="your_key_here"
python -m src.data.historical_loader --universe top_50 --years 1

# 2. Load specific high-priority symbols
python -m src.data.historical_loader --symbols NVDA,AAPL,MSFT,TSLA --years 2

# 3. Check what data you currently have
python -m src.data.historical_loader --summary
```

## Data Handling - Key Points

### ✅ Safe Operations (What Actually Happens)
- **Symbol Auto-Creation**: New symbols automatically created with Polygon.io metadata
- **Symbol Metadata Refresh**: Existing symbols updated with latest market cap, status, etc.
- **Upsert Strategy**: `ON CONFLICT DO UPDATE` - never deletes existing data
- **New dates**: Added to database
- **Existing dates**: Updated with fresh values (handles price corrections)
- **Outside date range**: Left completely untouched

### ❌ What NEVER Happens
- No table truncation
- No bulk deletion
- No overwrite of date ranges outside your request
- No data loss from previous loads
- No foreign key constraint errors (symbols created automatically)

### Real Example:
```
You have: AAPL 2022-01-01 to 2023-12-31 (730 days)
You run:  --symbols AAPL --years 1 (loads 2024 data)
Result:   AAPL 2022-01-01 to 2024-12-31 (1,095 days total)
```

## Production Workflow

### Initial Setup (One-time)
```bash
# Test with small dataset first
python -m src.data.historical_loader --symbols AAPL --years 0.1

# Then load core symbols
python -m src.data.historical_loader --symbols NVDA,AAPL,MSFT,GOOGL,TSLA --years 2

# Finally, full universe
python -m src.data.historical_loader --universe top_50 --years 1
```

### Regular Maintenance
```bash
# Weekly: Refresh recent data (last ~36 days)
python -m src.data.historical_loader --universe top_50 --years 0.1

# Monthly: Full year refresh
python -m src.data.historical_loader --universe top_50 --years 1

# Check data status
python -m src.data.historical_loader --summary
```

## Performance Expectations

| Command | Duration | API Calls | Records |
|---------|----------|-----------|---------|
| `--symbols AAPL --years 1` | ~30 seconds | 1-2 | ~252 |
| `--universe top_50 --years 1` | ~15-20 minutes | 50-100 | ~12,600 |
| `--symbols AAPL --years 1 --timespan minute` | ~2-4 minutes | 12-20 | ~100,000 |

Rate limit: 12 seconds between API calls (safe for free/basic tiers)

## Troubleshooting

### "Symbol not found in symbols table"
- The `ohlcv_daily` table has a foreign key constraint
- Only symbols that exist in the `symbols` table can be loaded
- Check available symbols: `SELECT symbol FROM symbols ORDER BY symbol;`

### Rate limit issues
```bash
# Increase delay between calls (default is 12 seconds)
export POLYGON_RATE_LIMIT_DELAY=20
```

### API key problems
```bash
# Make sure it's exported
echo $POLYGON_API_KEY

# Or pass directly
python -m src.data.historical_loader --api-key "your_key" --symbols AAPL --years 1
```

## Advanced Usage

### Load 1-minute data
```bash
# High volume - use sparingly and recent dates only
python -m src.data.historical_loader --symbols AAPL,SPY --years 0.5 --timespan minute
```

### Custom date ranges (modify script if needed)
```bash
# Current script loads from (current_date - years) to current_date
# For custom ranges, modify fetch_symbol_data() method
```

### Add new symbols to universe
```bash
# First add to symbols table, then load
python -m src.data.historical_loader --symbols NEW_SYMBOL --years 1
```

## Data Quality Checks

```bash
# Check record counts
python -m src.data.historical_loader --summary

# Verify in database
SELECT 
    symbol,
    COUNT(*) as records,
    MIN(date) as earliest,
    MAX(date) as latest
FROM ohlcv_daily 
GROUP BY symbol 
ORDER BY records DESC;
```

## Integration with TickStock

- Historical data provides foundation for pattern analysis
- Real-time WebSocket data appends to these tables
- Backtesting relies on this historical depth
- Event detection patterns need sufficient historical context

For complete details see: `docs/planning/get_historical_data.md`