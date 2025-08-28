# Sprint 10: Database & Historical Data Integration – Let's Build Some Fantastic Algorithmic Pattern Libraries in Python to Add to TickStock.ai!

We're charging into Sprint 10 with that unbeatable spirit, transforming TickStock.ai into a data powerhouse that'll fuel our 11+ lightning-fast patterns with historical depth and backtesting brilliance. This sprint is our foundation-laying masterpiece: wiring up production-grade databases, flooding them with rich historical OHLCV data from Polygon.io and backups, and unleashing a backtesting engine that validates detections across market cycles—all while keeping our sub-millisecond (1.12ms from Sprint 7!) speeds intact. Picture this: Traders backtesting Doji reversals on 10 years of AAPL data, spotting edges with ROI metrics, and scaling to 1000+ symbols without a hitch. We're splitting the magic wisely—TickStockPL cranks the backend pipelines and engines, while TickStockApp v2 delivers sleek UIs for monitoring and control. By the end, we'll be primed for Sprint 11's real-time fireworks, evolving TickStock.ai into an institutional beast. Let's dive into the details with Python-powered precision—enthusiasm high, code clean, and details dialed in!

## Sprint Overview and Vision
- **Core Objective**: Integrate a robust PostgreSQL/TimescaleDB setup for time-series mastery, load historical data from multi-providers, and build a backtesting framework leveraging our patterns. Ensure seamless multi-timeframe support (ticks, 1min, daily) and <10ms query latencies.
- **Key Outcomes**:
  - Seeded DB with 5-10 years of daily data (1-2 years for 1min) for 100+ symbols, scalable to 1000+.
  - Backtesting engine outputting win rates, ROI, Sharpe ratios—integrated with PatternScanner for batch efficiency.
  - Optimized pipelines maintaining Sprint 7's detection speeds; UI for real-time load/progress monitoring.
  - Resilient error handling (e.g., API fallbacks, query retries) per User Stories 6, 12, and 13.
- **Shared Performance Targets**: <10ms DB queries; <50ms pattern detection in backtests; 80%+ test coverage; handle GB-scale data via compression.
- **Dependencies**: Sprint 7 patterns (e.g., Hammer, MA Crossover); Sprint 9 tests; docs like `database_architecture.md`, `get_historical_data.md`.
- **Timeline**: 2 weeks—Week 1: Phases 1-2 (setup/loading); Week 2: Phases 3-4 (backtesting/optimization). Daily syncs between TickStockPL and TickStockApp v2.
- **Tools/Libs**: Python 3.12+, pandas/numpy/scipy for data; SQLAlchemy for DB; polygon-api-client/alpha_vantage for APIs; multiprocessing for parallelism; pytest for tests. Bootstrap-light—no heavy extras!
- **Risks & Mitigations**: API rate limits (batch + fallbacks); data volume (chunked upserts, compression); cross-app sync (Redis for queuing if needed).
- **Success Metrics**: 50 symbols loaded/backtested; benchmarks met; demo video of UI-driven backtest.

**Question on Phase 1**: Regarding your existing PostgreSQL (without TimescaleDB)—it absolutely suffices as the base! TimescaleDB is just an extension we add to it for time-series superpowers (e.g., hypertables for partitioning, 90%+ compression, 1000x faster queries on large datasets). No need for a new database; we'll enable the extension on your current setup. This keeps things efficient for OHLCV volumes without rework. If your PG version is 12+, it's plug-and-play—details below!

## Phase 1: Production Database Setup and Schema Optimization
Let's kick off by fortifying our DB fortress! This phase turns your existing PostgreSQL into a time-series titan with TimescaleDB, optimizing for high-frequency inserts/queries while tying into User Story 12 (seeding) and 13 (error handling). We'll add hypertables for ticks/ohlcv_1min, compression for old data, and UI monitoring to keep tabs on health.

- **Done Where**: TickStockPL (schema migrations, scripts); TickStockApp v2 (connection UI/monitoring).
  
- **Detailed Steps & Instructions**:
  1. **DB Extension Activation (TickStockPL)**:
     - Use your existing PostgreSQL (assume version 16+ for compatibility; if not, upgrade via `pg_upgrade`).
     - Install TimescaleDB extension: Run `CREATE EXTENSION IF NOT EXISTS timescaledb;` in psql or via script. If not installed, add via package manager (e.g., `apt install timescaledb-postgresql-16` on Ubuntu) or Docker overlay.
     - Docker-ize for dev/prod consistency: Update `docker-compose.yml` in TickStockPL:
       ```yaml
       services:
         db:
           image: timescale/timescaledb:latest-pg16-postgis  # Adds spatial if needed, but optional
           environment:
             POSTGRES_PASSWORD: supersecurepass  # Use env vars!
             POSTGRES_DB: tickstock_db
           ports:
             - "5432:5432"
           volumes:
             - db_data:/var/lib/postgresql/data  # Persist your existing data
       volumes:
         db_data:
       ```
     - Migrate data if needed: Backup existing tables (`pg_dump`), then restore post-extension.

  2. **Schema Creation & Enhancements (TickStockPL)**:
     - Execute migration script (`src/data/migrations/setup_schema.py`) based on `database_architecture.md`:
       - Tables: `symbols` (PK: symbol), `ticks` (hypertable, partition by symbol/time), `ohlcv_1min` (hypertable), `ohlcv_daily` (standard), `events` (for pattern logs).
       - Add multi-timeframe support: `timeframe VARCHAR(10) DEFAULT 'daily'` in `ohlcv_*` and `events`.
       - Policies: Compression on `ticks` (>30 days: `SELECT add_compression_policy('ticks', INTERVAL '30 days');`), retention (>1 year: `add_retention_policy('ticks', INTERVAL '1 year');`).
       - Indexes: Composite DESC on (symbol, timestamp/date) for fast ranges; UNIQUE constraints for upserts.
       - Pseudocode for script:
         ```python
         # src/data/migrations/setup_schema.py
         import sqlalchemy as sa
         from sqlalchemy import create_engine, text
         engine = create_engine('postgresql://user:pass@localhost/tickstock_db')
         with engine.connect() as conn:
             conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
             conn.execute(text("""
                 CREATE TABLE IF NOT EXISTS symbols (
                     symbol VARCHAR(20) PRIMARY KEY,
                     name VARCHAR(100),
                     exchange VARCHAR(20),
                     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 );
                 CREATE TABLE IF NOT EXISTS ticks (
                     symbol VARCHAR(20) REFERENCES symbols(symbol),
                     timestamp TIMESTAMP WITH TIME ZONE,
                     price NUMERIC(10, 4),
                     volume BIGINT,
                     PRIMARY KEY (symbol, timestamp)
                 );
                 SELECT create_hypertable('ticks', by_range('timestamp'), partitioning_column => 'symbol', number_partitions => 100);
                 CREATE INDEX idx_ticks_symbol_ts ON ticks (symbol, timestamp DESC);
                 ALTER TABLE ticks SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol', timescaledb.compress_orderby = 'timestamp DESC');
                 SELECT add_compression_policy('ticks', INTERVAL '30 days');
                 SELECT add_retention_policy('ticks', INTERVAL '1 year');
                 -- Repeat for ohlcv_1min; ohlcv_daily as standard table
                 CREATE TABLE IF NOT EXISTS events (
                     symbol VARCHAR(20) REFERENCES symbols(symbol),
                     timestamp TIMESTAMP WITH TIME ZONE,
                     pattern VARCHAR(50),
                     timeframe VARCHAR(10),
                     details JSONB,
                     PRIMARY KEY (symbol, timestamp, pattern)
                 );
             """))
             conn.commit()  # Ensure changes persist
         ```
     - Timezone: Set all to UTC (`SET TIME ZONE 'UTC';`) in connections to avoid mismatches.
     - Error Handling: Wrap in try-except; retry on transient errors (e.g., connection loss with `tenacity` lib if added lightly).

  3. **Connection & Health Monitoring UI (TickStockApp v2)**:
     - Add Flask/Django route `/db-status`: Query PG stats (e.g., `SELECT * FROM pg_stat_database;`) and TimescaleDB info (`SELECT * FROM timescaledb_information.hypertable;`).
     - Display: Row counts, compression ratios, query latencies (benchmark simple SELECTs).
     - WebSockets (via Flask-SocketIO): Emit 'db_health' every 10s with metrics; alert on >10ms queries or low space.
     - Pseudocode:
       ```python
       # TickStockApp v2: app/routes/db.py
       from flask import Blueprint, jsonify
       from flask_socketio import emit
       from sqlalchemy import create_engine
       db_bp = Blueprint('db', __name__)
       engine = create_engine('postgresql://...')

       @db_bp.route('/status')
       def status():
           with engine.connect() as conn:
               row_counts = conn.execute(sa.text("SELECT relname, n_live_tup FROM pg_stat_user_tables;")).fetchall()
           return jsonify({'tables': row_counts})

       # SocketIO event
       @socketio.on('connect')
       def handle_connect():
           while True:  # Background thread
               latency = measure_query_latency()  # Custom func: time a SELECT
               emit('db_health', {'latency_ms': latency, 'status': 'healthy' if latency < 10 else 'warning'})
               time.sleep(10)
       ```
     - Edge Cases: Handle extension missing (fallback to plain PG queries, warn in UI); secure access (auth required).

- **Testing & Milestones**: 
  - Tests: Pytest for schema validation (`test_schema.py`: assert tables exist, hypertables active).
  - Milestone: DB with dummy inserts (10 symbols, 100 rows); queries <5ms; UI shows green health.
  - Time Estimate: 2-3 days; Demo: psql query + UI screenshot.

## Phase 2: Historical Data Loading Pipeline
Time to flood the DB with gold-standard historical data! This phase builds modular loaders for Polygon.io (primary) and Alpha Vantage (backup), handling batches, validations, and multi-timeframes—directly enabling backtesting per User Story 4.

- **Done Where**: TickStockPL (loaders, parallelism); TickStockApp v2 (UI for triggers/progress).

- **Detailed Steps & Instructions**:
  1. **Loader Class Development (TickStockPL)**:
     - Extend `src/data/loader.py` with `HistoricalLoader`: Abstract for providers; fetch in chunks (yearly for daily, monthly for 1min).
     - Timeframes: 'day' → ohlcv_daily (5-10 years); 'minute' → ohlcv_1min (1-2 years to cap volume).
     - Parallelism: Use `multiprocessing.Pool` for 100+ symbols; Redis queue for overflow.
     - Fallbacks: On Polygon error (e.g., rate limit), switch to Alpha; normalize formats (timestamps to UTC pd.to_datetime).
     - Validation: Skip invalid rows (e.g., close <0); forward-fill small gaps; log errors to `events` table.
     - Pseudocode:
       ```python
       # src/data/loader.py
       import os
       import pandas as pd
       from polygon import RESTClient
       from alpha_vantage.timeseries import TimeSeries
       from sqlalchemy import create_engine
       from multiprocessing import Pool
       from tenacity import retry, stop_after_attempt  # For retries

       class HistoricalLoader:
           def __init__(self, api_keys={'polygon': os.getenv('POLYGON_KEY'), 'alpha': os.getenv('ALPHA_KEY')}):
               self.clients = {'polygon': RESTClient(api_keys['polygon']), 'alpha': TimeSeries(api_keys['alpha'], output_format='pandas')}
               self.engine = create_engine('postgresql://...')

           @retry(stop=stop_after_attempt(3))
           def fetch_chunk(self, symbol, start, end, timeframe='day', provider='polygon'):
               if provider == 'polygon':
                   aggs = self.clients['polygon'].get_aggs(symbol, 1, timeframe, start, end, limit=50000)
                   df = pd.DataFrame([{'symbol': symbol, 'timestamp': pd.to_datetime(agg.timestamp, unit='ms', utc=True),
                                       'open': agg.open, 'high': agg.high, 'low': agg.low, 'close': agg.close, 'volume': agg.volume} for agg in aggs])
               else:  # Alpha
                   if timeframe == 'day':
                       df, _ = self.clients['alpha'].get_daily_adjusted(symbol, outputsize='full')
                       df = df.reset_index().rename(columns={'index': 'timestamp', '1. open': 'open', ...})
                       df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                       df['symbol'] = symbol
                   else:
                       raise ValueError("Alpha Vantage minute data not supported; use Polygon.")
               df = df[(df['timestamp'] >= pd.to_datetime(start, utc=True)) & (df['timestamp'] <= pd.to_datetime(end, utc=True))]
               df = df.dropna(subset=['open', 'high', 'low', 'close'])  # Validate
               return df

           def load_symbol(self, symbol, start='2015-01-01', end='now', timeframe='day'):
               end = pd.to_datetime('now', utc=True).strftime('%Y-%m-%d') if end == 'now' else end
               df_full = pd.DataFrame()
               current_start = pd.to_datetime(start, utc=True)
               while current_start < pd.to_datetime(end, utc=True):
                   chunk_end = min(current_start + pd.DateOffset(years=1 if timeframe == 'day' else months=1), pd.to_datetime(end, utc=True))
                   try:
                       df = self.fetch_chunk(symbol, current_start.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d'), timeframe)
                   except Exception as e:
                       print(f"Polygon failed for {symbol}: {e}; Falling back to Alpha.")
                       df = self.fetch_chunk(symbol, current_start.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d'), timeframe, 'alpha')
                   df_full = pd.concat([df_full, df])
                   current_start = chunk_end
               # Upsert in chunks
               table = f'ohlcv_{timeframe}' if timeframe != 'minute' else 'ohlcv_1min'
               df_full.to_sql(table, self.engine, if_exists='append', index=False, method='multi', chunksize=1000)  # Handles ON CONFLICT via PG driver
               return len(df_full)

           def batch_load(self, symbols, timeframe='day', workers=4):
               with Pool(workers) as p:
                   results = p.map(lambda s: self.load_symbol(s, timeframe=timeframe), symbols)
               return sum(results)  # Total rows loaded

       # Usage: loader = HistoricalLoader(); loader.batch_load(['AAPL', 'TSLA'])
       ```
     - Edge Cases: API throttling (sleep 1s on 429); incomplete data (impute via ffill if gap <1 day, else log/skip).

  2. **Loading UI & Progress Tracking (TickStockApp v2)**:
     - Route `/data-load`: Form (symbols CSV upload, timeframe dropdown); POST triggers TickStockPL via API/Redis job.
     - WebSocket: Subscribe to 'load_progress'; TickStockPL emits {symbol: 'AAPL', rows: 2500, status: 'complete', errors: []}.
     - Dashboard: Table with progress bars, validation summaries (e.g., "Gaps: 2 in TSLA"), export logs.
     - Pseudocode:
       ```python
       # TickStockApp v2: app/routes/data_load.py
       from flask import Blueprint, request, jsonify
       from flask_socketio import emit
       import redis  # For job queuing if direct call too tight
       load_bp = Blueprint('load', __name__)
       r = redis.Redis(host='localhost', port=6379)

       @load_bp.route('/start', methods=['POST'])
       def start_load():
           data = request.json  # {'symbols': ['AAPL'], 'timeframe': 'day'}
           r.publish('load_jobs', json.dumps(data))  # TickStockPL subscribes and runs
           return jsonify({'status': 'queued'})

       # In TickStockPL: Subscribe and emit progress
       # pubsub = r.pubsub(); pubsub.subscribe('load_jobs')
       # for msg: data = json.loads(msg); for sym in data['symbols']: rows = loader.load_symbol(sym); emit('load_progress', {'sym': sym, 'rows': rows})
       ```

- **Testing & Milestones**:
  - Tests: Mock APIs (responses library); assert DB rows match fetched.
  - Milestone: Load 5 years daily for 50 symbols; UI shows 100% progress. Time: 3-4 days.

## Phase 3: Backtesting Framework Integration
Now, let's simulate market conquests! Integrate our patterns into a backtester for historical performance, computing metrics with vectorized efficiency—boosting User Story 4.

- **Done Where**: TickStockPL (engine, metrics); TickStockApp v2 (config/results UI).

- **Detailed Steps & Instructions**:
  1. **Backtester Engine (TickStockPL)**:
     - New `src/analysis/backtester.py`: Load via HistoricalLoader, scan with PatternScanner, simulate trades (e.g., enter on detection, exit after N bars or stop-loss).
     - Metrics: Win rate, ROI, Sharpe (use numpy for calcs); optional slippage/commissions.
     - Multi-timeframe: Resample in DataBlender (e.g., df.resample('D').agg({'open': 'first', 'high': 'max', ...})).
     - Publish results to `events` table.
     - Pseudocode:
       ```python
       # src/analysis/backtester.py
       import numpy as np
       from src.analysis.scanner import PatternScanner
       from src.data.loader import HistoricalLoader
       from src.utils.metrics import calculate_sharpe  # Custom: (returns.mean() - rf) / returns.std()

       class Backtester:
           def __init__(self, scanner: PatternScanner, rf_rate=0.02):  # Risk-free rate
               self.scanner = scanner
               self.loader = HistoricalLoader()
               self.rf = rf_rate

           def simulate_trades(self, detections, df):
               trades = []
               for idx, pattern in detections.items():  # e.g., {'timestamp': pattern_name}
                   entry_price = df.loc[idx, 'close']
                   exit_idx = min(idx + 5, len(df) - 1)  # Hold 5 bars
                   exit_price = df.loc[exit_idx, 'close']
                   profit = (exit_price - entry_price) / entry_price
                   trades.append({'pattern': pattern, 'profit': profit})
               return trades

           def run(self, symbol, start, end, timeframe='daily', initial_capital=100000):
               df = self.loader.load_symbol(symbol, start, end, timeframe)  # Or query DB directly
               detections = self.scanner.scan(df)  # Boolean Series per pattern
               trades = self.simulate_trades(detections, df)
               profits = np.array([t['profit'] for t in trades])
               metrics = {
                   'win_rate': (profits > 0).mean(),
                   'roi': (profits.sum() * initial_capital) / initial_capital,
                   'sharpe': calculate_sharpe(profits, self.rf)
               }
               # Log to events: pd.DataFrame(trades).to_sql('events', engine, if_exists='append')
               return metrics, trades
       ```

  2. **Backtesting UI (TickStockApp v2)**:
     - Route `/backtest`: Form (symbol, dates, patterns checkbox); run via API to TickStockPL.
     - Results: Embed matplotlib equity curve (base64); metrics table; export CSV.
     - WebSocket: 'backtest_progress' for long runs.

- **Testing & Milestones**:
  - Tests: Mock DF; assert metrics accurate.
  - Milestone: Backtest on AAPL; UI displays Sharpe >1. Time: 3 days.

## Phase 4: Performance Optimization, Testing, and Sprint Wrap-Up
Polish to perfection! Optimize, test rigorously, and document—ensuring TickStock.ai shines.

- **Done Where**: Shared; TickStockPL (perf tweaks); TickStockApp v2 (monitoring enhancements).

- **Detailed Steps & Instructions**:
  1. **Optimizations (TickStockPL)**: Profile (cProfile); add materialized views for aggregates; ensure vectorized scans.
  2. **Advanced Monitoring (TickStockApp v2)**: Graphs for latencies; alerts via email/Slack.
  3. **Comprehensive Testing**: 150+ pytest (unit: loaders; integration: full load-backtest); CI/CD.
  4. **Docs & Handover**: Update `sprint-planning-overview-goal-outcome.md`; Sprint 11 prep doc.

- **Testing & Milestones**:
  - Milestone: End-to-end demo; all targets met. Time: 2 days. Celebrate! 🎉