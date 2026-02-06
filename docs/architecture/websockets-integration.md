# WebSockets Integration for TickStock.ai

## Overview
TickStockApp handles real-time data ingestion via WebSockets (e.g., Massive.com's wss://socket.massive.com/stocks), providing per-minute OHLCV updates for symbols. This data is persisted directly to TimescaleDB and used for real-time market state analysis, including rankings, sector rotation, stage classification, and breadth metrics. The pipeline delivers sub-second dashboard updates for actionable trading insights.

## WebSocket Client Architecture

TickStockAppV2 provides flexible WebSocket client architecture with two operational modes to accommodate different throughput requirements and failure tolerance needs.

### Single-Connection Mode (Default)

**Configuration**:
```bash
USE_MASSIVE_API=true
MASSIVE_API_KEY=your_api_key
USE_MULTI_CONNECTION=false  # or omit (defaults to false)

# Symbol source for single-connection mode
SYMBOL_UNIVERSE_KEY=market_leaders:top_100  # Loads from cache_entries table
# Or use default fallback: ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX', 'META', 'NVDA']
```

**Characteristics**:
- Single `MassiveWebSocketClient` instance handles all ticker subscriptions
- Backward compatible with all existing configurations
- Suitable for monitoring up to ~100 tickers
- Simple configuration and management
- Single point of failure (connection loss impacts all tickers)
- **License Requirement**: Free/Starter Massive API licenses support 1 connection

**Use Cases**:
- Development and testing environments
- Small to medium ticker universes (<100 symbols)
- Simple monitoring scenarios
- Deployments where high availability is not critical
- **Required for Free/Starter Massive API licenses** (multi-connection requires Business tier)

### Multi-Connection Mode (Optional)

**Configuration**:
```bash
USE_MASSIVE_API=true
MASSIVE_API_KEY=your_api_key
USE_MULTI_CONNECTION=true
WEBSOCKET_CONNECTIONS_MAX=3

# Connection 1: Primary - High Priority Tickers
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_NAME=primary_watchlist
WEBSOCKET_CONNECTION_1_UNIVERSE_KEY=tech_leaders:top_100
# Or use direct symbols:
# WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,MSFT

# Connection 2: Secondary - Sector Watch
WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_2_NAME=sector_finance
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=finance:major_banks

# Connection 3: Tertiary - Emerging Opportunities
WEBSOCKET_CONNECTION_3_ENABLED=true
WEBSOCKET_CONNECTION_3_NAME=emerging_tech
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=emerging:high_growth
```

**Characteristics**:
- Up to 3 concurrent `MassiveWebSocketClient` instances (Massive API account limit)
- Independent ticker subscriptions per connection
- **3x Throughput Capacity**: Monitor 300+ tickers vs 100 on single connection
- **Priority Routing**: Isolate critical tickers on dedicated connections
- **Partial Failover**: System remains operational with 2/3 connections if one fails
- **Thread-Safe Aggregation**: Unified callback flow maintains data consistency
- Managed by `MultiConnectionManager` (drop-in replacement for `MassiveWebSocketClient`)
- **License Requirement**: Requires Massive API Business tier license (Free/Starter limited to 1 connection)

**Implementation Details**:
- **Ticker Assignment**:
  - **Preferred**: Universe keys via `CacheControl.get_universe_tickers()` for dynamic management
  - **Fallback**: Direct comma-separated symbol lists for static configurations
- **Connection Manager**: `src/infrastructure/websocket/multi_connection_manager.py`
- **Callback Aggregation**: All connections route through unified callbacks with connection ID tracking
- **Health Monitoring**: Per-connection statistics (message counts, error rates, last message time)
- **Subscription Routing**: Dynamic ticker assignment with load balancing capability

**Use Cases**:
- Production environments requiring high availability
- Large ticker universes (200-500+ symbols)
- Priority segmentation (isolate high-value tickers for guaranteed delivery)
- Scenarios requiring partial failover (maintain 66% capacity if one connection fails)
- Maximum throughput utilization of Massive API account limits

**Architecture Comparison**:

| Aspect | Single-Connection | Multi-Connection |
|--------|------------------|------------------|
| Max Tickers | ~100 | 300+ (100 per connection) |
| Throughput | Standard | 3x capacity |
| Failover | None (single point of failure) | 2/3 capacity maintained |
| Configuration | Simple (2 keys) | Detailed (18+ keys) |
| Use Case | Dev/Test, Small Universe | Production, Large Universe |
| Backward Compatible | N/A | Yes (default: disabled) |

## Configuration Details and Symbol Loading

### Single-Connection Mode Symbol Source

In single-connection mode (`USE_MULTI_CONNECTION=false`), symbols are loaded via the `MarketDataService._get_universe()` method:

**Symbol Loading Flow** (Sprint 61: Updated to use RelationshipCache):
1. `MarketDataService` reads `SYMBOL_UNIVERSE_KEY` from configuration
2. Calls `RelationshipCache.get_universe_symbols(universe_key)` to load symbols from `definition_groups`/`group_memberships` tables
3. Supports multi-universe join (e.g., `SPY:nasdaq100` loads distinct union of both)
4. Passes ticker list to `RealTimeDataAdapter.connect(universe)`
5. `RealTimeDataAdapter` creates single `MassiveWebSocketClient` and subscribes all tickers

**Configuration Settings Used**:
- ✅ `SYMBOL_UNIVERSE_KEY` - **Primary symbol source** (e.g., `market_leaders:top_100`)
- ❌ `WEBSOCKET_CONNECTION_X_SYMBOLS` - **Ignored** (only used in multi-connection mode)
- ❌ `WEBSOCKET_CONNECTION_X_UNIVERSE_KEY` - **Ignored** (only used in multi-connection mode)

**Example Configuration** (Sprint 61: Updated universe keys):
```bash
# .env for single-connection mode
USE_MULTI_CONNECTION=false

# Single universe (UNIVERSE type):
SYMBOL_UNIVERSE_KEY=nasdaq100          # 102 NASDAQ-100 stocks
# SYMBOL_UNIVERSE_KEY=dow30            # 30 Dow Jones stocks

# Single ETF holdings:
# SYMBOL_UNIVERSE_KEY=SPY              # 504 S&P 500 stocks (via SPY ETF)
# SYMBOL_UNIVERSE_KEY=QQQ              # 102 NASDAQ-100 stocks (via QQQ ETF)

# Multi-universe join (distinct union):
# SYMBOL_UNIVERSE_KEY=SPY:nasdaq100    # ~518 distinct stocks (SPY + NASDAQ-100)
# SYMBOL_UNIVERSE_KEY=SPY:QQQ:dow30    # ~522 distinct stocks (union of all 3)
```

**Fallback Behavior**:
- If `SYMBOL_UNIVERSE_KEY` universe not found in cache, uses hardcoded default:
  ```python
  ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX', 'META', 'NVDA']
  ```

### Multi-Connection Mode Symbol Source

In multi-connection mode (`USE_MULTI_CONNECTION=true`), symbols are loaded per-connection via `MultiConnectionManager._load_connection_config()`:

**Symbol Loading Flow** (Sprint 61: Updated to use RelationshipCache):
1. `MultiConnectionManager` reads `WEBSOCKET_CONNECTION_X_ENABLED` for each connection (X = 1, 2, 3)
2. For each enabled connection:
   - **Option A**: If `WEBSOCKET_CONNECTION_X_UNIVERSE_KEY` set, loads from `RelationshipCache.get_universe_symbols()`
     - Supports multi-universe join (e.g., `SPY:nasdaq100` loads distinct union)
   - **Option B**: If `WEBSOCKET_CONNECTION_X_SYMBOLS` set, parses comma-separated list
3. Creates separate `MassiveWebSocketClient` for each connection with its ticker list
4. Subscribes each connection independently

**Configuration Settings Used**:
- ✅ `WEBSOCKET_CONNECTION_X_UNIVERSE_KEY` - Preferred (e.g., `market_leaders:top_50`)
- ✅ `WEBSOCKET_CONNECTION_X_SYMBOLS` - Alternative for static lists (e.g., `AAPL,NVDA,TSLA`)
- ❌ `SYMBOL_UNIVERSE_KEY` - **Ignored** (only used in single-connection mode)

**Example Configuration** (Sprint 61: Updated universe keys):
```bash
# .env for multi-connection mode
USE_MULTI_CONNECTION=true

# Connection 1: Direct symbols (7 tickers)
WEBSOCKET_CONNECTION_1_ENABLED=true
WEBSOCKET_CONNECTION_1_SYMBOLS=AAPL,NVDA,TSLA,MSFT,GOOGL,META,AMZN

# Connection 2: Single universe (102 tickers)
WEBSOCKET_CONNECTION_2_ENABLED=true
WEBSOCKET_CONNECTION_2_UNIVERSE_KEY=nasdaq100

# Connection 3: Multi-universe join (518 distinct tickers)
WEBSOCKET_CONNECTION_3_ENABLED=true
WEBSOCKET_CONNECTION_3_UNIVERSE_KEY=SPY:nasdaq100
```

### Code Path Initialization

The `RealTimeDataAdapter` (`src/infrastructure/data_sources/adapters/realtime_adapter.py`) conditionally initializes based on `USE_MULTI_CONNECTION`:

```python
# realtime_adapter.py __init__ method
if config.get("USE_MASSIVE_API") and config.get("MASSIVE_API_KEY"):
    use_multi_connection = config.get("USE_MULTI_CONNECTION", False)

    if use_multi_connection:
        # MULTI-CONNECTION MODE
        from src.infrastructure.websocket.multi_connection_manager import MultiConnectionManager

        self.client = MultiConnectionManager(
            config=config,
            on_tick_callback=self.tick_callback,
            on_status_callback=self.status_callback,
            max_connections=config.get("WEBSOCKET_CONNECTIONS_MAX", 3),
        )
        logger.info("REAL-TIME-ADAPTER: Initialized with Multi-Connection Manager")
    else:
        # SINGLE CONNECTION MODE (backward compatible)
        self.client = MassiveWebSocketClient(
            api_key=config["MASSIVE_API_KEY"],
            on_tick_callback=self.tick_callback,
            on_status_callback=self.status_callback,
            config=config,
        )
        logger.info("REAL-TIME-ADAPTER: Initialized with single Massive WebSocket client")
```

**Key Files**:
- `src/core/services/market_data_service.py` - Service that manages universe loading
  - Method: `_get_universe()` - Loads symbols from `SYMBOL_UNIVERSE_KEY` (single-connection only)
  - Method: `_service_loop()` - Calls `adapter.connect(universe)` with loaded symbols
- `src/infrastructure/data_sources/adapters/realtime_adapter.py` - Adapter initialization
  - Conditionally creates `MassiveWebSocketClient` OR `MultiConnectionManager`
- `src/infrastructure/websocket/multi_connection_manager.py` - Multi-connection coordinator
  - Method: `_load_connection_config()` - Loads per-connection universe keys or symbol lists
- `src/presentation/websocket/massive_client.py` - Single WebSocket client
  - Handles authentication, subscription, and message callbacks

### Technical Implementation

Both modes utilize the same underlying `MassiveWebSocketClient` for Massive API communication. The `RealTimeDataAdapter` (`src/infrastructure/data_sources/adapters/realtime_adapter.py`) conditionally creates either:
- A single `MassiveWebSocketClient` instance (single-connection mode)
- A `MultiConnectionManager` instance wrapping multiple clients (multi-connection mode)

The `MultiConnectionManager` implements the same interface as `MassiveWebSocketClient` (`.connect()`, `.disconnect()`, `.subscribe()`), making it a true drop-in replacement with zero changes required to calling code.

## Current Architecture (Sprint 54+)

TickStockAppV2 operates as a standalone market state analysis platform. WebSocket data from Massive API is:
1. Received by `MarketDataService` via `MassiveWebSocketClient`
2. Persisted directly to TimescaleDB (`ohlcv_1min` table)
3. Used for market state analysis (rankings, sector rotation, stage classification)
4. Accessible via REST API (`GET /api/ticks/recent`)

**Key Points:**
- **No Redis forwarding**: Tick data persists directly to database
- **No TickStockPL integration**: Components operate independently
- **Database-first**: TimescaleDB is the single source of truth
- **Market state focus**: Rankings, breadth metrics, sentiment visualization

See [Redis Integration](./redis-integration.md) for details on the standalone architecture.

## Related Documentation

- **[`diagrams/websocket-single-connection-flow.md`](diagrams/websocket-single-connection-flow.md)** - Complete flow diagram for single-connection mode
- **[`system-architecture.md`](system-architecture.md)** - Complete system architecture overview
- **[`database-architecture.md`](database-architecture.md)** - Database schema for data storage
- **[`pattern-library-architecture.md`](pattern-library-architecture.md)** - Pattern scanning architecture
- **[`../guides/historical-data-loading.md`](../guides/historical-data-loading.md)** - Historical data loading procedures