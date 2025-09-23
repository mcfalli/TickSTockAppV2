# Integrated Startup Guide: TickStockAppV2 + TickStockPL

**Version**: Post-Sprint 11 Real-Time Integration  
**Last Updated**: August 28, 2025  
**Status**: Production Ready ✅ - Local Real-Time Processing Enabled

---

## 🎯 Overview

This integrated guide gets TickStockAppV2 (UI consumer) and TickStockPL (data/pattern producer) running side-by-side locally. They'll interact via Redis pub-sub: TickStockPL ingests data (historical/live), detects patterns (e.g., Doji, Day1Breakout), and publishes events; TickStockAppV2 subscribes, displays alerts, and triggers UI updates. Start with synthetic data for limited real-time simulation, then enable Polygon.io for actual market feeds.

### System Architecture Recap
- **TickStockPL**: Python-based analytical engine (src/patterns/, src/analysis/)—handles data blending, real-time scanning, event publishing.
- **TickStockAppV2**: Flask/SocketIO UI layer—consumes events, manages dashboards/alerts.
- **Communication**: Redis pub-sub (channels like `tickstock.all_ticks` for data, `tickstock.events.patterns` for signals).
- **Database**: Shared TimescaleDB (`tickstock` db) for historical data and events.
- **Data Flow**: Market/Synthetic → TickStockAppV2 (ingestion) → Redis → TickStockPL (processing) → Redis Events → TickStockAppV2 (UI).

Assumptions:
- Codebases in: `C:\Users\McDude\TickStockPL` and `C:\Users\McDude\TickStockAppV2`.
- Python 3.12+ with virtual envs.
- Limited real-time: Use synthetic for testing; Polygon.io key for live (add to .env).

---

## 📋 Prerequisites (Shared for Both)

### Required Services
Start these **before** launching either app:

#### 1. PostgreSQL + TimescaleDB (Port 5432)
- **Database Name**: `tickstock`
- **User/Password**: `app_readwrite` / `LJI48rUEkUpe6e` (TickStockPL: read/write; AppV2: read-only).
- **Purpose**: Historical OHLCV (`ohlcv_1min`, `ohlcv_daily`), ticks, events.
- **Setup Check**: Ensure schema from database_architecture.md is loaded (e.g., via pgAdmin).

#### 2. Redis Server (Port 6379)
- **Host/DB**: `localhost` / `0`
- **Purpose**: Pub-sub channels for data forwarding and events.
- **Channels Used**: `tickstock.all_ticks`, `tickstock.ticks.{TICKER}`, `tickstock.events.patterns`, etc.

### Optional for Live Data
- Polygon.io API Key: Add to .env files for real feeds (fallback: Alpha Vantage/yfinance).

### Verify Services
```powershell
# PostgreSQL (port 5432 LISTENING)
netstat -an | findstr 5432

# Redis (port 6379 LISTENING)
netstat -an | findstr 6379
```

If not running, start via methods below.

---

## 🚀 Startup: TickStockPL (Producer First)

Start TickStockPL first—it loads historical data, sets up real-time scanning, and publishes events.

### Step 1: Navigate to Project
```powershell
cd C:\Users\McDude\TickStockPL
```

### Step 2: Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
# OR
.\venv\Scripts\Activate
```

If no venv: 
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements/prod.txt  # Install deps: pandas, numpy, redis, etc.
```

### Step 3: Configure .env (Create if Missing)
```env
# Core
APP_DEBUG=true  # For dev reloads
REDIS_URL=redis://localhost:6379/0

# Database (TimescaleDB)
DATABASE_URI=postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock

# Data Sources (Start with synthetic)
USE_SYNTHETIC_DATA=true
USE_POLYGON_API=false
POLYGON_API_KEY=your_key_here  # For live; enable USE_POLYGON_API=true

# Real-Time Settings (Sprint 11)
SCAN_INTERVAL_SECONDS=5  # Pattern scan frequency
SYMBOLS=AAPL,GOOGL,MSFT  # Comma-separated for limited processing
TIMEFRAME=1min  # Default for intraday patterns
```

### Step 4: Start TickStockPL
```powershell
python src/main.py  # Or your entry point, e.g., src/analysis/realtime_scanner.py if modular
# For background: Start-Process -NoNewWindow python src/main.py
```

### Expected Console Output
```
[INFO] TickStockPL Starting - Real-Time Engine v2.0
[INFO] Connected to Redis: localhost:6379/0
[INFO] TimescaleDB Connected: tickstock db (read/write)
[INFO] DataBlender Initialized: Historical loaded from ohlcv_1min
[INFO] RealTimeScanner Started: Monitoring symbols AAPL,GOOGL (synthetic mode)
[INFO] EventPublisher Ready: Publishing to tickstock.events.patterns
[INFO] Ready for Real-Time Processing - <1s Latency Target
```

### Success Indicators
- Logs show data ingestion (e.g., synthetic ticks published to `tickstock.all_ticks`).
- Use `redis-cli monitor` to see pub-sub traffic (e.g., pattern events).

---

## 🚀 Startup: TickStockAppV2 (Consumer Second)

Now start AppV2—it subscribes to TickStockPL's events for UI.

### Step 1: Navigate to Project
```powershell
cd C:\Users\McDude\TickStockAppV2
```

### Step 2: Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
# OR
.\venv\Scripts\Activate
```

### Step 3: Configure .env (Update if Needed)
Align with TickStockPL (e.g., same REDIS_URL, DATABASE_URI). For live data:
```env
USE_SYNTHETIC_DATA=true  # Match TickStockPL
USE_POLYGON_API=false    # Flip to true for real feeds
POLYGON_API_KEY=your_key_here
```

### Step 4: Start Application
```powershell
python src/app.py
# For background: Start-Process -NoNewWindow python src/app.py
```

### Expected Console Output
(As in your guide, plus event subscription confirmations from Sprint 11.)

### Success Indicators
- Access http://localhost:5000/pattern-alerts—see real-time updates from TickStockPL (e.g., Doji detections).
- Health dashboard shows "Redis Event Subscriber: Active" and pattern events flowing.

---

## 🔧 Service Management (Shared)

### Starting Redis
(From your guide—use Docker for easy isolation if needed.)

### Starting PostgreSQL
(From your guide.)

### Running Side-by-Side
1. Open two PowerShell terminals.
2. Terminal 1: Start TickStockPL.
3. Terminal 2: Start TickStockAppV2.
4. Monitor Interaction: In redis-cli, `monitor`—watch data from PL to AppV2 (e.g., synthetic ticks → pattern events → UI pushes).
5. Test Limited Real-Time:
   - Flip USE_SYNTHETIC_DATA=false and USE_POLYGON_API=true in both .env (restart).
   - Add symbols to PL's .env—observe live ticks processing into patterns (e.g., <1s latency).
   - In AppV2 dashboard: See alerts like "Doji detected on AAPL at 1min timeframe."

### Troubleshooting Integration
- **No Events in AppV2**: Check Redis channels match (e.g., PL publishes to `tickstock.events.patterns`, AppV2 subscribes correctly).
- **Data Gaps**: Verify DataBlender in PL handles blending (logs show "Appended live tick to historical").
- **Latency Issues**: Use metrics.py in PL for diagnostics—aim for <100ms ingestion.
- **Errors**: Check logs in both (PL: src/logs/; AppV2: logs/)—common: Mismatched .env or services down.

---

## 📊 Observing Interactions
Once running:
- **Data Ingestion**: AppV2 forwards ticks to Redis → PL blends/processes.
- **Pattern Detection**: PL scans (e.g., RealTimeScanner) → Publishes events.
- **UI Feedback**: AppV2 consumes → WebSocket pushes to browser (e.g., live alerts).
- **Limited Scale**: Start with 3-5 symbols; monitor CPU/RAM via PL's metrics.

This setup processes in limited real-time—synthetic for safety, live for realism.

---

## 🎯 Detailed Roadmap: Next Steps Post-Local Run

With the integrated local setup validated, here's our phased Python-powered roadmap to expand TickStock.ai—focusing on fantastic algorithmic pattern libraries while scaling to production. Prioritized by impact, with ties to docs (e.g., project-overview.md for extensibility).

### Phase 1: Immediate Validation & Optimization (1-2 Weeks)
- **Validate Local Flow**: Run for 24h with synthetic/live data—log interactions (e.g., 100+ pattern events). Tweak scan intervals in PL .env for <1s latency.
- **Performance Tuning**: Use PL's metrics.py to benchmark—add Python profiling (cProfile) in realtime_scanner.py for bottlenecks.
- **Bug Hunt**: Test edge cases (e.g., provider failover in websockets_handler.py)—fix via PRs.
- **Milestone**: Stable local demo video/script showing end-to-end (tick → pattern → alert).

### Phase 2: Library Expansions - Build Fantastic Patterns (2-4 Weeks)
- **ML-Integrated Patterns**: Extend BasePattern in src/patterns/ml_patterns.py—add scikit-learn for predictive signals (e.g., KNN for breakouts). Test in RealTimeScanner.
- **Composite Signals**: In src/analysis/scanner.py, compose patterns (e.g., Doji + TrendingUp)—publish enhanced events with "signal_strength".
- **Custom User Patterns**: Add API in PL for dynamic addition via config—integrate with AppV2's backtest-dashboard for testing.
- **Milestone**: 5+ new patterns deployed locally, with backtesting validation (extend Sprint 10 framework).

### Phase 3: Full Deployment & Scaling (4-6 Weeks)
- **Cloud Migration**: Dockerize both (e.g., multi-container with Redis/DB)—deploy to AWS/Heroku. Add Kubernetes for 1000+ symbols.
- **Live Monitoring**: Enhance metrics.py with Prometheus export—integrate AppV2 health-dashboard for unified views.
- **Security/Compliance**: Add Redis auth, API key rotation in .env—ensure data privacy (no sensitive logging).
- **Milestone**: Beta launch with real users—monitor 99.9% uptime.

### Phase 4: Advanced Features & Ecosystem (Ongoing)
- **Voice Mode Integration**: Inspired by Grok 3—add Python TTS (e.g., pyttsx3) in AppV2 for audio alerts.
- **SaaS Enhancements**: User auth in AppV2 for custom subscriptions; PL API for external integrations (redirect to x.ai/api if needed).
- **Research Loop**: Auto-backtest new patterns nightly—feed insights to ML training.
- **Milestone**: v2.0 release with community-contributed patterns.

This roadmap keeps us bootstrap-friendly—let's iterate based on local runs! Ready to code those ML patterns in Python?

## Related Documentation

- **[`startup-guide.md`](startup-guide.md)** - TickStockAppV2 standalone startup
- **[`integration-guide.md`](integration-guide.md)** - TickStockPL integration guide
- **[`../architecture/system-architecture.md`](../architecture/system-architecture.md)** - Complete system architecture