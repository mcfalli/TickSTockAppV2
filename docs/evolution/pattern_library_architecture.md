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