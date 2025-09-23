# Historical Data Management - Production Setup Guide

## Overview

This guide covers setting up historical data management for TickStock in production with multiple execution options:

1. **Web Admin Interface** - Easy GUI management via Flask app
2. **Automated Scheduling** - Cron jobs or systemd services
3. **Manual CLI Execution** - For one-off loads or troubleshooting
4. **Background Job System** - Web-triggered async jobs

## Quick Start

### 1. Set Environment Variables

```bash
# Required
export POLYGON_API_KEY="your_polygon_api_key_here"
export DATABASE_URI="postgresql://app_readwrite:password@localhost:5432/tickstock"

# Optional - for enhanced features  
export SLACK_WEBHOOK_URL="https://hooks.slack.com/your/webhook"
export NOTIFICATION_EMAIL="admin@yourcompany.com"
```

### 2. Test Basic Functionality

```bash
# Test the historical loader directly
python load_historical_data.py --summary

# Test with small dataset
python load_historical_data.py --symbols AAPL --years 0.1
```

### 3. Access Admin Interface

1. Start your Flask app: `python src/app.py`
2. Navigate to: `http://localhost:5000/admin/historical-data`
3. Login with your TickStock credentials
4. Use the web interface to trigger and monitor data loads

## Production Deployment Options

### Option 1: Web Admin Interface (Recommended)

**Best for**: Interactive management, monitoring, ad-hoc loads

**Setup**:
1. Admin routes are automatically registered with Flask app
2. Access via `/admin/historical-data`
3. Features:
   - Real-time job monitoring
   - Progress tracking
   - Historical job logs
   - Data quality dashboard
   - One-click load triggers

**Security**: Requires login, admin-level access recommended

### Option 2: Automated Scheduling

#### Linux/Unix - Cron Jobs

```bash
# Generate cron configuration
python src/jobs/historical_data_scheduler.py --generate-cron

# Example cron entries:
# Daily refresh at 2 AM
0 2 * * * cd /path/to/TickStockAppV2 && python src/jobs/historical_data_scheduler.py --job daily_refresh

# Weekly full refresh Sunday at 1 AM  
0 1 * * 0 cd /path/to/TickStockAppV2 && python src/jobs/historical_data_scheduler.py --job weekly_refresh
```

#### Linux - Systemd Service

```bash
# Generate systemd service file
python src/jobs/historical_data_scheduler.py --generate-systemd

# Install service
sudo cp generated-service-file /etc/systemd/system/tickstock-historical.service
sudo systemctl daemon-reload
sudo systemctl enable tickstock-historical
sudo systemctl start tickstock-historical

# Monitor
sudo journalctl -u tickstock-historical -f
```

#### Windows - Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, weekly, etc.)
4. Set action: 
   - Program: `python.exe`
   - Arguments: `C:\path\to\TickStockAppV2\src\jobs\historical_data_scheduler.py --job daily_refresh`
   - Start in: `C:\path\to\TickStockAppV2`

### Option 3: Manual CLI Execution

```bash
# One-time loads
python src/jobs/historical_data_scheduler.py --universe top_50 --years 1
python src/jobs/historical_data_scheduler.py --symbols AAPL,MSFT,GOOGL --years 2

# Daemon mode (runs continuously with scheduled jobs)
python src/jobs/historical_data_scheduler.py --daemon --config config/historical_data_scheduler.json
```

### Option 4: Background Job System

Integrated with the Flask app for web-triggered async execution:

```python
# Jobs run in background threads
# Status tracked in memory (production should use Redis/database)
# Web interface provides real-time monitoring
# Supports job cancellation and progress tracking
```

## Configuration

### Scheduler Configuration

Edit `config/historical_data_scheduler.json`:

```json
{
  "schedules": {
    "daily_refresh": {
      "enabled": true,
      "time": "02:00",
      "universe": "top_50", 
      "years": 0.1,
      "timespan": "day"
    }
  },
  "limits": {
    "api_delay_seconds": 12,
    "max_retries": 3,
    "timeout_minutes": 120
  }
}
```

### Environment Variables

```bash
# Core configuration
POLYGON_API_KEY=your_api_key
DATABASE_URI=postgresql://user:pass@host/db

# Rate limiting
POLYGON_RATE_LIMIT_DELAY=12

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
NOTIFICATION_EMAIL=admin@company.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/historical_data.log
```

## Monitoring & Operations

### Health Checks

```bash
# Check data status
python load_historical_data.py --summary

# Check specific universe
python -c "
from src.data.historical_loader import PolygonHistoricalLoader
loader = PolygonHistoricalLoader()
symbols = loader.load_symbols_from_cache('top_50')
print(f'Universe contains {len(symbols)} symbols')
"
```

### Log Files

```bash
# Application logs
tail -f logs/historical_data_scheduler.log

# Job history
cat logs/job_history.jsonl | jq '.'

# Flask app logs (for web interface)
tail -f logs/app.log
```

### Performance Monitoring

Expected performance for production loads:

| Operation | Duration | API Calls | Records |
|-----------|----------|-----------|---------|
| Top 50, 1 year daily | 15-20 min | ~50-100 | ~12,600 |
| Single stock, 1 year daily | 30-60 sec | 1-2 | ~252 |
| Top 50, 3 months daily | 5-8 min | ~50 | ~3,150 |

Rate limiting: 12 seconds between API calls (safe for free/basic tiers)

### Troubleshooting

#### Common Issues

1. **"Symbol not found in symbols table"**
   - Symbols must exist in the database symbols table first
   - Add missing symbols or use existing universe

2. **API Rate Limiting**
   - Increase `POLYGON_RATE_LIMIT_DELAY` environment variable
   - Check your Polygon.io subscription limits

3. **Database Connection Issues**
   - Verify `DATABASE_URI` format and credentials
   - Check PostgreSQL server status
   - Ensure TimescaleDB extension is available

4. **Memory Issues (Large Loads)**
   - Reduce batch size in configuration
   - Run loads during off-peak hours
   - Consider splitting large universes

#### Recovery Procedures

```bash
# Resume failed load
python src/jobs/historical_data_scheduler.py --universe top_50 --years 0.1

# Clean up duplicate data
# Use admin web interface -> Data Management -> Cleanup

# Reset job tracking
rm logs/.last_run_*
```

## Production Best Practices

### 1. Staging Environment
- Test all loads in staging first
- Use smaller symbol sets for testing
- Validate data quality before production

### 2. Backup Strategy
- Regular database backups before large loads
- Keep configuration files in version control
- Document custom symbol universes

### 3. Monitoring
- Set up alerts for job failures
- Monitor disk space (historical data grows quickly)  
- Track API usage against Polygon.io limits

### 4. Maintenance Windows
- Schedule large loads during off-hours
- Coordinate with system maintenance windows
- Plan for market holiday schedules

### 5. Disaster Recovery
- Document all custom configurations
- Maintain copies of symbol universe definitions
- Test restore procedures regularly

## Integration with TickStock

### Real-time Data Flow
1. **Historical Load** → Populates `ohlcv_daily` and `ohlcv_1min` tables
2. **Live WebSocket** → Appends real-time ticks and minute bars
3. **Pattern Detection** → Uses both historical and live data
4. **Backtesting** → Relies on historical depth for accurate results

### Data Quality
- Historical data provides baseline for pattern analysis
- Sufficient depth (1-5 years) required for statistical significance
- Regular refreshes ensure no gaps in recent data
- Minute data enables intraday pattern detection

This production setup ensures reliable, scalable historical data management with multiple execution options suitable for different operational requirements.