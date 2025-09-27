# TickStockAppV2 Quick Start Guide

**Version**: 3.0.0
**Last Updated**: September 26, 2025

## Prerequisites

### Required Services
1. **PostgreSQL + TimescaleDB** (Port 5432)
   - Database: `tickstock`
   - User: `app_readwrite`
   - Connection string in `.env`

2. **Redis Server** (Port 6379)
   - Default localhost:6379
   - Used for pub-sub messaging

### Python Requirements
- Python 3.8+
- Virtual environment recommended

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd TickStockAppV2
```

### 2. Setup Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Key variables:
DATABASE_URL=postgresql://app_readwrite:password@localhost:5432/tickstock
REDIS_HOST=localhost
REDIS_PORT=6379
FLASK_SECRET_KEY=your-secret-key-here
```

### 4. Database Setup
```bash
# Run migrations
python model_migrations_run.py upgrade

# Verify database
python scripts/dev_tools/database_integrity/util_test_db_integrity.py
```

## Starting the Application

### Option 1: Development Mode
```bash
# Start both Flask and background services
python start_both_services.py
```

### Option 2: Production Mode
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:8501 --worker-class eventlet app:app
```

### Option 3: Individual Components
```bash
# Start Flask only
python src/app.py

# Start monitoring subscriber (separate terminal)
python src/services/monitoring_subscriber.py
```

## Verification

### 1. Check Health Endpoint
```bash
curl http://localhost:8501/health
# Should return: {"status": "healthy", "database": "connected", "redis": "connected"}
```

### 2. Access Web Interface
- Open browser: http://localhost:8501
- Default login: Use registration to create account
- Admin setup: See administration guide

### 3. Verify Redis Connection
```bash
# Monitor Redis channels
redis-cli
> SUBSCRIBE tickstock:monitoring
```

## Integration with TickStockPL

### Starting Full Stack
1. Ensure TickStockAppV2 is running
2. Start TickStockPL service (separate repository)
3. Verify integration:
   ```bash
   # Check for events
   redis-cli
   > SUBSCRIBE tickstock.events.patterns
   ```

### Testing Integration
```bash
# Run integration tests
python tests/integration/run_integration_tests.py

# Test specific components
python tests/integration/test_tickstockpl_integration.py
```

## Common Operations

### User Management
```bash
# Create admin user
python scripts/admin/create_admin_user.py

# Reset password
python scripts/admin/reset_password.py --username=user@example.com
```

### Data Loading

#### Quick Data Load
```bash
# Load historical data via admin UI
# Navigate to: http://localhost:8501/admin/historical-data

# Or use command line
python src/api/rest/admin_historical_data.py
```

#### Historical Data Loading Options

**1. Load via Admin Interface** (Recommended)
- Navigate to `/admin/historical-data`
- Select universe (top_50, sp500, etc.)
- Choose timeframe and date range
- Click "Load Data" and monitor progress

**2. Command Line Loading**
```bash
# Load specific symbols
python scripts/load_historical.py --symbols AAPL,GOOGL,MSFT --years 1

# Load universe
python scripts/load_historical.py --universe sp500 --years 2

# Load with specific dates
python scripts/load_historical.py \
  --symbols AAPL \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --timeframe daily
```

**3. Programmatic Loading**
```python
from src.data.historical_loader import HistoricalLoader

loader = HistoricalLoader()

# Load daily data
loader.load_daily_data(
    symbols=['AAPL', 'GOOGL'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Load intraday (1-minute) data
loader.load_intraday_data(
    symbols=['AAPL'],
    days=30,  # Last 30 days
    timeframe='1min'
)
```

#### Data Sources
- **Primary**: Polygon.io API (requires API key in .env)
- **Test Data**: Synthetic generator for development
```bash
# Generate test data
python src/data/test_scenario_generator.py
```

### Monitoring
```bash
# View logs
tail -f logs/tickstock.log

# Monitor performance
python scripts/dev_tools/monitor_performance.py
```

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql -h localhost -p 5432 -U app_readwrite -d tickstock -c "SELECT 1;"

# Check PostgreSQL service
# Windows: services.msc
# Linux: systemctl status postgresql
```

### Redis Connection Issues
```bash
# Test Redis
redis-cli ping
# Should return: PONG

# Check Redis service
# Windows: services.msc
# Linux: systemctl status redis
```

### Port Conflicts
```bash
# Check port usage
netstat -an | findstr 8501  # Windows
netstat -an | grep 8501     # Linux/Mac

# Change port in .env
FLASK_PORT=8502
```

### Performance Issues
- Check cache hit rates: http://localhost:8501/api/monitoring/metrics
- Monitor Redis latency: `redis-cli --latency`
- Review slow queries: Check `logs/tickstock.log`

## Next Steps

1. **Configure Settings**: See [Configuration Guide](./configuration.md)
2. **Setup Authentication**: Configure user roles and permissions
3. **Load Market Data**: Import symbols and historical data
4. **Connect Data Sources**: Configure Polygon API or other providers
5. **Deploy Production**: See deployment documentation

## Support

- **Documentation**: `/docs` folder
- **Integration Tests**: `python run_tests.py`
- **Health Check**: http://localhost:8501/health
- **Admin Dashboard**: http://localhost:8501/admin (requires admin role)