# Stock Data Maintenance Documentation

## Overview

The Stock Data Maintenance utility (`maint_get_stocks.py`) is responsible for keeping the TickStock database current with the latest stock market data from Polygon.io. This utility fetches common stocks (CS type), enriches them with company data, and maintains the `stock_main` and `stock_related_tickers` tables.

---

## Table of Contents

1. [Purpose](#purpose)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Data Flow](#data-flow)
6. [Database Schema](#database-schema)
7. [Scheduling](#scheduling)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring](#monitoring)
10. [API Rate Limits](#api-rate-limits)

---

## Purpose

The maintenance utility serves to:
- Fetch all US common stocks from Polygon.io API
- Map stocks to sectors and industries using SIC codes
- Maintain relationships between related stocks
- Keep market capitalization data current
- Ensure data freshness for the TickStock application

---

## Prerequisites

### Required Software
- Python 3.x
- PostgreSQL database
- Active Python virtual environment

### Required Python Packages

pip install requests psycopg2-binary


### Required Access
- Polygon.io API key with stocks data access
- PostgreSQL database credentials with read/write permissions
- Access to `stock_main` and `stock_related_tickers` tables

---

## Configuration

### API Configuration
python
POLYGON_API_KEY = "your_api_key_here"  # Polygon.io API key
BASE_URL = "https://api.polygon.io"


### Database Configuration
python
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "tickstock",
    "user": "app_readwrite",
    "password": "your_password_here"
}


### File Location

TickStockApp/
└── dev_tools/
    └── maint_get_stocks.py


---

## Usage

### Basic Commands

#### 1. Run Diagnostic Mode
Check API and database connectivity without making changes:

python dev_tools/maint_get_stocks.py --diagnose


#### 2. Test Mode
Preview what would be processed without database modifications:

python dev_tools/maint_get_stocks.py
# Select 'Y' when prompted for test mode


#### 3. Update Mode (UPSERT)
Add new stocks and update existing ones without removing any data:

python dev_tools/maint_get_stocks.py
# Select 'N' for test mode
# Select 'N' for truncation
# Select 'Y' to proceed


#### 4. Full Refresh Mode
Complete reload of all stock data (removes existing data first):

python dev_tools/maint_get_stocks.py
# Select 'N' for test mode
# Select 'Y' for truncation
# Confirm truncation
# Select 'Y' to proceed


### Interactive Prompts

The utility will guide you through the following decisions:

1. **Test Mode**: `Do you want to TEST the process first?`
   - Yes: Analyzes data without database changes
   - No: Proceeds to actual data loading

2. **Truncation**: `Do you want to TRUNCATE existing tables before loading?`
   - Yes: Deletes all existing data before loading (full refresh)
   - No: Uses UPSERT mode (preserves existing data)

3. **Final Confirmation**: `Ready to continue? This will modify the database!`
   - Last chance to cancel before database modifications

---

## Data Flow

### Process Pipeline


Polygon.io API
    ↓
1. Fetch Common Stocks (CS type)
    ↓
2. For each stock:
   a. Fetch company details
   b. Fetch related tickers
   c. Map SIC code → Sector/Industry
    ↓
3. Insert/Update stock_main
    ↓
4. Insert/Update stock_related_tickers
    ↓
5. Secondary Job (separate process):
   stock_main → cache_entries


### API Endpoints Used

| Endpoint | Purpose | Rate Limit |
|----------|---------|------------|
| `/v3/reference/tickers` | Fetch stock list | 5 calls/min |
| `/v3/reference/tickers/{ticker}` | Company details | 5 calls/min |
| `/v1/related-companies/{ticker}` | Related stocks | 5 calls/min |

---

## Database Schema

### stock_main Table
sql
CREATE TABLE stock_main (
    ticker VARCHAR PRIMARY KEY,
    name VARCHAR,
    market VARCHAR,
    locale VARCHAR,
    primary_exchange VARCHAR,
    type VARCHAR,
    active BOOLEAN,
    currency_name VARCHAR,
    cik VARCHAR,
    market_cap NUMERIC,
    sector VARCHAR,
    industry VARCHAR,
    country VARCHAR,
    sic_code VARCHAR,
    sic_description VARCHAR,
    total_employees INTEGER,
    share_class_shares_outstanding NUMERIC,
    weighted_shares_outstanding NUMERIC,
    list_date DATE,
    insert_date TIMESTAMP,
    last_updated_date TIMESTAMP,
    enabled BOOLEAN DEFAULT true
);


### stock_related_tickers Table
sql
CREATE TABLE stock_related_tickers (
    stock_ticker VARCHAR,
    related_ticker VARCHAR,
    insert_date TIMESTAMP,
    PRIMARY KEY (stock_ticker, related_ticker),
    FOREIGN KEY (stock_ticker) REFERENCES stock_main(ticker)
);


---

## Scheduling

### Recommended Schedule

| Frequency | Mode | Purpose | Command |
|-----------|------|---------|---------|
| Daily | UPSERT | Catch new listings | `python maint_get_stocks.py` (no truncation) |
| Weekly | UPSERT | Update market caps | `python maint_get_stocks.py` (no truncation) |
| Monthly | TRUNCATE | Full data refresh | `python maint_get_stocks.py` (with truncation) |

### Windows Task Scheduler Setup

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily/weekly/monthly)
4. Set action:
   
   Program: C:\path\to\venv\Scripts\python.exe
   Arguments: C:\path\to\dev_tools\maint_get_stocks.py
   Start in: C:\path\to\TickStockApp
   

### Linux Cron Setup


# Daily update at 2 AM
0 2 * * * cd /path/to/project && /path/to/venv/bin/python dev_tools/maint_get_stocks.py

# Weekly full refresh on Sunday at 3 AM
0 3 * * 0 cd /path/to/project && /path/to/venv/bin/python dev_tools/maint_get_stocks.py --full-refresh


---

## Troubleshooting

### Common Issues and Solutions

#### 1. API Connection Failed

❌ Cannot proceed without Polygon API connection

**Solutions:**
- Verify API key is correct
- Check internet connectivity
- Ensure Polygon.io subscription is active
- Run diagnostic mode: `python maint_get_stocks.py --diagnose`

#### 2. Database Connection Failed

❌ Cannot proceed without database connection

**Solutions:**
- Verify PostgreSQL is running
- Check database credentials
- Ensure user has proper permissions
- Test connection: `psql -h localhost -U app_readwrite -d tickstock`

#### 3. Rate Limit Exceeded

⚠️ Rate limit exceeded (429)

**Solutions:**
- Wait 60 seconds before retrying
- Reduce request frequency
- Upgrade Polygon.io subscription for higher limits

#### 4. Missing Tables

⚠️ Required tables not found!

**Solutions:**
- Run database migration scripts
- Create tables manually (see Database Schema section)

### Debug Commands


# Check API key validity
curl "https://api.polygon.io/v3/reference/tickers?apiKey=YOUR_KEY&limit=1"

# Test database connection
psql -h localhost -U app_readwrite -d tickstock -c "SELECT COUNT(*) FROM stock_main;"

# Run in diagnostic mode
python dev_tools/maint_get_stocks.py --diagnose


---

## Monitoring

### Key Metrics to Track

| Metric | Expected Value | Alert Threshold |
|--------|---------------|-----------------|
| Total stocks processed | 5,000-8,000 | < 4,000 |
| Failed API calls | < 10 per run | > 50 |
| Processing time | 30-60 minutes | > 2 hours |
| New stocks added | Variable | > 100/day |

### Log File Analysis


# Count errors in log
grep ERROR logs/stock_maintenance.log | wc -l

# View recent warnings
tail -n 100 logs/stock_maintenance.log | grep WARNING

# Check processing statistics
grep "Completed fetching" logs/stock_maintenance.log


### Health Check Query

sql
-- Check data freshness
SELECT 
    COUNT(*) as total_stocks,
    COUNT(CASE WHEN last_updated_date > NOW() - INTERVAL '24 hours' THEN 1 END) as updated_today,
    COUNT(CASE WHEN last_updated_date > NOW() - INTERVAL '7 days' THEN 1 END) as updated_this_week,
    MAX(last_updated_date) as most_recent_update
FROM stock_main
WHERE type = 'CS';

-- Check sector distribution
SELECT 
    sector,
    COUNT(*) as stock_count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()), 2) as percentage
FROM stock_main
WHERE type = 'CS'
GROUP BY sector
ORDER BY stock_count DESC;


---

## API Rate Limits

### Polygon.io Limits by Subscription

| Tier | Requests/Minute | Requests/Day |
|------|----------------|--------------|
| Basic | 5 | 500 |
| Starter | 100 | 10,000 |
| Developer | 1,000 | 100,000 |
| Advanced | 10,000 | Unlimited |

### Rate Limiting Strategy

The utility implements:
- 0.1 second delay between ticker-specific calls
- 0.5 second delay between batch calls
- Automatic retry with exponential backoff on rate limit errors

---

## Maintenance Notes

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-08-07 | Initial release with basic fetch functionality |
| 1.1 | 2025-08-07 | Added interactive prompts and test mode |
| 1.2 | 2025-08-07 | Enhanced connection testing and diagnostics |

### Future Enhancements

- [ ] Email notifications for completion/errors
- [ ] Parallel processing for faster updates
- [ ] Incremental updates based on last_updated timestamp
- [ ] Archive historical data before truncation
- [ ] Add support for ETFs and other security types
- [ ] Implement data validation checks
- [ ] Add rollback capability for failed loads

### Contact

For issues or questions regarding this maintenance utility:
- Check logs in `logs/stock_maintenance.log`
- Review diagnostic output: `python maint_get_stocks.py --diagnose`
- Consult the TickStock development team

---

*Last Updated: August 7, 2025*