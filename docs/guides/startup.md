# TickStock Complete Startup Guide

**Quick Reference** - How to start the entire TickStock ecosystem

---

## Quick Start (Recommended)

**Single command starts everything:**

```bash
cd C:\Users\McDude\TickStockAppV2
python start_all_services.py
```

**Access Points:**
- **Web UI**: http://localhost:5000
- **TickStockPL API**: http://localhost:8080
- **Streaming Dashboard**: http://localhost:5000/streaming

---

## What Gets Started

| Service | Purpose | Port/Channel | Status |
|---------|---------|--------------|--------|
| **TickStockAppV2** | Web UI & Admin Interface | http://localhost:5000 | ✅ Required |
| **TickStockPL API** | HTTP API Server | http://localhost:8080 | ✅ Required |
| **TickStockPL DataLoader** | Historical Data Import Handler | Redis: `tickstock.jobs.data_load` | ✅ Required |
| **TickStockPL Streaming** | Intraday Real-time Processing | Active 9:30 AM - 4:00 PM ET | ✅ Required |

### Automatic Features

- ✅ **Daily Processing** - Runs at 4:10 PM ET automatically
- ✅ **Streaming Sessions** - Start at 9:30 AM, stop at 4:00 PM ET
- ✅ **Historical Imports** - Admin UI triggers via Redis pub-sub
- ✅ **Health Monitoring** - Real-time metrics on `tickstock:monitoring`
- ✅ **Pattern Detection** - Real-time pattern events on Redis channels
- ✅ **WebSocket Broadcasting** - Live updates to browser clients

### Stop All Services

Press **Ctrl+C** - All services shut down gracefully

---

## Prerequisites

### Required Infrastructure

1. **PostgreSQL + TimescaleDB** (Port 5432)
   - Database: `tickstock`
   - User: `app_readwrite`
   - Password: Set in `.env`

2. **Redis Server** (Port 6379)
   - Default: localhost:6379
   - Used for pub-sub messaging and caching

### Verify Dependencies

```bash
# Check PostgreSQL
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -U app_readwrite -d tickstock -c "SELECT 1"
# Expected: Returns "1"

# Check Redis
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); print(r.ping())"
# Expected: Returns "True"
```

### Python Environment

**CRITICAL: Both projects require separate virtual environments**

#### TickStockAppV2 Virtual Environment
```bash
cd C:\Users\McDude\TickStockAppV2

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

#### TickStockPL Virtual Environment (REQUIRED)
```bash
cd C:\Users\McDude\TickStockPL

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

**Why Separate Environments?**
- `start_all_services.py` launches TickStockPL services using TickStockPL's venv Python
- Each project has different dependency requirements (e.g., TickStockPL needs `websockets`, `apscheduler`)
- Missing TickStockPL venv will cause immediate startup failure with clear error messages

---

## Startup Sequence & Validation

When using `start_all_services.py`, startup follows this rigorous validation sequence:

### Phase 1: Pre-Flight Checks (Fail-Fast)
1. **TickStockPL Virtual Environment Validation**
   - Checks if `C:/Users/McDude/TickStockPL/venv/Scripts/python.exe` exists
   - Validates critical dependencies: `apscheduler`, `websockets`, `redis`, `pandas`
   - **ABORTS** startup if validation fails with clear error messages

2. **Infrastructure Validation**
   - Redis connectivity (localhost:6379) - **ABORTS** if not running
   - PostgreSQL service (localhost:5432) - **ABORTS** if not running
   - Port 5000 availability - **ABORTS** if port is in use and cannot be freed

### Phase 2: Service Launch & Health Checks
1. **TickStockAppV2** (Consumer)
   - Launches process
   - 7s initialization wait
   - 3s health check (verifies process still running)
   - **ABORTS** and shuts down all services if crashed

2. **TickStockPL DataLoader** (Historical Import Handler)
   - Launches process
   - 2s health check
   - **ABORTS** and shuts down all services if crashed

3. **TickStockPL API** (HTTP API Server)
   - Launches process on port 8080
   - 2s health check
   - **ABORTS** and shuts down all services if crashed

4. **TickStockPL Streaming** (Real-time Processing)
   - Launches process
   - 2s health check
   - **ABORTS** and shuts down all services if crashed

**Total startup time:** ~15-20 seconds (includes all validations)

### Startup Console Output

Look for these success messages:

```
[TickStockAppV2] Service started successfully
[TickStockPL DataLoader] Subscribed to tickstock.jobs.data_load
[TickStockPL DataLoader] Service started successfully
[TickStockPL API] Service started successfully
[TickStockPL Streaming] Service started successfully

SERVICES RUNNING
[OK] TickStockAppV2: http://localhost:5000
[OK] TickStockPL DataLoader: Listening on tickstock.jobs.data_load
[OK] TickStockPL API: http://localhost:8080
[OK] TickStockPL Streaming: Active (9:30 AM - 4:00 PM ET)
```

---

## Individual Services (Advanced)

### TickStockAppV2 Only
```bash
cd C:\Users\McDude\TickStockAppV2
python src/app.py
```
**Port:** 5000 | **Purpose:** Web UI, admin interface, WebSocket server

### TickStockPL API Server Only
```bash
cd C:\Users\McDude\TickStockPL
python start_api_server.py
```
**Port:** 8080 | **Purpose:** HTTP API endpoints for pattern/indicator retrieval

### TickStockPL Streaming Service Only
```bash
cd C:\Users\McDude\TickStockPL
python streaming_service.py
```
**Schedule:** Market hours only (9:30 AM - 4:00 PM ET) | **Purpose:** Intraday real-time processing

### TickStockPL DataLoader Only
```bash
cd C:\Users\McDude\TickStockPL
python -m src.jobs.data_load_handler
```
**Channel:** `tickstock.jobs.data_load` | **Purpose:** Process historical import jobs from admin UI

### Daily Processing Jobs
```bash
cd C:\Users\McDude\TickStockPL
python -m src.jobs.daily_pattern_job
# or
python -m src.jobs.daily_indicator_job
```
**Schedule:** Automatic at 4:10 PM ET | **Purpose:** Daily pattern/indicator processing

---

## Environment Configuration

### Required Settings (.env)

**Database:**
```bash
DATABASE_URI=postgresql://app_readwrite:LJI48rUEkUpe6e@127.0.0.1:5432/tickstock
```
**Note:** Use `127.0.0.1` not `localhost` (Windows DNS issue fix)

**Redis:**
```bash
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://127.0.0.1:6379/0
```

**Massive API:**
```bash
MASSIVE_API_KEY=your_api_key_here
POLYGON_RATE_LIMIT_DELAY=12  # Free tier (5 calls/min)
# For paid tier: POLYGON_RATE_LIMIT_DELAY=1
```

**Flask:**
```bash
FLASK_SECRET_KEY=your-secret-key-here
FLASK_PORT=5000
APP_ENVIRONMENT=development
```

### Optional Settings

**Streaming:**
```bash
STREAMING_ENABLED=true
STREAMING_BUFFER_ENABLED=true
STREAMING_BUFFER_INTERVAL=250  # ms
SYMBOL_UNIVERSE_KEY=market_leaders:top_500
STREAMING_PATTERN_MIN_CONFIDENCE=0.7
```

**Processing:**
```bash
DAILY_PROCESSING_ENABLED=true
```

**Logging:**
```bash
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/tickstock.log
LOG_DB_ENABLED=true
LOG_DB_SEVERITY_THRESHOLD=error
```

---

## Verification & Testing

### Quick Health Check

```bash
# Check TickStockAppV2
curl http://localhost:5000/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

# Check TickStockPL API
curl http://localhost:8080/health
# Expected: {"status": "healthy", ...}
```

### Integration Tests

```bash
# Run TickStockAppV2 integration tests
cd C:\Users\McDude\TickStockAppV2
python run_tests.py
# Expected: 2 tests passing (~30 seconds)

# Run TickStockPL tests
cd C:\Users\McDude\TickStockPL
python run_tests.py
# Expected: 9205/9230 tests passing (99.7%)
```

### Streaming Integration Test

```bash
# Test streaming events flow
cd C:\Users\McDude\TickStockAppV2
python tests/integration/test_streaming_quick.py
# Expected: Events published to Redis, received by TickStockAppV2
```

### Redis Channel Verification

```bash
# Check if TickStockAppV2 is subscribed to streaming channels
python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
channels = ['tickstock:streaming:health', 'tickstock:patterns:streaming']
result = r.execute_command('PUBSUB', 'NUMSUB', *channels)
print('Subscribers:', dict(zip(result[::2], result[1::2])))
"
# Expected: At least 1 subscriber per channel
```

---

## Troubleshooting

### Critical Startup Failures

#### Error: "TickStockPL virtual environment validation failed"

**Symptom:**
```
[VALIDATION] ❌ CRITICAL: TickStockPL Python not found
❌ STARTUP ABORTED: TickStockPL virtual environment validation failed
```

**Cause:** TickStockPL virtual environment doesn't exist or is incomplete

**Fix:**
```bash
cd C:/Users/McDude/TickStockPL
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

**Verify:**
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/python.exe --version
# Should return Python version
```

---

#### Error: "Missing dependencies in TickStockPL venv"

**Symptom:**
```
[VALIDATION] ❌ Missing: websockets - Required for WebSocket connections
[VALIDATION] ❌ CRITICAL: 1 missing dependencies in TickStockPL venv
```

**Cause:** Required packages not installed in TickStockPL virtual environment

**Fix:**
```bash
cd C:/Users/McDude/TickStockPL
venv\Scripts\pip install websockets apscheduler redis pandas
# Or reinstall all requirements:
venv\Scripts\pip install -r requirements.txt
```

**Verify:**
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/python.exe -c "import websockets; print('OK')"
# Should print "OK"
```

---

#### Error: "Redis not running"

**Symptom:**
```
❌ STARTUP ABORTED: Redis not running
REASON: Redis is REQUIRED for pub-sub communication between services
```

**Cause:** Redis server is not running on localhost:6379

**Fix (Docker):**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

**Fix (Windows Local):**
```bash
# Navigate to Redis installation directory
redis-server.exe
```

**Verify:**
```bash
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); print(r.ping())"
# Should print "True"
```

---

#### Error: "PostgreSQL not running"

**Symptom:**
```
❌ STARTUP ABORTED: PostgreSQL not running
REASON: PostgreSQL is REQUIRED for data storage and pattern detection
```

**Cause:** PostgreSQL service is not running on localhost:5432

**Fix (Windows):**
```powershell
Start-Service postgresql-x64-14
# Or check service name:
Get-Service postgresql*
```

**Fix (Linux):**
```bash
sudo systemctl start postgresql
```

**Verify:**
```bash
PGPASSWORD=LJI48rUEkUpe6e psql -h 127.0.0.1 -U app_readwrite -d tickstock -c "SELECT 1"
# Should return "1"
```

---

#### Error: "Service crashed during initialization"

**Symptom:**
```
[VALIDATION] ❌ CRITICAL: TickStockPL Streaming crashed during initialization
REASON: Service started but terminated unexpectedly
```

**Cause:** Service encountered an error and exited immediately (exit code 1)

**Diagnosis Steps:**
1. **Check error messages above** - Look for Python tracebacks or import errors
2. **Common causes:**
   - Missing Python module (e.g., `ModuleNotFoundError`)
   - Configuration error (e.g., invalid `.env` settings)
   - Port conflict (e.g., port 8080 already in use)
   - Database connection failure

**Example: Missing Module**
```
[TickStockPL Streaming] ModuleNotFoundError: No module named 'apscheduler'
```
**Fix:** Install missing module in TickStockPL venv
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/pip install apscheduler
```

---

### Services Won't Start

**Issue:** Port 5000 already in use

**Fix:**
```bash
# start_all_services.py automatically detects and kills processes on port 5000
python start_all_services.py
# Or manually:
powershell -c "Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1 | ForEach-Object {Stop-Process -Id $_ -Force}"
```

**Issue:** Multiple Python processes running

**Check:**
```bash
tasklist | findstr python
```

**Kill All:**
```bash
taskkill /F /IM python.exe
# Then restart: python start_all_services.py
```

---

### Database Connection Issues

**Issue:** Cannot connect to PostgreSQL

**Check connection string in .env:**
```bash
# Use 127.0.0.1 instead of localhost
DATABASE_URI=postgresql://app_readwrite:LJI48rUEkUpe6e@127.0.0.1:5432/tickstock
```

**Verify PostgreSQL is running:**
```bash
# Windows
powershell -c "Get-Service postgresql*"

# Linux
systemctl status postgresql
```

**Test connection:**
```bash
PGPASSWORD=LJI48rUEkUpe6e psql -h 127.0.0.1 -U app_readwrite -d tickstock -c "\dt"
# Should list tables
```

---

### Redis Connection Issues

**Issue:** Redis not running

**Check if Redis is running:**
```bash
# Docker
docker ps | grep redis

# Windows process
tasklist | findstr redis

# Test connection
python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); print('Connected' if r.ping() else 'Failed')"
```

**Start Redis (if using Docker):**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

**Connection string in .env:**
```bash
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

---

### DataLoader Not Receiving Jobs

**Issue:** Admin historical import hangs

**Diagnosis:**
```bash
# Check if DataLoader is subscribed
python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
result = r.execute_command('PUBSUB', 'NUMSUB', 'tickstock.jobs.data_load')
print('Subscribers:', result[1])
"
# Expected: 1 or more subscribers
```

**Fix:** Restart services
```bash
# Stop (Ctrl+C)
python start_all_services.py
# Look for: "[TickStockPL DataLoader] Subscribed to tickstock.jobs.data_load"
```

**Verify:**
```bash
cd C:\Users\McDude\TickStockAppV2
python tests/integration/test_dataloader_redis.py
# Expected: Shows DataLoader subscribed and processing test job
```

---

### Streaming Not Working

**Issue:** Streaming dashboard shows no events

**Check:**
1. Services are running (see startup console)
2. Market hours (9:30 AM - 4:00 PM ET on trading days)
3. Redis subscriptions active

**Verify subscriptions:**
```bash
python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
channels = [
    'tickstock:streaming:session_started',
    'tickstock:patterns:streaming',
    'tickstock:indicators:streaming'
]
for ch in channels:
    result = r.execute_command('PUBSUB', 'NUMSUB', ch)
    print(f'{ch}: {result[1]} subscribers')
"
```

**Test streaming manually:**
```bash
cd C:\Users\McDude\TickStockAppV2
python tests/integration/test_streaming_quick.py
# Should publish events to Redis
```

---

## Service Monitoring

### Check Running Services

```bash
# List Python processes
tasklist | findstr python

# Check ports
powershell -c "Get-NetTCPConnection -LocalPort 5000,8080 -ErrorAction SilentlyContinue | Select-Object LocalPort, State, OwningProcess"
```

### Redis Channel Activity

```bash
# Monitor all TickStock events (development only)
redis-cli PSUBSCRIBE "tickstock:*"

# Monitor specific channel
redis-cli SUBSCRIBE tickstock:streaming:health
```

### Service Logs

All service output is displayed in the `start_all_services.py` console. Look for:

- `[TickStockAppV2]` - Web application logs
- `[TickStockPL DataLoader]` - Historical import logs
- `[TickStockPL API]` - API server logs
- `[TickStockPL Streaming]` - Streaming service logs

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| **Start everything** | `cd TickStockAppV2 && python start_all_services.py` |
| **Stop everything** | Press Ctrl+C |
| **Health check** | `curl http://localhost:5000/health` |
| **Test integration** | `cd TickStockAppV2 && python run_tests.py` |
| **Test streaming** | `cd TickStockAppV2 && python tests/integration/test_streaming_quick.py` |
| **Check subscribers** | `redis-cli PUBSUB NUMSUB tickstock.jobs.data_load` |
| **Monitor events** | `redis-cli PSUBSCRIBE "tickstock:*"` |
| **View logs** | Check console output from `start_all_services.py` |
| **Kill processes** | `taskkill /F /IM python.exe` |

---

## Next Steps After Startup

1. **Access Web UI**: http://localhost:5000
2. **Login/Register**: Create admin account if first time
3. **Load Historical Data**: Admin → Historical Data → Select universe and load
4. **View Streaming Dashboard**: http://localhost:5000/streaming (during market hours)
5. **Monitor Health**: Subscribe to `tickstock:monitoring` Redis channel

---

## Related Documentation

### TickStockAppV2 Docs
- **Quick Start**: [docs/guides/quickstart.md](quickstart.md)
- **Configuration**: [docs/guides/configuration.md](configuration.md)
- **Testing**: [docs/guides/testing.md](testing.md)
- **Streaming Verification**: [docs/architecture/streaming-integration-verified.md](../architecture/streaming-integration-verified.md)
- **Integration Compliance**: [docs/architecture/tickstockpl-integration-compliance.md](../architecture/tickstockpl-integration-compliance.md)

### TickStockPL Docs (Reference)
- **Architecture**: `C:\Users\McDude\TickStockPL\docs\architecture\processing-pipeline.md`
- **Data Import**: `C:\Users\McDude\TickStockPL\docs\architecture\data-import-service.md`
- **Redis Integration Guide**: `C:\Users\McDude\TickStockPL\docs\planning\sprints\sprint33\REDIS_INTEGRATION_GUIDE_FOR_TICKSTOCKAPPV2.md`

---

## Summary

**To get started:**
1. Ensure PostgreSQL and Redis are running
2. Run: `python start_all_services.py`
3. Wait for "SERVICES RUNNING" message (~15 seconds)
4. Access: http://localhost:5000

**To stop:**
- Press Ctrl+C in the terminal running `start_all_services.py`

**For help:**
- Check service logs in console output
- Run health checks: `curl http://localhost:5000/health`
- Test integration: `python run_tests.py`

---

**Last Updated:** October 3, 2025
**Version:** Sprint 33 Complete
**Status:** ✅ All Services Operational
