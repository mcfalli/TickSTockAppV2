# WebSockets Integration for TickStock.ai

## Overview
TickStockApp handles real-time data ingestion via WebSockets (e.g., Polygon.io's wss://socket.polygon.io/stocks), providing per-minute OHLCV updates for symbols. This data is forwarded to TickStockPL's `DataBlender` for blending with historical data, enabling pattern scanning (batch and real-time) and event publishing to TickStockApp. The pipeline supports high-frequency patterns (e.g., Day1Breakout) and daily aggregations, storing live data in the database for persistence.

## Location
- **WebSockets Handler**: In TickStockApp, likely in `src/data/websockets_handler.py` or similar module.
- **Functionality**: Connects to Polygon WebSockets, subscribes to symbols (e.g., AAPL, TSLA), processes per-minute bars, and forwards to TickStockPL.

## Data Flow
1. **Ingestion (TickStockApp)**:
   - Connects to Polygon WebSockets using `websocket-client` or Polygon's Python client.
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
    data = json.loads(message)  # Polygon WebSocket format
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
        'wss://socket.polygon.io/stocks',
        on_message=on_message,
        header={'Authorization': f'Bearer {config.get('POLYGON_API_KEY')}'}
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
- **Fallback**: If WebSockets fail, TickStockApp can pull recent data via Polygon's REST (get_historical_data.md).
- **Scale**: Redis ensures low-latency data transfer; in dev, use in-memory queue (pubsub.py) to save costs.

This pipeline is implemented in Sprint 10 (sprint_plan.md).

## Related Documentation

- **[`system-architecture.md`](system-architecture.md)** - Complete system architecture overview
- **[`database-architecture.md`](database-architecture.md)** - Database schema for data storage
- **[`pattern-library-architecture.md`](pattern-library-architecture.md)** - Pattern scanning architecture
- **[`../guides/historical-data-loading.md`](../guides/historical-data-loading.md)** - Historical data loading procedures