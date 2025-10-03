# TickStock Service Dependencies & Integration Architecture

**Version:** Sprint 33 Complete
**Last Updated:** October 3, 2025

---

## Overview

TickStock.ai consists of **two separate Python projects** with **independent virtual environments** that communicate via **Redis pub-sub** and **HTTP APIs**. This document explains the critical dependencies, startup requirements, and inter-service communication patterns.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL:5432          Redis:6379          Port:5000/8080│
│  (TimescaleDB)         (Pub-Sub & Cache)      (HTTP Servers)│
└─────────────────────────────────────────────────────────────┘
                              ▲  ▲
                              │  │
        ┌─────────────────────┘  └────────────────────┐
        │                                              │
┌───────▼──────────────┐                    ┌─────────▼──────────────┐
│  TickStockAppV2      │                    │  TickStockPL           │
│  (CONSUMER)          │                    │  (PRODUCER)            │
├──────────────────────┤                    ├────────────────────────┤
│ Virtual Env: venv/   │◄─── HTTP API ─────│ Virtual Env: venv/     │
│                      │                    │                        │
│ Dependencies:        │◄─── Redis Pub ────│ Dependencies:          │
│ - Flask 2.3.3        │      Events       │ - Flask 2.3.3          │
│ - flask-socketio     │                   │ - websockets 15.0.1    │
│ - redis 5.0.1        │                   │ - apscheduler 3.10.4   │
│ - websocket-client   │─── Redis Sub ────►│ - redis 5.0.1          │
│ - eventlet           │    Channels       │ - pandas 2.3.2         │
│                      │                   │ - numpy 2.3.2          │
│ Port: 5000           │                   │ - scipy 1.16.1         │
│                      │                   │                        │
│ Services:            │                   │ Services:              │
│ ├─ Web UI            │                   │ ├─ HTTP API :8080      │
│ ├─ WebSocket Server  │                   │ ├─ DataLoader          │
│ ├─ Redis Subscriber  │                   │ ├─ Streaming           │
│ └─ Admin Dashboard   │                   │ └─ Daily Processing    │
└──────────────────────┘                   └────────────────────────┘
```

---

## Critical Dependencies

### Infrastructure Layer (REQUIRED)

| Component | Port | Purpose | Startup Validation |
|-----------|------|---------|-------------------|
| **PostgreSQL** | 5432 | TimescaleDB database for all data storage | ✅ ABORTS if not running |
| **Redis** | 6379 | Pub-sub messaging + caching | ✅ ABORTS if not running |
| **Port 5000** | 5000 | TickStockAppV2 web server | ✅ ABORTS if in use |
| **Port 8080** | 8080 | TickStockPL API server | ⚠️ Checked during API launch |

### Python Virtual Environments

#### TickStockAppV2 Virtual Environment
- **Location:** `C:\Users\McDude\TickStockAppV2\venv\`
- **Used by:** TickStockAppV2 web application only
- **Critical packages:** Flask, flask-socketio, eventlet, redis

#### TickStockPL Virtual Environment (CRITICAL)
- **Location:** `C:\Users\McDude\TickStockPL\venv\`
- **Used by:** TickStockPL API, DataLoader, Streaming services
- **Critical packages:**
  - `websockets==15.0.1` - WebSocket connection management
  - `apscheduler==3.10.4` - Streaming scheduler (market hours)
  - `redis==5.0.1` - Pub-sub event publishing
  - `pandas==2.3.2` - Data processing

**Why Separate?**
- `start_all_services.py` uses `sys.executable` for TickStockAppV2 (its own venv)
- TickStockPL services explicitly launched with `C:/Users/McDude/TickStockPL/venv/Scripts/python.exe`
- **Missing TickStockPL venv → Immediate startup abort with clear error**

---

## Service Startup Sequence

### Phase 1: Pre-Flight Validation (Fail-Fast)

```python
# 1. TickStockPL Virtual Environment Check
TICKSTOCKPL_PYTHON = Path("C:/Users/McDude/TickStockPL/venv/Scripts/python.exe")
if not TICKSTOCKPL_PYTHON.exists():
    ABORT("TickStockPL virtual environment not found")

# 2. Dependency Validation
for dep in ["apscheduler", "websockets", "redis", "pandas"]:
    subprocess.run([TICKSTOCKPL_PYTHON, "-c", f"import {dep}"])
    if returncode != 0:
        ABORT(f"Missing {dep} in TickStockPL venv")

# 3. Infrastructure Checks
if not redis_running():
    ABORT("Redis is REQUIRED for pub-sub communication")
if not postgres_running():
    ABORT("PostgreSQL is REQUIRED for data storage")
if port_5000_in_use():
    ABORT("Port 5000 is in use and cannot be freed")
```

### Phase 2: Service Launch with Health Checks

| Order | Service | Launch Command | Health Check | Abort on Failure |
|-------|---------|---------------|--------------|-----------------|
| 1 | **TickStockAppV2** | `sys.executable src/app.py` | 10s wait, verify running | ✅ YES |
| 2 | **TickStockPL DataLoader** | `TICKSTOCKPL_PYTHON -m src.jobs.data_load_handler` | 2s wait, verify running | ✅ YES |
| 3 | **TickStockPL API** | `TICKSTOCKPL_PYTHON start_api_server.py` | 2s wait, verify running | ✅ YES |
| 4 | **TickStockPL Streaming** | `TICKSTOCKPL_PYTHON streaming_service.py` | 2s wait, verify running | ✅ YES |

**Health Check Implementation:**
```python
def validate_service_health(process, service_name, timeout=3):
    time.sleep(timeout)
    if process.poll() is not None:
        # Process exited = crashed
        ABORT(f"{service_name} crashed during initialization (exit code: {process.poll()})")
        shutdown_all_services()
    return True
```

---

## Inter-Service Communication

### Redis Pub-Sub Channels

#### TickStockPL → TickStockAppV2 (Event Broadcasting)

| Channel | Event Type | Purpose |
|---------|-----------|---------|
| `tickstock:patterns:streaming` | Pattern detected | Real-time pattern notifications |
| `tickstock:indicators:streaming` | Indicator calculated | Real-time indicator updates |
| `tickstock:streaming:session_started` | Session start | Streaming session initiated |
| `tickstock:streaming:session_stopped` | Session stop | Streaming session ended |
| `tickstock:streaming:health` | Health metrics | Processing performance stats |
| `tickstock:monitoring` | System health | General system metrics |
| `tickstock.events.patterns` | Daily patterns | Daily batch pattern results |

#### TickStockAppV2 → TickStockPL (Job Commands)

| Channel | Event Type | Purpose |
|---------|-----------|---------|
| `tickstock.jobs.data_load` | Data load job | Admin triggers historical data import |
| `tickstock.jobs.backtest` | Backtest request | User initiates backtest |

### HTTP API Calls

**TickStockAppV2 → TickStockPL API**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `http://localhost:8080/health` | GET | API health check |
| `http://localhost:8080/patterns/{symbol}` | GET | Query pattern history |
| `http://localhost:8080/indicators/{symbol}` | GET | Query indicator values |

---

## Failure Scenarios & Recovery

### Scenario 1: TickStockPL venv Missing

**Error:**
```
[VALIDATION] ❌ CRITICAL: TickStockPL Python not found at C:/Users/McDude/TickStockPL/venv/Scripts/python.exe
❌ STARTUP ABORTED: TickStockPL virtual environment validation failed
```

**Impact:** Complete startup failure - no services launched

**Recovery:**
```bash
cd C:/Users/McDude/TickStockPL
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### Scenario 2: Missing `websockets` Dependency

**Error:**
```
[TickStockPL Streaming] ModuleNotFoundError: No module named 'websockets'
[VALIDATION] ❌ CRITICAL: TickStockPL Streaming crashed during initialization
```

**Impact:** Streaming service fails, all services shut down

**Recovery:**
```bash
C:/Users/McDude/TickStockPL/venv/Scripts/pip install websockets==15.0.1
```

### Scenario 3: Redis Not Running

**Error:**
```
❌ STARTUP ABORTED: Redis not running
REASON: Redis is REQUIRED for pub-sub communication between services
```

**Impact:** Startup aborted before launching any services

**Recovery:**
```bash
# Docker
docker run -d -p 6379:6379 --name redis redis:latest

# Windows
redis-server.exe
```

### Scenario 4: Service Crashes During Initialization

**Error:**
```
[VALIDATION] ✅ TickStockPL API running (PID: 12345)
[VALIDATION] ❌ CRITICAL: TickStockPL API crashed during initialization
❌ STARTUP ABORTED: TickStockPL API crashed during initialization
```

**Impact:** All services immediately shut down gracefully

**Recovery:**
1. Check service logs above the error for Python tracebacks
2. Identify root cause (missing module, config error, port conflict)
3. Fix issue and restart `python start_all_services.py`

---

## Validation Checklist

Before starting services, ensure:

- [ ] **TickStockAppV2 venv exists and dependencies installed**
  ```bash
  cd C:\Users\McDude\TickStockAppV2
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
  ```

- [ ] **TickStockPL venv exists and dependencies installed** (CRITICAL)
  ```bash
  cd C:\Users\McDude\TickStockPL
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
  ```

- [ ] **PostgreSQL running on port 5432**
  ```bash
  PGPASSWORD=LJI48rUEkUpe6e psql -h 127.0.0.1 -U app_readwrite -d tickstock -c "SELECT 1"
  ```

- [ ] **Redis running on port 6379**
  ```bash
  python -c "import redis; r = redis.Redis(host='127.0.0.1', port=6379); print(r.ping())"
  ```

- [ ] **Port 5000 available**
  ```bash
  powershell -c "Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue"
  # Should return nothing
  ```

- [ ] **Critical TickStockPL dependencies installed**
  ```bash
  C:/Users/McDude/TickStockPL/venv/Scripts/python.exe -c "import websockets, apscheduler, redis, pandas; print('All OK')"
  ```

---

## Quick Reference

### Start All Services
```bash
cd C:\Users\McDude\TickStockAppV2
python start_all_services.py
```

### Stop All Services
Press **Ctrl+C** - All services shut down gracefully

### Verify All Services Running
```bash
# Check processes
tasklist | findstr python

# Check ports
powershell -c "Get-NetTCPConnection -LocalPort 5000,8080 -ErrorAction SilentlyContinue"

# Check Redis subscribers
python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
result = r.execute_command('PUBSUB', 'NUMSUB', 'tickstock:patterns:streaming')
print(f'Subscribers: {result[1]}')
"
```

---

## Related Documentation

- [Startup Guide](../guides/startup.md) - Complete startup instructions
- [Architecture Overview](README.md) - System architecture
- [Redis Integration](redis-integration.md) - Pub-sub patterns
- [Configuration Guide](../guides/configuration.md) - Environment variables

---

**Last Updated:** October 3, 2025
**Sprint:** 33 Complete
**Status:** ✅ All services operational with robust validation
