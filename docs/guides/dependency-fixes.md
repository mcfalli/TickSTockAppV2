# TickStockPL Developer Instructions

**Date:** October 3, 2025
**Issue:** TickStockPL HTTP API Server crash on startup
**Root Cause:** Missing `aiohttp` dependency in TickStockPL virtual environment

---

## Issue Summary

The TickStockPL HTTP API server (`start_api_server.py`) is failing to start with:
```
ModuleNotFoundError: No module named 'aiohttp'
```

This causes the entire TickStock ecosystem to abort startup due to the new validation system detecting the crash within 2 seconds.

---

## Root Cause Analysis

**File:** `C:\Users\McDude\TickStockPL\src\api\api_server.py`
**Line 16:** `from aiohttp import web`

The API server implementation uses `aiohttp` for async HTTP handling, but this dependency was not included in `requirements/base.txt`.

**Impact:**
- TickStockPL API server crashes immediately after launch (exit code 1)
- TickStockAppV2 validation detects crash and shuts down all services
- No pattern detection, indicator processing, or streaming services available

---

## Fix Applied

### 1. ✅ Updated `requirements/base.txt`

**File:** `C:\Users\McDude\TickStockPL\requirements\base.txt`

**Added line 13:**
```python
aiohttp==3.9.1  # Async HTTP server for API endpoints (Sprint 33)
```

**Location:** After `itsdangerous==2.2.0`, before pattern detection dependencies section

### 2. ✅ Installed `aiohttp` in TickStockPL venv

```bash
C:/Users/McDude/TickStockPL/venv/Scripts/pip install aiohttp==3.9.1
```

**Dependencies installed:**
- `aiohttp==3.9.1`
- `aiosignal==1.4.0`
- `frozenlist==1.7.0`
- `multidict==6.6.4`
- `propcache==0.3.2`
- `yarl==1.20.1`

### 3. ✅ Updated startup validation

**File:** `C:\Users\McDude\TickStockAppV2\start_all_services.py`

Added `aiohttp` to critical dependency validation (line 108):
```python
critical_deps = {
    "apscheduler": "Required for streaming scheduler",
    "websockets": "Required for WebSocket connections",
    "aiohttp": "Required for HTTP API server",  # NEW
    "redis": "Required for pub-sub messaging",
    "pandas": "Required for data processing"
}
```

---

## Verification Steps

### 1. Test aiohttp installation
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/python.exe -c "import aiohttp; print('aiohttp OK')"
```
**Expected output:** `aiohttp OK`

### 2. Test API server startup manually
```bash
cd C:/Users/McDude/TickStockPL
venv\Scripts\python.exe start_api_server.py
```
**Expected output:**
```
============================================================
TickStockPL HTTP API Server
Sprint 33 Phase 4
============================================================

Starting API server on http://localhost:8080
Press Ctrl+C to stop

Available endpoints:
  POST   /api/processing/trigger-manual
  GET    /api/processing/status
  ...
```

### 3. Test integrated startup
```bash
cd C:/Users/McDude/TickStockAppV2
python start_all_services.py
```

**Expected validation output:**
```
[VALIDATION] ✅ TickStockPL Python found
[VALIDATION] ✅ Found: apscheduler
[VALIDATION] ✅ Found: websockets
[VALIDATION] ✅ Found: aiohttp
[VALIDATION] ✅ Found: redis
[VALIDATION] ✅ Found: pandas
...
[VALIDATION] ✅ TickStockPL API running (PID: XXXXX)
```

---

## Additional Dependencies for TickStockPL

If the API server still fails, check for these additional dependencies that `api_server.py` imports:

### Required modules (should already be in requirements):
- ✅ `asyncio` (Python stdlib)
- ✅ `json` (Python stdlib)
- ✅ `logging` (Python stdlib)
- ✅ `uuid` (Python stdlib)
- ✅ `datetime` (Python stdlib)
- ✅ `redis` (already in requirements)
- ✅ `psycopg2` (psycopg2-binary in requirements)
- ✅ `dotenv` (python-dotenv in requirements)

### TickStockPL internal imports (verify these files exist):
- `config.tickstockpl_config` → `C:\Users\McDude\TickStockPL\config\tickstockpl_config.py`
- `src.services.daily_processing_scheduler` → `C:\Users\McDude\TickStockPL\src\services\daily_processing_scheduler.py`
- `src.jobs.daily_import_job` → `C:\Users\McDude\TickStockPL\src\jobs\daily_import_job.py`
- `src.jobs.daily_indicator_job` → `C:\Users\McDude\TickStockPL\src\jobs\daily_indicator_job.py`
- `src.jobs.daily_pattern_job` → `C:\Users\McDude\TickStockPL\src\jobs\daily_pattern_job.py`

---

## For Future Reference

### Complete TickStockPL Dependency List

**Updated `requirements/base.txt` should now include:**

```python
# Core web/event dependencies
Flask==2.3.3
Werkzeug==2.3.7
python-dotenv==1.1.0
requests==2.31.0
websocket-client==1.8.0
redis==5.0.1
psycopg2-binary
SQLAlchemy
prometheus-client==0.17.0
PyJWT==2.10.1
itsdangerous==2.2.0
aiohttp==3.9.1  # NEW - Sprint 33 HTTP API server

# Pattern detection and data processing
pandas==2.3.2
numpy==2.3.2
scipy==1.16.1
matplotlib==3.10.5
pydantic>=2.0.0

# Sprint 33: Processing Engines Dependencies
apscheduler==3.10.4
pandas-market-calendars==4.4.1
pytz==2024.2
websockets==15.0.1  # NEW - Sprint 33 Streaming WebSocket connections
```

---

## Testing After Fix

### Test 1: Pre-flight Validation
```bash
cd C:/Users/McDude/TickStockAppV2
python start_all_services.py
```

Look for:
```
[VALIDATION] Checking TickStockPL virtual environment...
[VALIDATION] ✅ TickStockPL Python found
[VALIDATION] ✅ Found: apscheduler
[VALIDATION] ✅ Found: websockets
[VALIDATION] ✅ Found: aiohttp  # THIS IS NEW
[VALIDATION] ✅ Found: redis
[VALIDATION] ✅ Found: pandas
[VALIDATION] ✅ All critical TickStockPL dependencies verified
```

### Test 2: Service Health Checks
```
[VALIDATION] ✅ TickStockAppV2 running (PID: 12345)
[VALIDATION] ✅ TickStockPL DataLoader running (PID: 12346)
[VALIDATION] ✅ TickStockPL API running (PID: 12347)  # Should NOT crash now
[VALIDATION] ✅ TickStockPL Streaming running (PID: 12348)
```

### Test 3: API Endpoint Health Check
```bash
# Wait for services to start, then:
curl http://localhost:8080/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-03T...",
  "services": {
    "redis": "connected",
    "database": "connected",
    "scheduler": "active"
  }
}
```

---

## If Issues Persist

### Scenario 1: aiohttp installed but API still crashes

**Check Python version compatibility:**
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/python.exe --version
```
`aiohttp 3.9.1` requires Python 3.8+

### Scenario 2: Different import error

**Capture full error output:**
```bash
cd C:/Users/McDude/TickStockPL
venv\Scripts\python.exe start_api_server.py 2>&1 | tee api_error.log
```

Send `api_error.log` for analysis.

### Scenario 3: Port 8080 already in use

**Check what's using port 8080:**
```bash
powershell -c "Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue"
```

**Kill the process:**
```bash
powershell -c "Get-NetTCPConnection -LocalPort 8080 | Select-Object -ExpandProperty OwningProcess -First 1 | ForEach-Object {Stop-Process -Id $_ -Force}"
```

---

## Summary for TickStockPL Developer

**Action Required:**
1. ✅ **COMPLETED** - Add `aiohttp==3.9.1` to `requirements/base.txt`
2. ✅ **COMPLETED** - Install aiohttp in TickStockPL venv
3. ✅ **COMPLETED** - Update TickStockAppV2 validation to check for aiohttp
4. ⏳ **PENDING** - Verify API server starts successfully
5. ⏳ **PENDING** - Test full system integration

**No code changes required** - This is purely a dependency issue.

**Files Modified:**
- `C:\Users\McDude\TickStockPL\requirements\base.txt` (line 13 added)
- `C:\Users\McDude\TickStockAppV2\start_all_services.py` (line 108 updated)

**Next Steps:**
1. Restart services: `cd C:/Users/McDude/TickStockAppV2 && python start_all_services.py`
2. Verify all 4 services start and pass health checks
3. Test API endpoint: `curl http://localhost:8080/health`
4. Confirm streaming service operates during market hours (9:30 AM - 4:00 PM ET)

---

**Contact:** If API server continues to crash after these fixes, capture the full error output and check for additional missing dependencies or configuration issues.
