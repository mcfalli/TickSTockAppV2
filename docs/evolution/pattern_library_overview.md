# Pattern Library Overview

## Goals
Build a modular Python library for detecting stock patterns in OHLCV data. Start with basics (candlesticks, charts, trends, breakouts), extend to reversals/multi-timeframe. Integrate with scanner for batch/real-time analysis; publish events for signals.

## Categories
- Candlestick: Single-bar (Doji, Hammer).
- Chart/Reversals: Multi-bar (HeadAndShoulders, DoubleBottom).
- Trend: Indicator-based (MACrossover).
- Breakout: Intraday (Day1Breakout).

## Integration
- Scanner orchestrates detections, publishes events to TickStockApp.
- Data: From DB/feeds, resampled for timeframes.
- Extensibility: Subclass BasePattern; add to scanner.

See patterns.md for detailed specs.