# TickStock.ai Pattern Library Specification

This document outlines the core patterns for the TickStock.ai pattern detection library. Each pattern is designed to detect specific price movements in OHLCV (Open, High, Low, Close, Volume) data, supporting multiple timeframes (e.g., 1min, daily) and integrating with the `PatternScanner` to publish events to TickStockApp. Patterns inherit from a `BasePattern` class, returning a boolean pandas Series for detections.

## Overview

Patterns are categorized into:
- **Candlestick Patterns**: Single-bar formations indicating immediate sentiment (e.g., reversals).
- **Chart Patterns**: Multi-bar formations signaling trend changes (e.g., reversals or continuations).
- **Trend Patterns**: Indicator-based signals for momentum or trend shifts.
- **Breakout Patterns**: Intraday setups capturing high-momentum moves, especially early in the trading session.
- **Intra-day Trend Patterns**: Session-specific trends for real-time monitoring (e.g., intra-day highs/lows and momentum).

All patterns are timeframe-agnostic, adapting via resampling (e.g., in `DataBlender`) and configurable parameters (e.g., window sizes, tolerances). Ties to User Story 8 for multi-timeframe support.

## Candlestick Patterns

### Doji
- **Description**: A neutral pattern where open and close prices are very close, signaling indecision. Often a reversal precursor. (Ties to User Story 1: Real-time detection for alerts.)
- **Timeframes**: Any (e.g., 1min for intraday, daily for swing; adapts param via 'timeframe').
- **Parameters**:
  - `tolerance` (float, default: 0.01): Max body size as % of candle range (high-low).
  - `timeframe` (str, default: 'daily'): For event metadata and param scaling (e.g., tighter tolerance on 1min).
- **Detection Logic** (Pseudocode):
  ```python
  body = abs(data['close'] - data['open'])
  candle_range = data['high'] - data['low']
  detected = body <= tolerance * candle_range
  return detected  # Boolean Series
  ```
- **Edge Cases**: Zero candle_range (no trades: return False); low volume (< avg: optional filter via composite in User Story 9); partial bars in real-time (blend via DataBlender).
- **Event Output**: `{"pattern": "Doji", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min"}`

### Hammer
- **Description**: Bullish reversal pattern with a small body at the top and a long lower shadow, indicating rejection of lower prices. (Ties to User Story 1: For bullish reversal alerts in downtrends.)
- **Timeframes**: Any; scale shadow_ratio for shorter frames.
- **Parameters**:
  - `shadow_ratio` (float, default: 2.0): Min ratio of lower shadow to body.
  - `timeframe` (str, default: 'daily').
- **Detection Logic** (Pseudocode):
  ```python
  body = abs(data['close'] - data['open'])
  lower_shadow = min(data['open'], data['close']) - data['low']
  upper_shadow = data['high'] - max(data['open'], data['close'])
  detected = (lower_shadow > shadow_ratio * body) & (upper_shadow < body)
  return detected
  ```
- **Edge Cases**: Inverted hammer variant (optional subclass); zero body (treat as Doji overlap via composite); high volatility days (adjust ratio dynamically per User Story 5).
- **Event Output**: `{"pattern": "Hammer", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "daily", "direction": "bullish"}`

### Closed in Top 10% of Range
- **Description**: Intra-day bullish signal where the close is in the upper 10% of the bar's range, indicating strong buying pressure toward session end. (Ties to User Story 1: Real-time intra-day alerts.)
- **Timeframes**: Intra-day (e.g., 1min, 5min); warn/disable on daily via timeframe param.
- **Parameters**:
  - `percent_threshold` (float, default: 0.10): Top percentage of range for close.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  range_val = data['high'] - data['low']
  upper_threshold = data['high'] - (percent_threshold * range_val)
  detected = data['close'] >= upper_threshold
  return detected
  ```
- **Edge Cases**: Flat range (zero: False); end-of-day only (mask via session times); combine with volume filter (e.g., AND RelativeVolume >=1.5 per User Story 9).
- **Event Output**: `{"pattern": "ClosedInTop10Percent", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min", "direction": "bullish"}`

### Closed in Bottom 10% of Range
- **Description**: Intra-day bearish signal where the close is in the lower 10% of the bar's range, indicating strong selling pressure toward session end. (Ties to User Story 1: Real-time intra-day alerts.)
- **Timeframes**: Intra-day (e.g., 1min, 5min); warn/disable on daily via timeframe param.
- **Parameters**:
  - `percent_threshold` (float, default: 0.10): Bottom percentage of range for close.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  range_val = data['high'] - data['low']
  lower_threshold = data['low'] + (percent_threshold * range_val)
  detected = data['close'] <= lower_threshold
  return detected
  ```
- **Edge Cases**: Flat range (zero: False); end-of-day only (mask via session times); combine with volume filter (e.g., AND RelativeVolume >=1.5 per User Story 9).
- **Event Output**: `{"pattern": "ClosedInBottom10Percent", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min", "direction": "bearish"}`

## Chart Patterns (Reversals)

### HeadAndShoulders
- **Description**: Bearish reversal pattern with a left shoulder, higher head, right shoulder, and a neckline break, signaling trend exhaustion. (Ties to User Story 3: For multi-bar reversals on blended data.)
- **Timeframes**: Daily, hourly (longer-term for reliability).
- **Parameters**:
  - `window` (int, default: 50): Bars to analyze (scaled to timeframe, e.g., 50 1min bars ~1hr).
  - `direction` (str, default: 'bearish'): 'bearish' for top, 'bullish' for inverse.
  - `tolerance` (float, default: 0.02): % for peak/neckline similarity.
  - `timeframe` (str, default: 'daily').
- **Detection Logic** (Pseudocode):
  ```python
  from scipy.signal import find_peaks
  highs = find_peaks(data['high'], distance=window//3)[0]  # Find shoulders/head
  lows = find_peaks(-data['low'], distance=window//3)[0]  # Neckline points
  # Assume recent 3 highs: left_shoulder, head, right_shoulder
  if len(highs) >= 3 and abs(data['high'][highs[-3]] - data['high'][highs[-1]]) < tolerance * data['high'][highs[-2]] and data['high'][highs[-2]] > max(data['high'][highs[-3]], data['high'][highs[-1]]):
      neckline = (data['low'][lows[-2]] + data['low'][lows[-1]]) / 2  # Avg recent lows
      detected = data['close'] < neckline  # Break below
  else:
      detected = pd.Series(False, index=data.index)
  return detected
  ```
- **Edge Cases**: Insufficient peaks (return False); noisy data (increase distance param); inverse via direction flip (handle as subclass).
- **Event Output**: `{"pattern": "HeadAndShoulders", "symbol": "AAPL", "timestamp": "...", "price": close, "direction": "bearish", "timeframe": "daily"}`

### InverseHeadAndShoulders
- **Description**: Bullish reversal with lower head between two higher troughs, breaking above neckline. (Ties to User Story 3: For multi-bar reversals on blended data.)
- **Timeframes**: Daily, hourly.
- **Parameters**: Same as HeadAndShoulders (`window`, `direction='bullish'`, `tolerance`, `timeframe`).
- **Detection Logic** (Pseudocode):
  ```python
  from scipy.signal import find_peaks
  lows = find_peaks(-data['low'], distance=window//3)[0]  # Find troughs
  highs = find_peaks(data['high'], distance=window//3)[0]  # Neckline points
  # Assume recent 3 lows: left_trough, head, right_trough
  if len(lows) >= 3 and abs(data['low'][lows[-3]] - data['low'][lows[-1]]) < tolerance * data['low'][lows[-2]] and data['low'][lows[-2]] < min(data['low'][lows[-3]], data['low'][lows[-1]]):
      neckline = (data['high'][highs[-2]] + data['high'][highs[-1]]) / 2  # Avg recent highs
      detected = data['close'] > neckline  # Break above
  else:
      detected = pd.Series(False, index=data.index)
  return detected
  ```
- **Edge Cases**: Insufficient troughs (return False); noisy data (increase distance); bearish variant via direction.
- **Event Output**: `{"pattern": "InverseHeadAndShoulders", "symbol": "AAPL", "timestamp": "...", "price": close, "direction": "bullish", "timeframe": "daily"}`

### DoubleBottom
- **Description**: Bullish reversal with two similar lows, breaking above the intervening high. (Ties to User Story 3: For multi-bar reversals on blended data.)
- **Timeframes**: Any (intraday to weekly).
- **Parameters**:
  - `window` (int, default: 30): Bars to search for bottoms.
  - `tolerance` (float, default: 0.02): % similarity for lows.
  - `timeframe` (str, default: 'daily').
- **Detection Logic** (Pseudocode):
  ```python
  from scipy.signal import find_peaks
  lows = find_peaks(-data['low'], distance=window//2)[0]  # Find two bottoms
  if len(lows) >= 2 and abs(data['low'][lows[-2]] - data['low'][lows[-1]]) < tolerance * data['low'][lows[-1]]:
      intervening_high = data['high'].iloc[lows[-2]:lows[-1]].max()
      detected = data['close'] > intervening_high
  else:
      detected = pd.Series(False, index=data.index)
  return detected
  ```
- **Edge Cases**: Uneven lows (exceed tolerance: False); no break (detect only on confirmation); double top variant (subclass with direction='bearish').
- **Event Output**: `{"pattern": "DoubleBottom", "symbol": "AAPL", "timestamp": "...", "price": close, "direction": "bullish", "timeframe": "1H"}`

## Trend Patterns

### MACrossover
- **Description**: Trend signal when a fast moving average crosses a slow one (bullish: fast > slow, bearish: fast < slow). (Ties to User Story 9: Composable with conditions like EMA.)
- **Timeframes**: Any (e.g., 1min for scalping, daily for trends).
- **Parameters**:
  - `fast` (int, default: 12): Fast EMA period.
  - `slow` (int, default: 26): Slow EMA period.
  - `timeframe` (str, default: 'daily').
- **Detection Logic** (Pseudocode):
  ```python
  fast_ema = data['close'].ewm(span=fast, adjust=False).mean()
  slow_ema = data['close'].ewm(span=slow, adjust=False).mean()
  bullish = (fast_ema.shift(1) < slow_ema.shift(1)) & (fast_ema > slow_ema)
  bearish = (fast_ema.shift(1) > slow_ema.shift(1)) & (fast_ema < slow_ema)
  detected = bullish | bearish  # Or separate patterns for direction
  return detected
  ```
- **Edge Cases**: Flat markets (multiple crosses: filter with volume); short data (NaN handling: drop); direction param for bullish/bearish split.
- **Event Output**: `{"pattern": "MACrossover", "symbol": "AAPL", "timestamp": "...", "price": close, "direction": "bullish", "timeframe": "1min"}`

### High of Day
- **Description**: Intra-day signal when the current high exceeds the session's previous high, indicating potential breakout or strength. (Ties to User Story 1: Real-time intra-day alerts.)
- **Timeframes**: Intra-day (e.g., 1min).
- **Parameters**:
  - `session_start_hour` (int, default: 9): Market open time.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  session_mask = data['timestamp'].dt.hour >= session_start_hour
  session_high = data['high'][session_mask].cummax().shift(1)
  detected = (data['high'] > session_high) & session_mask
  return detected
  ```
- **Edge Cases**: Pre-market data (exclude via mask); ties (no detect); combine with breakout (per User Story 9).
- **Event Output**: `{"pattern": "HighOfDay", "symbol": "AAPL", "timestamp": "...", "price": high, "timeframe": "1min", "direction": "bullish"}`

### Low of Day
- **Description**: Intra-day signal when the current low falls below the session's previous low, indicating potential breakdown or weakness. (Ties to User Story 1: Real-time intra-day alerts.)
- **Timeframes**: Intra-day (e.g., 1min).
- **Parameters**:
  - `session_start_hour` (int, default: 9): Market open time.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  session_mask = data['timestamp'].dt.hour >= session_start_hour
  session_low = data['low'][session_mask].cummin().shift(1)
  detected = (data['low'] < session_low) & session_mask
  return detected
  ```
- **Edge Cases**: Pre-market data (exclude); ties (no detect); combine with volume drop (per User Story 9).
- **Event Output**: `{"pattern": "LowOfDay", "symbol": "AAPL", "timestamp": "...", "price": low, "timeframe": "1min", "direction": "bearish"}`

## Breakout Patterns

### Day1Breakout
- **Description**: Intraday breakout early in the trading session (first 1-2 hours), after a consolidation phase, confirmed by high volume. Targets high-momentum stocks. (Ties to User Story 2: Easy addition as breakout.)
- **Timeframes**: Intraday only (e.g., 1min, 5min).
- **Parameters**:
  - `consolidation_window` (int, default: 20): Bars to check for tight range pre-break.
  - `min_volume_multiple` (float, default: 1.5): Min volume vs. average for confirmation.
  - `session_start_hour` (int, default: 9): Market open (e.g., 9:30 AM ET).
  - `session_end_hour` (int, default: 12): End of breakout window.
- **Detection Logic** (Pseudocode):
  ```python
  session_mask = (data['timestamp'].dt.hour >= session_start_hour) & (data['timestamp'].dt.hour < session_end_hour)
  avg_volume = data['volume'].rolling(50).mean()
  high_break = (data['close'] > data['high'].rolling(consolidation_window).max().shift(1)) & (data['volume'] > min_volume_multiple * avg_volume)
  low_break = (data['close'] < data['low'].rolling(consolidation_window).min().shift(1)) & (data['volume'] > min_volume_multiple * avg_volume)
  detected = (high_break | low_break) & session_mask
  return detected
  ```
- **Edge Cases**: No consolidation (False); low volume break (ignore); direction split (high=long, low=short).
- **Event Output**: `{"pattern": "Day1Breakout", "symbol": "AAPL", "timestamp": "...", "price": close, "direction": "long", "timeframe": "1min"}`

## Intra-day Trend Patterns

### Trending Up
- **Description**: Intra-day momentum signal where price shows consistent upward movement over a short window, often with increasing volume. (Ties to User Story 1: Real-time momentum alerts.)
- **Timeframes**: Intra-day (e.g., 1min, 5min).
- **Parameters**:
  - `window` (int, default: 10): Bars to check for upward trend.
  - `min_slope` (float, default: 0.01): Minimum positive slope for trend line.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  from scipy.stats import linregress
  def rolling_slope(s):
      return linregress(range(len(s)), s).slope if len(s) == window else float('nan')
  slope = data['close'].rolling(window).apply(rolling_slope)
  detected = slope > min_slope
  return detected
  ```
- **Edge Cases**: Short data (NaN: False); flat slope (below min: False); add volume increase filter (per User Story 9).
- **Event Output**: `{"pattern": "TrendingUp", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min", "direction": "bullish"}`

### Trending Down
- **Description**: Intra-day momentum signal where price shows consistent downward movement over a short window, often with increasing volume. (Ties to User Story 1: Real-time momentum alerts.)
- **Timeframes**: Intra-day (e.g., 1min, 5min).
- **Parameters**:
  - `window` (int, default: 10): Bars to check for downward trend.
  - `max_slope` (float, default: -0.01): Maximum negative slope for trend line.
  - `timeframe` (str, default: '1min').
- **Detection Logic** (Pseudocode):
  ```python
  from scipy.stats import linregress
  def rolling_slope(s):
      return linregress(range(len(s)), s).slope if len(s) == window else float('nan')
  slope = data['close'].rolling(window).apply(rolling_slope)
  detected = slope < max_slope
  return detected
  ```
- **Edge Cases**: Short data (NaN: False); flat slope (above max: False); add volume increase filter (per User Story 9).
- **Event Output**: `{"pattern": "TrendingDown", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min", "direction": "bearish"}`

## Integration Notes
- **Scanner Usage**: Add patterns via `scanner.add_pattern(Doji, {'tolerance': 0.05, 'timeframe': '1min'})`. The scanner publishes events to TickStockApp via `EventPublisher` (e.g., Redis pub-sub).
- **Data Prep**: Use `DataBlender` to resample data for desired timeframe before scanning. Historical data from `ohlcv_daily`, real-time ticks appended via `RealTimeScanner`.
- **Extensibility**: Add new patterns by subclassing `BasePattern` or `ReversalPattern`, implementing `detect()`. For candlesticks, consider CandlestickPattern subclass with shared utils (e.g., def calc_body(data)). Supports composites (User Story 9) like Doji & above EMA.

## Implementation Notes
Prioritize implementation based on sprints and complexity:
- **Sprint 5 (Core)**: Start with candlestick patterns (Doji, Hammer) for quick validation with single-bar logic.
- **Sprint 6**: Add trend patterns (MACrossover) to test indicator-based detection.
- **Sprint 7 (Advanced)**: Implement breakouts (Day1Breakout) and reversals (HeadAndShoulders, DoubleBottom) for multi-bar scenarios.
- Use vectorized pandas/numpy ops for efficiency; test with sample data (data/sample_ticks.csv) before real-time integration.
- Future: Add ML-based patterns (e.g., via scikit-learn) after core stability.

This spec serves as the foundation for implementation in `src/patterns/` and testing in `tests/`. Next steps: Prototype these in Sprint 4-6 of our plan.

### Manual Test Diagram (Text-Based for Visualization)
To prototype detections, here's a quick text-based diagram simulating a sample OHLCV DataFrame scan—visualizes how detect() outputs a boolean Series on dummy data (e.g., for Doji). Ties to backtesting (User Story 4) for quick validation. (Note: Defaults may not trigger on this data; tune params like tolerance=0.07 for Doji to match illustrative Trues.)

Sample DataFrame (OHLCV for AAPL, 1min timeframe):
timestamp          open   high   low   close  volume
2025-08-24 09:30   150.0  151.0  149.5  150.1  10000   # Small body, possible Doji (with tuned tolerance)
2025-08-24 09:31   150.1  152.0  149.0  151.5  15000   # Hammer-like (adjust shadow_ratio if needed)
2025-08-24 09:32   151.5  153.0  151.0  152.9  12000   # Closed in top 10%

Scan Output (Boolean Series from detect(), with defaults):
timestamp          Doji   Hammer   ClosedInTop10Percent
2025-08-24 09:30   False  False    False
2025-08-24 09:31   False  False    False
2025-08-24 09:32   False  False    True   # Triggers event publish for each True
Visual Flow: DataBlender --> PatternScanner.scan() --> Detections Series --> Publish Events if True