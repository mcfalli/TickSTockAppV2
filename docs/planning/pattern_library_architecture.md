# Pattern Library Architecture

## Folder Structure
```
tickstock-patterns/
├── src/
│   ├── patterns/ (base.py, candlestick.py, chart.py, trend.py, breakout.py)
│   ├── analysis/ (scanner.py, backtester.py)
│   ├── data/ (loader.py, preprocessor.py)
│   └── utils/ (visuals.py, metrics.py)
├── docs/ (this file, patterns.md, etc.)
├── tests/
└── examples/
```

## Key Classes
- **BasePattern**: Abstract; detect() returns boolean Series.
- **ReversalPattern**: Subclass for reversals (e.g., direction param).
- **PatternScanner**: Batch scanning, add_pattern(), scan() with event publish.
- **RealTimeScanner**: Incremental updates for live data.
- **EventPublisher**: Pub-sub (Redis) for signals to TickStockApp.

## Process
- Batch: Load DataFrame, add patterns, scan() → events.
- Real-Time: Update with ticks, scan window → events.
- Blending: DataBlender resamples/append for mixed frequencies.

Optimizations: Vectorized ops; window-based for efficiency.

## Pseudocode Snippets
### DataBlender (src/data/preprocessor.py)
```python
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

### EventPublisher (src/analysis/scanner.py)
```python
class EventPublisher:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.Redis.from_url(redis_url) if redis_url else None
        self.channel = "tickstock_patterns"

    def publish(self, event: dict):
        if self.redis:
            self.redis.publish(self.channel, json.dumps(event))
        else:
            print(f"Publishing event: {event}")  # Fallback for testing
```