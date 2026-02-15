### TickStock's Valued Patterns and Indicators
The most valued technical indicators (with associated timeframes) and chart patterns for swing traders (holding days to weeks) and intra-day traders (holding hours within a single day, but not aggressive scalping). We'll prioritize them based on common industry consensus from reliable sources, focusing on high-reliability, frequently cited options that align with trend-following, momentum, and risk management in non-aggressive strategies. 
This is the basis for technical indicators for TickStock.ai's pattern and indicator processing engine. 

### Approach Summary
These are best practices with priorities from my trading experience and preferences and industry standards for these trader types and cross-referencing multiple sources (e.g., Investopedia, TradingView, ThinkMarkets) to avoid bias. 

### Process Updates
All indicators, including session-based ones like VWAP, are recomputed and stored at every WebSocket-raised per-minute event (real-time running value) and during the EOD import batch (final reconciled value). No separate or special update logic is required for any indicator.

### Pattern & Indicator Storage Strategy
Storage Tables (ONLY USE THESE)
- Patterns: daily_patterns table for ALL timeframes
- Indicators: daily_indicators table for ALL timeframes
Timeframe Column
- Use timeframe column to specify bar timeframe: 'daily', 'hourly', '1min', 'weekly', 'monthly'
- Single table design enables flexible timeframe support without schema changes
Persistence Strategy (Sprint 74)
- DELETE + INSERT approach: Remove existing (symbol + indicator/pattern + timeframe), then insert new
- Expiration: Set expiration_date for automatic cleanup (next day for daily, session-based for intraday)
- Metadata: Include source, sprint, and detection context in metadata JSONB field
What NOT to Use
- ❌ intraday_patterns - Legacy table, not used
- ❌ intraday_indicators - Legacy table, not used
- ❌ hourly_patterns - Legacy table, not used
- ❌ Separate tables per timeframe - Use unified tables with timeframe column instead
Example Query
-- Get all indicators for AAPL across all timeframes
SELECT symbol, indicator_type, timeframe, value_data
FROM daily_indicators
WHERE symbol = 'AAPL';


### Table 1: Most Valued Technical Indicators by Trader Type
Prioritized by overall utility (e.g., trend confirmation first, then momentum, volatility, and volume). Timeframes are recommended defaults; adjust based on market volatility.

| Priority | Indicator                          | Description & Key Use                                                                 | Calculation     | Storage         | Trader Type |
|----------|------------------------------------|---------------------------------------------------------------------------------------|-----------------|-----------------|-------------|
| 1        | Moving Averages (SMA/EMA)          | Trend identification, crossovers for entries/exits (10/20/50/200 periods)             | daily           | daily           | Swing       |
| 2        | Relative Strength Index (RSI)      | Momentum, overbought/oversold, divergences (14-period)                                | daily           | daily           | Swing       |
| 3        | MACD                               | Trend strength & momentum crossovers (12,26,9)                                        | daily           | daily           | Swing       |
| 4        | Bollinger Bands                    | Volatility squeezes & overextension (20-period, 2 SD)                                 | daily           | daily           | Swing       |
| 5        | Volume                             | Confirmation of price moves (raw or relative)                                         | daily           | daily           | Swing       |
| 6        | Stochastic Oscillator              | Overbought/oversold momentum (%K/%D crossovers, 14-period)                            | daily           | daily           | Swing       |
| 7        | Average True Range (ATR)           | Volatility for stops & position sizing (14-period)                                    | daily           | daily           | Swing       |
| 8        | Pivot Points (Standard)            | Daily S/R levels from prior day OHLC (PP, R1/R2/R3, S1/S2/S3)                        | daily (prior day) | daily         | Swing       |
| 9        | Pivot Points (Fibonacci)           | Daily S/R levels using Fibonacci ratios (38.2%, 61.8%, 100%)                         | daily (prior day) | daily         | Swing       |
| 1        | Moving Averages (SMA/EMA)          | Intra-day trend & quick signals (5/10/20 periods)                                     | 15min           | 15min           | Intra-day   |
| 2        | Relative Strength Index (RSI)      | Short-term momentum & divergences (14-period)                                         | 15min           | 15min           | Intra-day   |
| 3        | MACD                               | Intra-day momentum changes (12,26,9)                                                  | 15min           | 15min           | Intra-day   |
| 4        | Bollinger Bands                    | Volatility squeezes & breakouts (20-period, 2 SD)                                     | 15min           | 15min           | Intra-day   |
| 5        | Volume Weighted Average Price (VWAP) | Intra-day fair-value benchmark, deviation signals                                   | 1min            | 1min            | Intra-day   |
| 6        | Stochastic Oscillator              | Fast overbought/oversold reads (14-period)                                            | 15min           | 15min           | Intra-day   |
| 7        | Pivot Points                       | Daily S/R levels for intra-day targets (standard, Fibonacci, etc.)                    | daily (prior day) | daily         | Intra-day   |


### Table 2: Most Valued Chart Patterns by Trader Type
Prioritized by reliability (e.g., reversal patterns with >70% success rates like Head and Shoulders first, then continuations). Focus on visual confirmations with volume.

| Priority | Pattern                              | Description & Key Use                                              | Detection Timeframe | Storage              | Trader Type |
|----------|--------------------------------------|--------------------------------------------------------------------|---------------------|----------------------|-------------|
| 1        | Head and Shoulders (incl. Inverse)   | Major reversal on neckline break (~75% reliability)                | daily               | daily                | Swing       |
| 2        | Double Top / Double Bottom           | Reversal after two tests of level                                  | daily               | daily                | Swing       |
| 3        | Ascending / Descending Triangle      | Continuation or reversal on breakout                               | daily, 4h           | daily                | Swing       |
| 4        | Flags / Pennants                     | Brief continuation pause after impulse                             | daily               | daily                | Swing       |
| 5        | Cup and Handle                       | Bullish continuation after rounded base                            | daily, weekly       | daily                | Swing       |
| 6        | Rising / Falling Wedges              | Reversal against prevailing trend                                  | daily               | daily                | Swing       |
| 7        | Range Breakout                       | Continuation after consolidation                                   | daily               | daily                | Swing       |
| 1        | Flags / Pennants                     | Quick intra-day continuation after strong move                     | 5min, 15min         | 15min                | Intra-day   |
| 2        | Triangles (Symmetrical, Asc/Desc)    | Intra-day continuation or reversal on breakout                     | 15min               | 15min                | Intra-day   |
| 3        | Head and Shoulders (incl. Inverse)   | Fast intra-day reversals on neckline break                         | 15min               | 15min                | Intra-day   |
| 4        | Double Top / Double Bottom           | Intra-day reversals after double test                              | 15min               | 15min                | Intra-day   |
| 5        | V-Top / V-Bottom                     | Sharp intra-day exhaustion/reversal spikes                         | 5min, 15min         | 5min, 15min          | Intra-day   |
| 6        | Engulfing (Bullish / Bearish)        | Candle-based reversal signal                                       | 5min, 15min         | 5min, 15min          | Intra-day   |
| 7        | Pin Bar                              | Rejection candle at S/R levels                                     | 5min, 15min         | 5min, 15min          | Intra-day   |

