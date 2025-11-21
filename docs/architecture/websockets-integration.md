# WebSockets Integration for TickStock.ai

## Overview
TickStockApp handles real-time data ingestion via WebSockets (e.g., Massive.com's wss://socket.massive.com/stocks), providing per-minute OHLCV updates for symbols. This data is forwarded to TickStockPL's `DataBlender` for blending with historical data, enabling pattern scanning (batch and real-time) and event publishing to TickStockApp. The pipeline supports high-frequency patterns (e.g., Day1Breakout) and daily aggregations, storing live data in the database for persistence.

## WebSocket Client Architecture

TickStockAppV2 provides flexible WebSocket client architecture with two operational modes to accommodate different throughput requirements and failure tolerance needs.

### Single-Connection Mode (Default)

**Configuration**:
```bash
USE_MASSIVE_API=true
MASSIVE_API_KEY=your_api_key
USE_MULTI_CONNECTION=false  # or omit (defaults to false)
```

**Characteristics**:
- Single `MassiveWebSocketClient` instance handles all ticker subscriptions
- Backward compatible with all existing configurations
- Suitable for monitoring up to ~100 tickers
- Simple configuration and management
- Single point of failure (connection loss impacts all tickers)

**Use Cases**:
- Development and testing environments
- Small to medium ticker universes (<100 symbols)
- Simple monitoring scenarios
- Deployments where high availability is not critical

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

### Technical Implementation

Both modes utilize the same underlying `MassiveWebSocketClient` for Massive API communication. The `RealTimeDataAdapter` (`src/infrastructure/data_sources/adapters/realtime_adapter.py`) conditionally creates either:
- A single `MassiveWebSocketClient` instance (single-connection mode)
- A `MultiConnectionManager` instance wrapping multiple clients (multi-connection mode)

The `MultiConnectionManager` implements the same interface as `MassiveWebSocketClient` (`.connect()`, `.disconnect()`, `.subscribe()`), making it a true drop-in replacement with zero changes required to calling code.

## Location
- **WebSockets Handler**: In TickStockApp, likely in `src/data/websockets_handler.py` or similar module.
- **Functionality**: Connects to Massive WebSockets, subscribes to symbols (e.g., AAPL, TSLA), processes per-minute bars, and forwards to TickStockPL.

## Data Flow
1. **Ingestion (TickStockApp)**:
   - Connects to Massive WebSockets using `websocket-client` or Massive's Python client.
   - Receives OHLCV messages (e.g., {'symbol': 'AAPL', 'timestamp': '2025-08-23T07:10:00Z', 'open': 150.0, 'high': 151.2, 'low': 149.8, 'close': 150.5, 'volume': 10000}).
   - Optionally aggregates ticks to 1min bars in-memory (pandas).
   - Sends to TickStockPL via Redis (channel: "tickstock_data") or direct call for dev.
   - Inserts to DB (`ticks` or `ohlcv_1min`) for persistence (database_architecture.md).

2. **Blending (TickStockPL)**:
   - `DataBlender` (src/data/preprocessor.py) receives live data.
   - Appends to historical DataFrame (loaded from DB, e.g., `ohlcv_daily` or `ohlcv_1min`).
   - Resamples if needed (e.g., align to 1min for intraday patterns).
   - Feeds to `RealTimeScanner` for incremental pattern detection (pattern_library_architecture.md).

3. **Scanning and Events (TickStockPL)**:
   - `RealTimeScanner` scans blended data for patterns (e.g., Doji, Day1Breakout).
   - Publishes events to Redis (channel: "tickstock_patterns") via `EventPublisher` (e.g., {"pattern": "Day1Breakout", "symbol": "AAPL", "timestamp": "...", "direction": "long", "timeframe": "1min"}).

4. **Consumption (TickStockApp)**:
   - Subscribes to "tickstock_patterns" channel.
   - Processes events: Logs to DB (`events` table), updates UI, or triggers trades.

## Nightly Aggregations
- Live data stored in `ticks` or `ohlcv_1min` defines "the day" (market open to close).
- Nightly job (src/data/aggregator.py) rolls up to `ohlcv_daily` using SQL/Python (e.g., FIRST open, MAX high, LAST close, SUM volume).
- Ensures historical consistency for long-term patterns (e.g., HeadAndShoulders).

## Sample WebSockets Handler (TickStockApp)
```python
# In TickStockApp/src/data/websockets_handler.py
import websocket
import json
import redis
from datetime import datetime

redis_client = redis.Redis.from_url('redis://localhost:6379')
DATA_CHANNEL = 'tickstock_data'

def on_message(ws, message):
    data = json.loads(message)  # Massive WebSocket format
    tick = {
        'symbol': data['sym'],
        'timestamp': pd.to_datetime(data['t'], unit='ms'),
        'open': data['o'],
        'high': data['h'],
        'low': data['l'],
        'close': data['c'],
        'volume': data['v']
    }
    # Forward to TickStockPL
    redis_client.publish(DATA_CHANNEL, json.dumps(tick))
    # Insert to DB (e.g., ohlcv_1min)
    # ... SQLAlchemy upsert ...

def start_websockets(symbols):
    ws = websocket.WebSocketApp(
        'wss://socket.massive.com/stocks',
        on_message=on_message,
        header={'Authorization': f'Bearer {config.get('MASSIVE_API_KEY')}'}
    )
    ws.send(json.dumps({'action': 'subscribe', 'params': f'A.{",".join(symbols)}'}))  # Aggregate bars
    ws.run_forever()

# Run: start_websockets(['AAPL', 'TSLA'])
```

## Integration with TickStockPL
- **DataBlender Update**:
  ```python
  # In src/data/preprocessor.py (TickStockPL)
  class DataBlender:
      def __init__(self, historical_data: pd.DataFrame, redis_url: str = None):
          self.data = historical_data.set_index('timestamp')
          self.redis = redis.Redis.from_url(redis_url) if redis_url else None
          if self.redis:
              self.pubsub = self.redis.pubsub()
              self.pubsub.subscribe('tickstock_data')

      def listen_and_append(self):
          for message in self.pubsub.listen():
              if message['type'] == 'message':
                  tick = json.loads(message['data'])
                  new_df = pd.DataFrame([tick]).set_index('timestamp')
                  self.data = pd.concat([self.data, new_df]).sort_index()
                  return self.resample(self.data, '1min')  # Feed to scanner
  ```
- Scanner consumes blended data, raises events (pattern_library_architecture.md).

## Notes
- **Frequency**: Per-minute WebSockets align with `ohlcv_1min` for intraday patterns (e.g., Day1Breakout). Resample for higher timeframes in `DataBlender`.
- **Fallback**: If WebSockets fail, TickStockApp can pull recent data via Massive's REST (get_historical_data.md).
- **Scale**: Redis ensures low-latency data transfer; in dev, use in-memory queue (pubsub.py) to save costs.

This pipeline is implemented in Sprint 10 (sprint_plan.md).

## Related Documentation

- **[`system-architecture.md`](system-architecture.md)** - Complete system architecture overview
- **[`database-architecture.md`](database-architecture.md)** - Database schema for data storage
- **[`pattern-library-architecture.md`](pattern-library-architecture.md)** - Pattern scanning architecture
- **[`../guides/historical-data-loading.md`](../guides/historical-data-loading.md)** - Historical data loading procedures