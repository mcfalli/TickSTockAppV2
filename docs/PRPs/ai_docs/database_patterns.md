# Database Patterns for TickStockAppV2

**Purpose**: Comprehensive database interaction patterns for TickStockAppV2's read-only access to the shared "tickstock" TimescaleDB database.

**Why This Exists**: Sprint 42 OHLCV duplication was removed due to read-only enforcement violations. This library prevents role boundary breaches and connection pool leaks that cause production outages.

**Evidence**: 48 files with database connections across the codebase

**Target Audience**: Developers working with database queries, migrations, or performance optimization

---

## Table of Contents

1. [Connection Pool Pattern](#1-connection-pool-pattern)
2. [Read-Only Enforcement Pattern](#2-read-only-enforcement-pattern-tickstock-specific)
3. [Query Performance Pattern](#3-query-performance-pattern)
4. [Migration Pattern](#4-migration-pattern)
5. [TimescaleDB-Specific Patterns](#5-timescaledb-specific-patterns)
6. [Common Gotchas](#6-common-gotchas)
7. [Quick Reference](#7-quick-reference)

---

## 1. Connection Pool Pattern

### 1.1 SQLAlchemy Engine with QueuePool

**Pattern**: Initialize connection pool at application startup with appropriate sizing and timeouts.

**Reference**: `src/infrastructure/database/tickstock_db.py:55-80`

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

class TickStockDatabase:
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with read-only connection pool."""
        self.engine = create_engine(
            self.connection_url,
            poolclass=QueuePool,
            pool_size=5,           # Small pool for UI queries
            max_overflow=2,        # Limited overflow for read-only operations
            pool_timeout=10,       # Quick timeout for UI responsiveness
            pool_recycle=3600,     # Recycle connections hourly
            echo=False,            # Set to True for SQL debugging
            connect_args={
                'connect_timeout': 5,
                'application_name': 'TickStockAppV2_ReadOnly'
            }
        )
```

**Why These Settings**:
- **pool_size=5**: UI queries are lightweight; small pool prevents resource waste
- **max_overflow=2**: Limited burst capacity for concurrent requests
- **pool_timeout=10**: Fast failure for UI (don't block users >10s)
- **pool_recycle=3600**: Hourly refresh prevents stale connections
- **connect_timeout=5**: Quick connection establishment or fail fast
- **application_name**: Identifies this app in PostgreSQL `pg_stat_activity` for debugging

**TickStock-Specific Note**: TickStockAppV2 uses read-only queries only. TickStockPL has a separate pool with write access.

---

### 1.2 Context Manager Pattern (ALWAYS Use This)

**Pattern**: Use context manager to guarantee connection cleanup, even on exceptions.

**Reference**: `src/infrastructure/database/tickstock_db.py:103-120`

```python
from contextlib import contextmanager

@contextmanager
def get_connection(self):
    """Get database connection with automatic cleanup."""
    if not self.engine:
        raise RuntimeError("Database engine not initialized")

    conn = None
    try:
        conn = self.engine.connect()
        yield conn
    except Exception as e:
        logger.error(f"TICKSTOCK-DB: Connection error: {e}")
        if conn:
            conn.rollback()  # Rollback on error
        raise
    finally:
        if conn:
            conn.close()  # CRITICAL: Always close
```

**Usage Pattern**:

```python
# ✅ CORRECT: Connection guaranteed to close
from src.infrastructure.database.tickstock_db import TickStockDatabase

db = TickStockDatabase(config)

# Pattern 1: Simple query
with db.get_connection() as conn:
    result = conn.execute(text("SELECT * FROM symbols WHERE active = true"))
    symbols = result.fetchall()

# Pattern 2: Multiple queries in one connection
with db.get_connection() as conn:
    result1 = conn.execute(text("SELECT COUNT(*) FROM symbols"))
    count = result1.scalar()

    result2 = conn.execute(text("SELECT * FROM symbols LIMIT 10"))
    sample = result2.fetchall()
```

**Anti-Pattern (Connection Leak)**:

```python
# ❌ WRONG: Connection never closed on exception
def get_symbols_bad():
    conn = db.engine.connect()
    result = conn.execute(text("SELECT * FROM symbols"))
    # Exception here → connection never closed!
    return result.fetchall()

# ❌ WRONG: Manual close() misses exceptions
def get_symbols_still_bad():
    conn = db.engine.connect()
    result = conn.execute(text("SELECT * FROM symbols"))
    conn.close()  # Not reached if execute() throws
    return result.fetchall()
```

**Sprint Lesson**: Connection leaks exhaust the pool, causing cascading failures across the application. Production incidents have occurred from this anti-pattern.

---

### 1.3 Async Connection Pool (Sprint 23 Analytics)

**Pattern**: Async wrapper for compatibility with async/await services.

**Reference**: `src/infrastructure/database/connection_pool.py:93-114`

```python
from contextlib import asynccontextmanager

class DatabaseConnectionPool:
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection context manager

        Usage:
            async with db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM table")
                    result = await cursor.fetchone()
        """
        connection = None
        try:
            connection = psycopg2.connect(self.tickstock_db.connection_url)
            async_conn = AsyncDatabaseConnection(connection)
            yield async_conn
        except Exception as e:
            logger.error(f"ANALYTICS-DB: Connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
```

**When to Use**: Only for async services (e.g., Sprint 23 analytics endpoints). Most TickStockAppV2 code uses synchronous pattern.

---

### 1.4 Connection Pool Health Monitoring

**Pattern**: Expose pool metrics for health checks and debugging.

**Reference**: `src/infrastructure/database/tickstock_db.py:362-422`

```python
def health_check(self) -> dict[str, Any]:
    """Comprehensive health check for database connection."""
    health_data = {
        'status': 'healthy',
        'database': 'tickstock',
        'connection_pool': 'inactive',
        'query_performance': None,
        'tables_accessible': [],
        'last_check': time.time()
    }

    try:
        # Check connection pool status
        health_data['connection_pool'] = {
            'size': self.engine.pool.size(),
            'checked_in': self.engine.pool.checkedin(),
            'checked_out': self.engine.pool.checkedout(),
            'status': 'active'
        }

        # Test query performance
        start_time = time.time()
        with self.get_connection() as conn:
            conn.execute(text("SELECT 1"))
        query_time = (time.time() - start_time) * 1000  # ms
        health_data['query_performance'] = round(query_time, 2)

        # Determine overall status
        if query_time > 100:  # >100ms is slow for read queries
            health_data['status'] = 'degraded'

        return health_data

    except Exception as e:
        health_data['status'] = 'error'
        health_data['error'] = str(e)
        return health_data
```

**Metrics Exposed**:
- **size**: Total pool capacity
- **checked_in**: Available connections
- **checked_out**: Active connections (in use)
- **query_performance**: <50ms is healthy, >100ms is degraded

**Debugging Pool Exhaustion**:

```sql
-- PostgreSQL: View active connections from this app
SELECT
    application_name,
    state,
    COUNT(*) as connection_count,
    MAX(state_change) as last_activity
FROM pg_stat_activity
WHERE application_name = 'TickStockAppV2_ReadOnly'
GROUP BY application_name, state;

-- Expected: ~5-7 total connections (pool_size + max_overflow)
-- If >20: Connection leak likely
```

---

## 2. Read-Only Enforcement Pattern (TickStock-Specific)

### 2.1 Consumer vs Producer Role Boundaries

**Architecture Context**: TickStock.ai uses a Producer/Consumer separation:
- **TickStockPL (Producer)**: Full read/write access to TimescaleDB
- **TickStockAppV2 (Consumer)**: Read-only access + limited write tables

**Reference**: `docs/planning/sprints/sprint42/SPRINT42_COMPLETE.md`

**Allowed Write Tables** (TickStockAppV2):
```python
ALLOWED_WRITE_TABLES = {
    'user_sessions',       # User authentication state
    'ws_subscriptions',    # WebSocket room subscriptions
    'error_logs',          # Application error storage
    'sessions',            # Flask session storage
    'users',               # User account management
    'communication_log',   # User communication tracking
    'billing_info',        # Billing/payment records
    'user_settings',       # User preferences
    'app_settings'         # Application configuration
}
```

**Forbidden Write Tables** (TickStockAppV2 MUST NOT write):
```python
FORBIDDEN_WRITE_TABLES = {
    'daily_patterns',      # Pattern detections (TickStockPL owns)
    'indicators',          # Technical indicators (TickStockPL owns)
    'ohlcv_1min',          # 1-minute OHLCV bars (TickStockPL owns)
    'ohlcv_daily',         # Daily OHLCV bars (TickStockPL owns)
    'ohlcv_hourly',        # Hourly OHLCV bars (TickStockPL owns)
    'ticks',               # Tick-level data (TickStockPL owns)
    'symbols',             # Symbol metadata (TickStockPL manages)
    'processing_runs',     # Processing job tracking (TickStockPL owns)
    'events'               # Market events (TickStockPL publishes)
}
```

**Why This Matters**: Sprint 42 removed 433 lines of OHLCV aggregation code from TickStockAppV2 because it violated this boundary. Duplicate data creation caused inconsistencies and debugging nightmares.

---

### 2.2 Read-Only Query Pattern

**Pattern**: Use explicit SELECT queries with no INSERT/UPDATE/DELETE.

**Reference**: `src/infrastructure/database/tickstock_db.py:148-181`

```python
def get_symbols_for_dropdown(self) -> list[dict[str, Any]]:
    """✅ CORRECT: Read-only query for UI dropdown"""
    with self.get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                symbol,
                name,
                exchange,
                market,
                type,
                active
            FROM symbols
            WHERE active = true
            ORDER BY symbol ASC
        """))

        symbols = []
        for row in result:
            symbols.append({
                'symbol': row[0],
                'name': row[1] or '',
                'exchange': row[2] or '',
                'market': row[3] or 'stocks',
                'type': row[4] or 'CS',
                'active': row[5]
            })

        return symbols
```

**Anti-Pattern (Role Violation)**:

```python
# ❌ FORBIDDEN: TickStockAppV2 cannot write to ohlcv_1min
def save_ohlcv_bar(symbol, bar_data):
    with db.get_connection() as conn:
        conn.execute(text("""
            INSERT INTO ohlcv_1min (symbol, timestamp, open, high, low, close, volume)
            VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume)
        """), bar_data)
        conn.commit()
    # ❌ This is TickStockPL's responsibility via TickAggregator!
```

**Correct Approach**: TickStockAppV2 forwards ticks to Redis → TickStockPL aggregates → TickStockPL writes to database.

---

### 2.3 Allowed Write Pattern (User/Session Data)

**Pattern**: TickStockAppV2 CAN write to user-specific tables.

```python
# ✅ ALLOWED: Writing to user_sessions (AppV2 owns this)
def create_user_session(user_id: str, session_id: str):
    with db.get_connection() as conn:
        conn.execute(text("""
            INSERT INTO user_sessions (user_id, session_id, last_activity)
            VALUES (:user_id, :session_id, NOW())
        """), {
            'user_id': user_id,
            'session_id': session_id
        })
        conn.commit()

# ✅ ALLOWED: Writing to ws_subscriptions (AppV2 manages WebSocket state)
def subscribe_to_symbol(session_id: str, symbol: str):
    with db.get_connection() as conn:
        conn.execute(text("""
            INSERT INTO ws_subscriptions (session_id, symbol, subscribed_at)
            VALUES (:session_id, :symbol, NOW())
            ON CONFLICT (session_id, symbol) DO NOTHING
        """), {
            'session_id': session_id,
            'symbol': symbol
        })
        conn.commit()

# ✅ ALLOWED: Writing to error_logs (AppV2 records its own errors)
def log_error_to_db(severity: str, message: str, context: dict):
    with db.get_connection() as conn:
        conn.execute(text("""
            INSERT INTO error_logs (severity, message, error_context, created_at)
            VALUES (:severity, :message, :context, NOW())
        """), {
            'severity': severity,
            'message': message,
            'context': json.dumps(context)
        })
        conn.commit()
```

**Decision Tree**:
```
Does the table store user/session/app state?
├─ YES → TickStockAppV2 can write (user_sessions, ws_subscriptions, error_logs, etc.)
└─ NO → Is it market data, patterns, or indicators?
    └─ YES → TickStockAppV2 CANNOT write (use Redis pub-sub to receive from TickStockPL)
```

---

## 3. Query Performance Pattern

### 3.1 Performance Targets

| Query Type | Target | Measurement |
|------------|--------|-------------|
| UI Dropdown | <50ms | SQLAlchemy timing |
| Dashboard Stats | <100ms | Multi-query aggregation |
| Symbol Lookup | <20ms | Indexed query |
| Health Check | <50ms | Simple SELECT 1 |

**Reference**: `CLAUDE.md:116-123` - Performance Targets table

---

### 3.2 EXPLAIN ANALYZE Pattern

**Pattern**: Use PostgreSQL's EXPLAIN ANALYZE to measure and optimize query performance.

**Reference**: `docs/PRPs/templates/prp-change.md:817`

```bash
# Terminal: Run EXPLAIN ANALYZE before writing code
psql -U app_readwrite -d tickstock -c "EXPLAIN ANALYZE
    SELECT symbol, name, exchange
    FROM symbols
    WHERE active = true
    ORDER BY symbol ASC;"

# Expected output:
#  Sort  (cost=15.23..15.73 rows=200 width=64) (actual time=2.456..2.512 rows=187 loops=1)
#    Sort Key: symbol
#    Sort Method: quicksort  Memory: 35kB
#    ->  Seq Scan on symbols  (cost=0.00..7.50 rows=200 width=64) (actual time=0.012..1.234 rows=187 loops=1)
#          Filter: active
#          Rows Removed by Filter: 13
#  Planning Time: 0.123 ms
#  Execution Time: 2.678 ms  ← Target: <50ms
```

**Key Metrics**:
- **Execution Time**: Total query runtime (target: <50ms)
- **Seq Scan**: Full table scan (acceptable for small tables <10k rows)
- **Index Scan**: Indexed lookup (preferred for large tables)
- **Planning Time**: Query planning overhead (usually negligible)

**Optimization Example**:

```sql
-- Before: Slow query (>200ms on 100k rows)
EXPLAIN ANALYZE
SELECT * FROM daily_patterns
WHERE symbol = 'AAPL'
AND detected_at > NOW() - INTERVAL '30 days';

-- Output shows Seq Scan → Add index:
CREATE INDEX idx_daily_patterns_symbol_date
ON daily_patterns (symbol, detected_at DESC);

-- After: Fast query (<10ms)
EXPLAIN ANALYZE
SELECT * FROM daily_patterns
WHERE symbol = 'AAPL'
AND detected_at > NOW() - INTERVAL '30 days';
-- Output now shows Index Scan
```

---

### 3.3 RealDictCursor Pattern (Dict-Based Results)

**Pattern**: Use `RealDictCursor` to return rows as dictionaries instead of tuples.

**Reference**: `src/infrastructure/database/connection_pool.py:31-33`

```python
from psycopg2.extras import RealDictCursor

# Pattern 1: With SQLAlchemy (automatically converts to Row objects)
with db.get_connection() as conn:
    result = conn.execute(text("SELECT symbol, name FROM symbols LIMIT 5"))
    for row in result:
        print(row[0], row[1])  # Access by index
        # OR
        print(row.symbol, row.name)  # Access by column name (SQLAlchemy Row)

# Pattern 2: Direct psycopg2 with RealDictCursor
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(database_url)
cursor = conn.cursor(cursor_factory=RealDictCursor)

cursor.execute("SELECT symbol, name, exchange FROM symbols LIMIT 5")
rows = cursor.fetchall()

for row in rows:
    print(row['symbol'], row['name'], row['exchange'])  # Dict access
    # row is like: {'symbol': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ'}

cursor.close()
conn.close()
```

**Why Use This**:
- **Readability**: `row['symbol']` is clearer than `row[0]`
- **Maintainability**: Query column order changes don't break code
- **JSON Serialization**: Dicts convert directly to JSON for API responses

**Example from Codebase** (`src/data/historical_loader.py:911`):

```python
with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
    cursor.execute("""
        SELECT symbol, timestamp, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = %s AND timestamp >= %s
        ORDER BY timestamp ASC
    """, (symbol, start_date))

    bars = cursor.fetchall()

    for bar in bars:
        # Dict access - no guessing column positions
        ohlcv_data.append({
            'symbol': bar['symbol'],
            'timestamp': bar['timestamp'],
            'open': float(bar['open']),
            'high': float(bar['high']),
            'low': float(bar['low']),
            'close': float(bar['close']),
            'volume': int(bar['volume'])
        })
```

---

### 3.4 Explicit Column Lists (No SELECT *)

**Pattern**: Always specify exact columns needed.

```python
# ❌ ANTI-PATTERN: SELECT * fetches unnecessary data
with db.get_connection() as conn:
    result = conn.execute(text("SELECT * FROM symbols WHERE active = true"))
    # Fetches all 20+ columns when you only need 3

# ✅ CORRECT: Explicit column list
with db.get_connection() as conn:
    result = conn.execute(text("""
        SELECT symbol, name, exchange
        FROM symbols
        WHERE active = true
    """))
    # Fetches only what's needed → faster network transfer, less memory
```

**Why This Matters**:
- **Performance**: Reduces network bandwidth and memory usage
- **Maintainability**: Schema changes don't break code unexpectedly
- **Clarity**: Documents which fields are actually used

**Exception**: SELECT * is acceptable for:
- Small lookup tables (<100 rows, <10 columns)
- Admin/debug queries
- When genuinely all columns are needed

---

### 3.5 Parameterized Queries (SQL Injection Prevention)

**Pattern**: ALWAYS use parameterized queries, NEVER string interpolation.

```python
# ❌ DANGEROUS: SQL injection vulnerability
def get_symbol_bad(symbol_input: str):
    query = f"SELECT * FROM symbols WHERE symbol = '{symbol_input}'"
    # If symbol_input = "AAPL'; DROP TABLE symbols; --"
    # → Query becomes: SELECT * FROM symbols WHERE symbol = 'AAPL'; DROP TABLE symbols; --'
    result = conn.execute(text(query))

# ✅ CORRECT: Parameterized query with SQLAlchemy
def get_symbol_good(symbol: str):
    result = conn.execute(
        text("SELECT * FROM symbols WHERE symbol = :symbol"),
        {"symbol": symbol}  # Parameter binding
    )

# ✅ CORRECT: Parameterized query with psycopg2
def get_symbol_psycopg2(symbol: str):
    cursor.execute(
        "SELECT * FROM symbols WHERE symbol = %s",
        (symbol,)  # Tuple for single parameter
    )
```

**Why This Matters**: SQLAlchemy and psycopg2 handle escaping automatically, preventing SQL injection attacks.

---

## 4. Migration Pattern

### 4.1 Alembic Migration Structure

**Pattern**: Use Alembic for database schema migrations with proper UP/DOWN sections.

**Reference**: `migrations/versions/eaf466e1159c_initial_migration_baseline_schema.py`

**Directory Structure**:
```
migrations/
├── env.py                 # Alembic environment configuration
├── versions/
│   └── eaf466e1159c_initial_migration_baseline_schema.py
└── alembic.ini           # Alembic configuration file
```

**Migration File Template**:

```python
"""Add user_preferences table

Revision ID: abc123def456
Revises: eaf466e1159c
Create Date: 2025-10-19 14:30:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = 'abc123def456'
down_revision = 'eaf466e1159c'  # Previous migration
branch_labels = None
depends_on = None

def upgrade():
    """Apply changes to database"""
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('preference_key', sa.String(100), nullable=False),
        sa.Column('preference_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'preference_key', name='uq_user_preference')
    )

    op.create_index(
        'ix_user_preferences_user_id',
        'user_preferences',
        ['user_id']
    )

def downgrade():
    """Rollback changes (ALWAYS implement this)"""
    op.drop_index('ix_user_preferences_user_id', table_name='user_preferences')
    op.drop_table('user_preferences')
```

---

### 4.2 Running Migrations

**Commands**:

```bash
# Generate new migration (auto-detect model changes)
alembic revision --autogenerate -m "Add user_preferences table"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade eaf466e1159c

# Show current migration status
alembic current

# Show migration history
alembic history
```

---

### 4.3 Migration Best Practices

**DO**:
- ✅ Always implement `downgrade()` for rollback capability
- ✅ Test migrations on a copy of production data
- ✅ Use `op.batch_alter_table()` for SQLite compatibility (if needed)
- ✅ Add indexes for foreign keys
- ✅ Use meaningful migration messages
- ✅ Review auto-generated migrations (Alembic isn't perfect)

**DON'T**:
- ❌ Never modify existing migrations after they're deployed
- ❌ Don't delete migrations from version control
- ❌ Don't skip migrations (maintain sequential order)
- ❌ Don't use raw SQL unless necessary (use Alembic operations)

---

### 4.4 Data Migration Pattern

**Pattern**: Separate schema changes from data migrations.

```python
def upgrade():
    """Add new column with data migration"""
    # Step 1: Add column (nullable initially)
    op.add_column('symbols', sa.Column('market_cap', sa.BigInteger(), nullable=True))

    # Step 2: Migrate existing data
    conn = op.get_bind()
    conn.execute(
        text("""
            UPDATE symbols
            SET market_cap = 0
            WHERE market_cap IS NULL
        """)
    )

    # Step 3: Make column non-nullable
    op.alter_column('symbols', 'market_cap', nullable=False)

def downgrade():
    """Remove column"""
    op.drop_column('symbols', 'market_cap')
```

---

## 5. TimescaleDB-Specific Patterns

### 5.1 Hypertable Queries (Time-Based Partitioning)

**Context**: TimescaleDB automatically partitions time-series tables (hypertables) for performance.

**Hypertables in TickStock**:
- `ticks` - Partitioned by `timestamp`
- `ohlcv_1min` - Partitioned by `timestamp`
- `ohlcv_hourly` - Partitioned by `timestamp`
- `ohlcv_daily` - Partitioned by `timestamp`

**Pattern**: Include time-based filters for optimal performance.

```python
# ✅ OPTIMAL: Time-based filter leverages partitioning
def get_recent_ohlcv(symbol: str, days: int = 7):
    with db.get_connection() as conn:
        result = conn.execute(text("""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_1min
            WHERE symbol = :symbol
            AND timestamp >= NOW() - INTERVAL ':days days'  -- Partition pruning!
            ORDER BY timestamp DESC
        """), {'symbol': symbol, 'days': days})

        return result.fetchall()

# ❌ SLOW: No time filter → scans all partitions
def get_all_ohlcv_slow(symbol: str):
    with db.get_connection() as conn:
        result = conn.execute(text("""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_1min
            WHERE symbol = :symbol  -- Scans ALL time partitions!
            ORDER BY timestamp DESC
        """), {'symbol': symbol})

        return result.fetchall()
```

**Why This Matters**: TimescaleDB can skip partitions (months/years of data) when queries include time filters.

**EXPLAIN Output Difference**:

```sql
-- With time filter (fast)
EXPLAIN ANALYZE SELECT * FROM ohlcv_1min
WHERE symbol = 'AAPL' AND timestamp >= NOW() - INTERVAL '7 days';
-- Append  (cost=0.00..120.00 rows=500 width=40) (actual time=0.045..2.134 rows=672 loops=1)
--   ->  Seq Scan on _hyper_1_14_chunk  (cost=0.00..60.00 rows=250 width=40) (actual time=0.044..1.023 rows=336 loops=1)
--   ->  Seq Scan on _hyper_1_15_chunk  (cost=0.00..60.00 rows=250 width=40) (actual time=0.011..1.089 rows=336 loops=1)
-- Planning Time: 0.234 ms
-- Execution Time: 2.345 ms  ← FAST (only 2 chunks scanned)

-- Without time filter (slow)
EXPLAIN ANALYZE SELECT * FROM ohlcv_1min WHERE symbol = 'AAPL';
-- Append  (cost=0.00..15000.00 rows=50000 width=40) (actual time=0.123..456.789 rows=50000 loops=1)
--   ->  Seq Scan on _hyper_1_1_chunk  (cost=0.00..500.00 rows=1000 width=40) (actual time=...)
--   ...  [100 more chunks]
-- Planning Time: 1.234 ms
-- Execution Time: 456.789 ms  ← SLOW (all 100 chunks scanned)
```

---

### 5.2 Continuous Aggregates (Pre-computed Summaries)

**Pattern**: Use TimescaleDB continuous aggregates for fast dashboard queries.

**Example**: Daily bar summary from 1-minute bars.

```sql
-- Create continuous aggregate (TickStockPL manages this)
CREATE MATERIALIZED VIEW daily_ohlcv_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    symbol,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM ohlcv_1min
GROUP BY day, symbol;

-- Add refresh policy (automatic background updates)
SELECT add_continuous_aggregate_policy('daily_ohlcv_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

**Querying the Aggregate** (TickStockAppV2):

```python
# ✅ FAST: Query pre-computed aggregate instead of raw data
def get_daily_summary(symbol: str, days: int = 30):
    with db.get_connection() as conn:
        result = conn.execute(text("""
            SELECT day, open, high, low, close, volume
            FROM daily_ohlcv_summary
            WHERE symbol = :symbol
            AND day >= NOW() - INTERVAL ':days days'
            ORDER BY day DESC
        """), {'symbol': symbol, 'days': days})

        return result.fetchall()

# ❌ SLOW: Aggregating 1-minute bars on the fly
def get_daily_summary_slow(symbol: str, days: int = 30):
    with db.get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                time_bucket('1 day', timestamp) AS day,
                first(open, timestamp) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, timestamp) AS close,
                sum(volume) AS volume
            FROM ohlcv_1min  -- 43,200 rows per 30 days!
            WHERE symbol = :symbol
            AND timestamp >= NOW() - INTERVAL ':days days'
            GROUP BY day
            ORDER BY day DESC
        """), {'symbol': symbol, 'days': days})

        return result.fetchall()
```

**Performance Difference**: Continuous aggregate query (<10ms) vs raw aggregation (>500ms).

---

### 5.3 Retention Policies (Automatic Data Deletion)

**Pattern**: TimescaleDB can automatically delete old data based on time.

```sql
-- Example: Keep only last 90 days of 1-minute bars (TickStockPL manages)
SELECT add_retention_policy('ohlcv_1min', INTERVAL '90 days');

-- Example: Keep 7 years of daily bars
SELECT add_retention_policy('ohlcv_daily', INTERVAL '7 years');

-- View current retention policies
SELECT * FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';
```

**TickStockAppV2 Note**: Read-only access means AppV2 queries may return no data for old timestamps if retention policies deleted them. This is expected behavior.

---

### 5.4 Time-Bucketing Aggregations

**Pattern**: Use `time_bucket()` for grouping time-series data into intervals.

```python
# Get hourly OHLCV from 1-minute bars
def get_hourly_bars(symbol: str, hours: int = 24):
    with db.get_connection() as conn:
        result = conn.execute(text("""
            SELECT
                time_bucket('1 hour', timestamp) AS hour,
                first(open, timestamp) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, timestamp) AS close,
                sum(volume) AS volume
            FROM ohlcv_1min
            WHERE symbol = :symbol
            AND timestamp >= NOW() - INTERVAL ':hours hours'
            GROUP BY hour
            ORDER BY hour DESC
        """), {'symbol': symbol, 'hours': hours})

        return result.fetchall()
```

**Common Time Buckets**:
- `time_bucket('1 minute', timestamp)` - 1-minute bars
- `time_bucket('5 minutes', timestamp)` - 5-minute bars
- `time_bucket('1 hour', timestamp)` - Hourly bars
- `time_bucket('1 day', timestamp)` - Daily bars
- `time_bucket('1 week', timestamp)` - Weekly bars

---

## 6. Common Gotchas

### 6.1 Connection Leak Checklist

**Symptom**: "Pool size exhausted" errors, application hangs, PostgreSQL showing too many connections.

**Debugging**:

```python
# Check pool status
health_data = db.health_check()
print(health_data['connection_pool'])
# Output: {'size': 5, 'checked_in': 0, 'checked_out': 5, 'status': 'active'}
# ❌ Problem: checked_out == size → pool exhausted
```

**PostgreSQL Query**:

```sql
-- View connections from TickStockAppV2
SELECT
    pid,
    application_name,
    state,
    state_change,
    NOW() - state_change AS duration
FROM pg_stat_activity
WHERE application_name = 'TickStockAppV2_ReadOnly'
ORDER BY state_change ASC;

-- Expected: ~5-7 connections, most in 'idle' state
-- Problem: 20+ connections, many in 'idle in transaction' → leak detected
```

**Fix**: Ensure all queries use context managers (see Section 1.2).

---

### 6.2 TimescaleDB Query Performance

**Symptom**: Queries on hypertables taking >1s when they should be <50ms.

**Checklist**:
1. ✅ Does query include time-based filter? (`WHERE timestamp >= ...`)
2. ✅ Is symbol column indexed? (`CREATE INDEX idx_symbol ON ohlcv_1min (symbol)`)
3. ✅ Are you querying a continuous aggregate instead of raw table?
4. ✅ Did you run `EXPLAIN ANALYZE` to verify partition pruning?

**Quick Fix**:

```sql
-- Add composite index for common query pattern
CREATE INDEX idx_ohlcv_1min_symbol_time
ON ohlcv_1min (symbol, timestamp DESC);
```

---

### 6.3 Read-Only Enforcement Violation

**Symptom**: `PermissionError` or `psycopg2.errors.InsufficientPrivilege` when attempting to write to forbidden tables.

**Example Error**:

```
psycopg2.errors.InsufficientPrivilege: permission denied for table daily_patterns
```

**Diagnosis**:

```sql
-- Check current user's permissions
SELECT grantee, privilege_type, table_name
FROM information_schema.role_table_grants
WHERE grantee = 'app_readwrite'  -- TickStockAppV2's database user
ORDER BY table_name;

-- Expected: SELECT on daily_patterns (read-only)
-- Should NOT have: INSERT, UPDATE, DELETE on daily_patterns
```

**Fix**: Remove the write query and use Redis pub-sub to receive data from TickStockPL instead.

---

### 6.4 SQLAlchemy 2.x Parameter Binding

**Symptom**: `TypeError: 'list' object is not a mapping` when using positional parameters.

**Problem**: SQLAlchemy 2.x requires named parameters (dict), not positional (%s).

```python
# ❌ OLD (SQLAlchemy 1.x style, doesn't work in 2.x)
params = ['AAPL', 7]
result = conn.execute(
    text("SELECT * FROM symbols WHERE symbol = %s AND active = %s"),
    params  # List of positional parameters
)

# ✅ NEW (SQLAlchemy 2.x style)
result = conn.execute(
    text("SELECT * FROM symbols WHERE symbol = :symbol AND active = :active"),
    {'symbol': 'AAPL', 'active': True}  # Dict of named parameters
)
```

**Reference**: `src/infrastructure/database/tickstock_db.py:122-146`

---

## 7. Quick Reference

### 7.1 Connection Pattern Cheat Sheet

```python
# ✅ CORRECT: Context manager
with db.get_connection() as conn:
    result = conn.execute(text("SELECT * FROM symbols"))
    data = result.fetchall()

# ✅ CORRECT: Parameterized query
with db.get_connection() as conn:
    result = conn.execute(
        text("SELECT * FROM symbols WHERE symbol = :symbol"),
        {'symbol': 'AAPL'}
    )

# ✅ CORRECT: Transaction rollback
with db.get_connection() as conn:
    try:
        conn.execute(text("INSERT INTO user_sessions ..."))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise

# ❌ WRONG: Connection leak
conn = db.engine.connect()
result = conn.execute(text("SELECT * FROM symbols"))
# Exception here → connection never closed!

# ❌ WRONG: SQL injection
query = f"SELECT * FROM symbols WHERE symbol = '{user_input}'"
```

---

### 7.2 Performance Optimization Checklist

Before deploying a database query:

- [ ] Query returns results in <50ms (run `EXPLAIN ANALYZE`)
- [ ] Uses explicit column list (no `SELECT *`)
- [ ] Uses parameterized queries (no string interpolation)
- [ ] Includes time-based filter for hypertables
- [ ] Uses context manager for connection cleanup
- [ ] Uses `RealDictCursor` for dict-based results (if applicable)
- [ ] Respects read-only boundaries (no writes to forbidden tables)

---

### 7.3 Common SQL Queries (TickStockAppV2)

**Get Active Symbols**:
```python
with db.get_connection() as conn:
    result = conn.execute(text("""
        SELECT symbol, name, exchange
        FROM symbols
        WHERE active = true
        ORDER BY symbol ASC
    """))
```

**Get Recent Patterns** (from TickStockPL):
```python
# Note: TickStockAppV2 should use Redis pub-sub, not direct queries
# This is read-only fallback for UI display
with db.get_connection() as conn:
    result = conn.execute(text("""
        SELECT symbol, pattern_name, confidence, detected_at
        FROM daily_patterns
        WHERE detected_at >= NOW() - INTERVAL '7 days'
        ORDER BY detected_at DESC
        LIMIT 100
    """))
```

**Get User Session**:
```python
with db.get_connection() as conn:
    result = conn.execute(text("""
        SELECT session_id, user_id, last_activity
        FROM user_sessions
        WHERE session_id = :session_id
    """), {'session_id': session_id})
```

---

### 7.4 Health Check Query

```python
def database_health_check():
    """Quick database health check"""
    try:
        start = time.time()
        with db.get_connection() as conn:
            # Test basic connectivity
            conn.execute(text("SELECT 1"))

            # Test TimescaleDB extension
            result = conn.execute(text("""
                SELECT extname
                FROM pg_extension
                WHERE extname = 'timescaledb'
            """))
            timescale_enabled = result.scalar() is not None

        query_time_ms = (time.time() - start) * 1000

        return {
            'status': 'healthy' if query_time_ms < 100 else 'degraded',
            'query_time_ms': round(query_time_ms, 2),
            'timescale_enabled': timescale_enabled
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
```

---

### 7.5 References

**Primary Files**:
- `src/infrastructure/database/tickstock_db.py` - Main database connection class
- `src/infrastructure/database/connection_pool.py` - Async connection pool
- `src/config/database_config.py` - Database configuration
- `migrations/versions/` - Alembic migration files

**Documentation**:
- `CLAUDE.md:199-226` - Database access patterns and essential queries
- `docs/planning/sprints/sprint42/SPRINT42_COMPLETE.md` - Read-only enforcement lesson
- `docs/PRPs/templates/prp-new.md:419-481` - Database pattern examples

**External Resources**:
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [TimescaleDB Docs](https://docs.timescale.com/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---

## Summary

**Key Takeaways**:

1. **ALWAYS use context managers** (`with db.get_connection()`) - Connection leaks cause production outages
2. **Respect read-only boundaries** - TickStockAppV2 cannot write to pattern/indicator/OHLCV tables
3. **Include time filters on hypertables** - Leverages TimescaleDB partitioning for 100x speed improvements
4. **Use parameterized queries** - Prevents SQL injection vulnerabilities
5. **Run EXPLAIN ANALYZE** - Verify query performance <50ms before deployment
6. **Use RealDictCursor** - Dict-based results improve code readability and maintainability
7. **Test migrations on production copy** - Schema changes are high-risk operations

**Sprint Lessons Captured**:
- Sprint 42: OHLCV aggregation removed from AppV2 due to role violation
- Connection pool exhaustion debugging patterns
- TimescaleDB-specific optimizations

**Next Steps**:
- Review your code for connection leak anti-patterns (Section 1.2)
- Verify read-only compliance with allowed/forbidden table lists (Section 2.1)
- Add `EXPLAIN ANALYZE` checks to CI/CD pipeline for critical queries

---

**Version**: 1.0
**Last Updated**: 2025-10-19
**Maintainer**: TickStock Development Team
**Related Pattern Libraries**: `pytest_patterns.md`, `error_handling_patterns.md`, `configuration_patterns.md`
