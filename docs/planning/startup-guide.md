# TickStockAppV2 - Startup Guide

**Version**: Sprint 10 Integration Complete  
**Last Updated**: August 28, 2025  
**Status**: Production Ready ✅

---

## 🎯 Overview

This guide provides complete startup instructions for TickStockAppV2 after Sprint 10 integration. The application is now a lean UI consumer layer that integrates with TickStockPL backend services via Redis pub-sub architecture.

### System Architecture
- **TickStockAppV2**: UI Consumer Layer (Flask/SocketIO web interface)
- **TickStockPL**: Data Producer Backend (separate service)
- **Communication**: Redis pub-sub messaging for loose coupling
- **Database**: Shared TimescaleDB instance (`tickstock` database)

---

## 📋 Prerequisites

### Required Services
These services **MUST** be running before starting TickStockAppV2:

#### 1. PostgreSQL + TimescaleDB (Port 5433)
- **Database Name**: `tickstock`
- **User**: `app_readwrite`
- **Password**: `LJI48rUEkUpe6e`
- **Purpose**: Shared database for TickStockPL data consumption
- **Tables**: `symbols`, `ticks`, `ohlcv_1min`, `ohlcv_daily`, `events`

#### 2. Redis Server (Port 6379)
- **Host**: `localhost`
- **Port**: `6379`  
- **Database**: `0`
- **Purpose**: TickStockPL event consumption, job management, user sessions
- **Channels**: Pattern alerts, backtest progress, system health

### Optional Services
- **TickStockPL Backend**: For full functionality (backtesting, pattern detection)

---

## 🚀 Quick Start

### Step 1: Verify Prerequisites
```powershell
# Check PostgreSQL is running (should see port 5433 LISTENING)
netstat -an | findstr 5433

# Check Redis is running (should see port 6379 LISTENING)  
netstat -an | findstr 6379
```

### Step 2: Navigate to Project
```powershell
cd C:\Users\McDude\TickStockAppV2
```

### Step 3: Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
# OR
.\venv\Scripts\Activate
```

### Step 4: Start Application
```powershell
python src/app.py
# OR
.\venv\Scripts\python src/app.py
```

### Step 5: Access Dashboards
- **Main Dashboard**: http://localhost:5000
- **Health Monitor**: http://localhost:5000/health-dashboard  
- **Backtesting**: http://localhost:5000/backtest-dashboard
- **Pattern Alerts**: http://localhost:5000/pattern-alerts

---

## 🔧 Service Management

### Starting Redis (if needed)

#### Windows Service Method
```powershell
# Start Redis service (if installed as service)
sc start Redis

# Check Redis service status
sc query Redis
```

#### Manual Redis Method
```powershell
# Start Redis server manually (if you have Redis installed)
redis-server

# With custom config
redis-server redis.conf
```

#### Docker Method
```powershell
# Run Redis in Docker
docker run -d -p 6379:6379 --name tickstock-redis redis:latest

# Stop Redis container
docker stop tickstock-redis

# Start existing Redis container  
docker start tickstock-redis
```

### Starting PostgreSQL (if needed)
```powershell
# Check PostgreSQL service status
sc query postgresql-x64-13

# Start PostgreSQL service (usually auto-starts)
sc start postgresql-x64-13

# Alternative: Use Services manager (services.msc)
```

---

## ✅ Startup Success Indicators

### Expected Console Output
Look for these key messages during startup:

```
🚀 TICKSTOCK APPLICATION STARTING (Simplified)
STARTUP: Running startup sequence...
REDIS: Connected successfully to localhost:6379 db=0
TICKSTOCK-DB: Read-only connection pool initialized successfully
TICKSTOCKPL-SERVICES: WebSocket broadcaster initialized
TICKSTOCKPL-SERVICES: Pattern alert manager initialized
TICKSTOCKPL-SERVICES: Redis event subscriber started successfully
✅ TICKSTOCK APPLICATION READY
📊 Data Source: Synthetic
🔧 Redis: Connected
🌐 SocketIO: Enabled
STARTUP: Starting server on 0.0.0.0:5000
```

### Health Check Verification
1. **Visit Health Dashboard**: http://localhost:5000/health-dashboard
2. **Verify Green Status**: Database, Redis, and TickStockPL connections
3. **Check System Stats**: Connection pools, performance metrics

---

## 🚨 Troubleshooting

### Common Issues

#### "Redis connection failed"
```
STARTUP: Redis connection failed - continuing without Redis
```

**Solutions:**
1. **Verify Redis is running**: `netstat -an | findstr 6379`
2. **Start Redis service**: `sc start Redis`
3. **Check environment variables**: Ensure `REDIS_URL=redis://localhost:6379/0` in `.env`

#### "Database connection failed"  
```
TICKSTOCK-DB: Connection test failed: connection to server failed
```

**Solutions:**
1. **Verify PostgreSQL is running**: `netstat -an | findstr 5433`
2. **Check credentials**: Ensure `app_readwrite` user exists with correct password
3. **Test manual connection**: Use pgAdmin or psql to connect to `tickstock` database

#### "No symbols loading"
```
Failed to load jobs: Backtest service not available
Failed to load pattern subscriptions
```

**Expected Behavior**: This is normal when TickStockPL backend is not running. TickStockAppV2 will show these messages until TickStockPL is started.

#### Port Already in Use
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solutions:**
1. **Check running processes**: `netstat -ano | findstr 5000`
2. **Kill existing process**: `taskkill /PID <process_id> /F`
3. **Use different port**: Set `APP_PORT=5001` in `.env`

---

## ⚙️ Configuration

### Environment Variables (.env)
Key configuration settings in `.env` file:

```env
# Application
APP_HOST=0.0.0.0
APP_PORT=5000
APP_DEBUG=false
APP_ENVIRONMENT=development

# Database (Original TickStock database)
DATABASE_URI=postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock

# Redis Configuration (Sprint 10)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# TimescaleDB Configuration (Sprint 10)
TICKSTOCK_DB_HOST=localhost
TICKSTOCK_DB_PORT=5433
TICKSTOCK_DB_NAME=tickstock
TICKSTOCK_DB_USER=app_readwrite
TICKSTOCK_DB_PASSWORD=LJI48rUEkUpe6e

# Data Sources
USE_SYNTHETIC_DATA=true
USE_POLYGON_API=false
```

### Performance Tuning
```env
# Database Performance
DATABASE_SYNCH_AGGREGATE_SECONDS=10

# Synthetic Data Settings
SYNTHETIC_ACTIVITY_LEVEL=medium
SYNTHETIC_PER_SECOND_FREQUENCY=15.0

# Logging
LOG_CONSOLE_VERBOSE=false
LOG_FILE_ENABLED=true
```

---

## 📊 System Architecture Details

### Sprint 10 Services
The application initializes these Sprint 10 integration services:

1. **TickStockDatabase Service**
   - Read-only TimescaleDB connection
   - UI data queries for dropdowns and stats
   - Health monitoring integration

2. **RedisEventSubscriber**  
   - Consumes TickStockPL events from Redis
   - Pattern alerts, backtest progress, system health
   - Real-time WebSocket forwarding

3. **WebSocketBroadcaster**
   - Flask-SocketIO integration 
   - <100ms real-time browser updates
   - User connection management

4. **BacktestJobManager**
   - Complete job lifecycle management
   - Redis-based storage with TTL
   - Integration with TickStockPL via pub-sub

5. **PatternAlertManager**
   - User subscription and preference management
   - Alert filtering and delivery logic
   - Rate limiting and quiet hours

### Data Flow Architecture
```
TickStockPL → Redis Pub-Sub → TickStockAppV2 → WebSocket → Browser
```

---

## 🎯 Next Steps

### For Full Functionality
To see complete system operation with real data:

1. **Start TickStockPL Backend** (separate Python service)
2. **Verify Redis Pub-Sub** communication between services  
3. **Test End-to-End Flow**: Pattern detection → Redis → UI display

### For Development
- **Code Changes**: Automatic reload with `APP_DEBUG=true`
- **Database Changes**: Use pgAdmin to modify TimescaleDB schema
- **Redis Monitoring**: Use `redis-cli monitor` to watch pub-sub traffic

---

## 📞 Support

### Log Files
Application logs stored in: `logs/tickstock_YYYYMMDD_HHMMSS_*.log`

### Health Monitoring  
- **Health Dashboard**: Real-time system status
- **API Endpoint**: `GET /api/tickstockpl/health` 
- **Stats Endpoint**: `GET /stats` (login required)

### Documentation
- **Sprint 10 Summary**: `docs/planning/sprint10/sprint10-completed-summary.md`
- **Architecture Overview**: `docs/architecture_overview.md`
- **Project Structure**: `docs/project_structure.md`

---

**Last Updated**: August 28, 2025  
**Status**: ✅ Sprint 10 Complete - Ready for Production