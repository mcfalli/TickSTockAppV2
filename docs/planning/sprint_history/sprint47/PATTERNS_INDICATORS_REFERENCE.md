# TickStock.ai Patterns & Indicators Reference Guide

**Sprint 47 Documentation**
**Created**: 2025-10-22
**Purpose**: Comprehensive reference for all patterns and indicators with enabled status, key attributes, and logic summaries

---

## Table of Contents
1. [Pattern Reference](#pattern-reference)
2. [Indicator Reference](#indicator-reference)
3. [Usage Notes](#usage-notes)

---

## Pattern Reference

### Enabled Patterns (5 Active)

| Pattern Name | Category | Enabled | Timeframes | Bars Required | Confidence | Risk | Logic Summary | Code Reference |
|-------------|----------|---------|------------|---------------|------------|------|---------------|----------------|
| **Doji** | Candlestick | ✅ Yes | Daily, Weekly, Hourly, Intraday | 1 | 50% | Low | Single-bar indecision pattern. Detects when `ABS(open - close) < (high - low) * 0.1`. Open and close are very close, indicating market indecision and potential reversal. | `src.patterns.candlestick.doji` |
| **Hammer** | Candlestick | ✅ Yes | Daily, Weekly, Intraday | 1 | 60% | Medium | Bullish reversal with small body at top and long lower shadow. Detects when `lower_shadow > 2 * body AND upper_shadow < 0.5 * body`. Indicates rejection of lower prices. | `src.patterns.candlestick.hammer` |
| **PriceChange** | Momentum | ✅ Yes | Intraday, 1min, Hourly, Daily | 1 | 70% | Low | Test pattern detecting price changes >1% between bars. Bullish if price up, bearish if down. Used for streaming architecture validation. | `src.patterns.candlestick.price_change` |
| **HeadShoulders** | Multi-bar | ✅ Yes | Daily, Weekly, Monthly, Intraday | 20 | 80% | High | Bearish reversal with left shoulder, higher head, right shoulder, and neckline break. Detects three peaks where middle peak is highest, followed by break below support (neckline). | `src.patterns.multi_bar` (HeadAndShouldersPattern) |
| **AlwaysDetected** | Test | ✅ Yes | Intraday, 1min, Hourly, Daily | 1 | 70% | Low | Architecture test pattern. Returns detection with confidence=0.85 on every bar. No actual logic, used for integration testing. | `src.patterns.candlestick.always_detected` |

### Disabled Patterns (20 Inactive)

| Pattern Name | Category | Enabled | Timeframes | Bars Required | Confidence | Risk | Logic Summary | Code Reference |
|-------------|----------|---------|------------|---------------|------------|------|---------------|----------------|
| **BullishEngulfing** | Candlestick | ❌ No | Hourly, Daily, Weekly, Monthly | 2 | 70% | Medium | Two-candle bullish reversal. Current bullish candle completely engulfs previous bearish candle body. Requires body engulfment validation. | `src.patterns.candlestick.bullish_engulfing` |
| **BearishEngulfing** | Candlestick | ❌ No | Hourly, Daily, Weekly, Monthly | 2 | 70% | Medium | Two-candle bearish reversal. Current bearish candle completely engulfs previous bullish candle body. Mirror of BullishEngulfing. | `src.patterns.candlestick.bearish_engulfing` |
| **HangingMan** | Candlestick | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 65% | Medium | Bearish reversal with same structure as Hammer but appears in uptrends. Long lower shadow with small body at top. | `src.patterns.candlestick.hanging_man` |
| **DailyBO** | Pattern | ❌ No | Daily | 1 | 50% | Medium | Daily breakout pattern. Detects when `price > daily_high AND momentum > 0`. Targets breakout above recent high with positive momentum. | `event_detector.DailyBreakoutDetector` |
| **WeeklyBO** | Pattern | ❌ No | Weekly | 1 | 50% | Medium | Weekly breakout pattern. Detects when `price > weekly_high AND volume > avg_volume * 1.5`. Requires volume confirmation. | `event_detector.WeeklyBreakoutDetector` |
| **EngulfingBullish** | Pattern | ❌ No | Daily | 1 | 50% | High | Legacy bullish engulfing. Detects when `current_body > previous_body AND bullish engulfs bearish`. Multi-bar pattern checking body sizes. | `pattern_detector.EngulfingDetector` |
| **ShootingStar** | Pattern | ❌ No | Daily | 1 | 50% | Medium | Bearish reversal with long upper shadow. Detects when `upper_shadow > 2 * body AND lower_shadow < 0.5 * body`. Indicates rejection of higher prices. | `pattern_detector.ShootingStarDetector` |
| **Support** | Pattern | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 50% | Low | Support level pattern. Detects when `price >= support_level * 0.98 AND previous_decline >= 2%`. Price bouncing off support. | `pattern_detector.SupportDetector` |
| **Resistance** | Pattern | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 50% | Low | Resistance level pattern. Detects when `price <= resistance_level * 1.02 AND previous_advance >= 2%`. Price hitting resistance ceiling. | `pattern_detector.ResistanceDetector` |
| **Triangle** | Pattern | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 50% | Medium | Triangle consolidation pattern. Detects when `range_narrowing AND volume_declining`. Continuation/breakout setup. | `pattern_detector.TriangleDetector` |
| **VolumeSpike** | Streaming | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 50% | Medium | Volume spike signal. Detects when `volume > avg_volume * 3.0`. Indicates unusual trading activity. | `src.patterns.streaming` (VolumeSpikePattern) |
| **MACrossover** | Multi-bar | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 75% | Low | Moving average crossover. Fast MA crosses slow MA (bullish: fast > slow, bearish: fast < slow). Trend change indicator. | `src.patterns.multi_bar` (MovingAverageCrossoverPattern) |
| **SRBreakout** | Multi-bar | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 70% | Medium | Support/Resistance breakout. Price breaks above resistance or below support with volume confirmation. | `src.patterns.multi_bar` (SupportResistanceBreakoutPattern) |
| **DoubleBottom** | Multi-bar | ❌ No | Daily, Weekly, Monthly | 20 | 75% | Medium | Bullish reversal with two similar lows. Detects two lows within tolerance, breaking above intervening high. "W" pattern formation. | `src.patterns.multi_bar` (DoubleBottomPattern) |
| **MinuteTrend** | Streaming | ❌ No | 1min, Hourly | 20 | 60% | Low | Minute-level trend detection. Analyzes short-term momentum using 20-bar window. For intraday trading signals. | `src.patterns.streaming` (MinuteTrendPattern) |
| **IntradayGap** | Streaming | ❌ No | 1min, Hourly | 1 | 70% | Medium | Intraday gap pattern. Detects gaps between bars during trading session. Targets continuation or reversal setups. | `src.patterns.streaming` (IntradayGapPattern) |
| **MomentumSpike** | Streaming | ❌ No | 1min, Hourly | 1 | 65% | Medium | Momentum spike pattern. Detects rapid price acceleration in short timeframe. For scalping/day trading. | `src.patterns.streaming` (MomentumSpikePattern) |
| **SwingHighLow** | Daily | ❌ No | Hourly, Daily, Weekly, Monthly | 1 | 65% | Low | Swing high/low detection. Identifies local peaks and troughs using pivot point analysis. Support/resistance reference. | `src.patterns.daily.swing_high_low_pattern` (SwingHighLowPattern) |
| **WeeklyBreakout** | Daily | ❌ No | Weekly | 1 | 70% | Medium | Weekly timeframe breakout. Similar to WeeklyBO but different implementation in daily patterns module. | `src.patterns.daily.weekly_breakout_pattern` (WeeklyBreakoutPattern) |
| **MultiDayBreakout** | Daily | ❌ No | Daily, Weekly, Monthly | 1 | 75% | Medium | Multi-day breakout pattern. Detects breakouts requiring multiple days of confirmation. Reduces false positives. | `src.patterns.daily.multi_day_breakout_pattern` (MultiDayBreakoutPattern) |

---

## Indicator Reference

### Enabled Indicators (5 Active)

| Indicator Name | Category | Enabled | Period | Output Type | Typical Range | Bars Required | Logic Summary | Code Reference |
|---------------|----------|---------|--------|-------------|---------------|---------------|---------------|----------------|
| **RSI** | Momentum | ✅ Yes | 14 | Percentage | 0-100 | 14 | Relative Strength Index. Measures momentum by comparing magnitude of recent gains vs losses. RSI > 70 = overbought, RSI < 30 = oversold. Uses 14-period EMA for smoothing. | `src.indicators.rsi` |
| **SMA** | Trend | ✅ Yes | 20 | Numeric | Varies | 20 | Simple Moving Average. Calculates average of closing prices over period (20, 50, 200 common). Smooths price data to identify trend direction. | `src.indicators.sma` |
| **SMA_5** | Trend | ✅ Yes | 5 | Numeric | Varies | 5 | 5-period Simple Moving Average. Fast-reacting MA for short-term trends. Calculates average of last 5 closing prices to smooth short-term fluctuations. | `src.indicators.sma_5` |
| **SMA5** | Indicator | ✅ Yes | 14 | Numeric | N/A | 5 | Alternative 5-period SMA implementation. Similar to SMA_5 but different module. Used for intraday and short-term analysis. | `src.indicators.sma_5` |
| **AlwaysTrue** | Test | ✅ Yes | 1 | Numeric | Always 1.0 | 1 | Architecture test indicator. Returns value=1.0 on every bar. No actual logic, used for integration testing. | `src.indicators.always_true` |

### Disabled Indicators (13 Inactive)

| Indicator Name | Category | Enabled | Period | Output Type | Typical Range | Bars Required | Logic Summary | Code Reference |
|---------------|----------|---------|--------|-------------|---------------|---------------|---------------|----------------|
| **MACD** | Indicator | ❌ No | N/A | Numeric | N/A | 26 | Moving Average Convergence Divergence. Calculates difference between 12-EMA and 26-EMA (MACD line), then 9-EMA of MACD (signal line). Crossovers indicate trend changes. | `src.indicators.daily_indicators` |
| **Stochastic** | Indicator | ❌ No | 14 | Percentage | 0-100 | 1 | Stochastic Oscillator. Compares current close to price range over 14 periods. %K = (current - lowest_low) / (highest_high - lowest_low) * 100. %D = 3-period MA of %K. | `src.indicators.daily_indicators` |
| **Williams_R** | Indicator | ❌ No | 14 | Percentage | -100 to 0 | 1 | Williams %R. Momentum indicator showing overbought/oversold. Calculated as (highest_high - current) / (highest_high - lowest_low) * -100. Values near -20 = overbought, near -80 = oversold. | `src.indicators.daily_indicators` |
| **CCI** | Indicator | ❌ No | 20 | Numeric | -200 to 200 | 1 | Commodity Channel Index. Measures deviation from average price. CCI = (typical_price - SMA) / (0.015 * mean_deviation). >100 = overbought, <-100 = oversold. | `src.indicators.daily_indicators` |
| **EMA** | Indicator | ❌ No | 20 | Numeric | Varies | 26 | Exponential Moving Average. Weighted MA giving more weight to recent prices. Supports multiple periods (12, 26 common). Reacts faster than SMA to price changes. | `src.indicators.daily_indicators` |
| **Bollinger_Bands** | Indicator | ❌ No | 20 | Numeric | Varies | 1 | Bollinger Bands. Creates price envelope using 20-period SMA ± 2 standard deviations. Upper/lower bands adapt to volatility. Price touching bands indicates overbought/oversold. | `src.indicators.daily_indicators` |
| **OBV** | Indicator | ❌ No | N/A | Numeric | Varies | 1 | On-Balance Volume. Cumulative volume indicator. Adds volume on up days, subtracts on down days. Divergences between OBV and price indicate potential reversals. | `src.indicators.daily_indicators` |
| **Volume_SMA** | Indicator | ❌ No | 20 | Numeric | Varies | 1 | Volume Simple Moving Average. 20-period average of volume. Used to identify unusual volume (current volume vs Volume_SMA). Volume spikes indicate increased interest. | `src.indicators.daily_indicators` |
| **VWAP** | Indicator | ❌ No | N/A | Numeric | Varies | 1 | Volume Weighted Average Price. Cumulative (price * volume) / cumulative volume for session. Intraday benchmark for execution quality. Price above VWAP = bullish bias. | `src.indicators.intraday_indicators` |
| **ATR** | Indicator | ❌ No | 14 | Numeric | Varies | 20 | Average True Range. Measures volatility by averaging true range over 14 periods. True Range = max(high-low, abs(high-prev_close), abs(low-prev_close)). Higher ATR = higher volatility. | `src.indicators.daily_indicators` |
| **Bollinger_Width** | Indicator | ❌ No | 20 | Numeric | Varies | 1 | Bollinger Band Width. Measures distance between upper and lower bands: (upper_band - lower_band) / middle_band. Narrow width = low volatility (breakout setup), wide = high volatility. | `src.indicators.daily_indicators` |
| **Relative_Strength_SPY** | Indicator | ❌ No | 20 | Percentage | Varies | 1 | Relative Strength vs SPY. Compares stock performance to S&P 500 (SPY). RS = (stock_price / SPY_price) / (stock_price_20_days_ago / SPY_price_20_days_ago). >1 = outperforming. | `src.indicators.daily_indicators` |
| **Relative_Strength_QQQ** | Indicator | ❌ No | 20 | Percentage | Varies | 1 | Relative Strength vs QQQ. Compares stock performance to Nasdaq 100 (QQQ). Same calculation as RS_SPY but vs QQQ. Useful for tech stock comparison. | `src.indicators.daily_indicators` |

---

## Usage Notes

### Pattern Categories

- **Candlestick**: Single or few-bar formations based on OHLC relationships (body, shadows)
- **Multi-bar**: Complex patterns requiring analysis of multiple bars (3-50+)
- **Momentum**: Patterns detecting price velocity or acceleration changes
- **Test**: Patterns used exclusively for architecture and integration testing
- **Daily/Streaming**: Timeframe-specific pattern implementations
- **Pattern (Legacy)**: Older pattern implementations, candidates for refactoring

### Indicator Categories

- **Momentum**: Measures rate of price change (RSI, MACD, Stochastic)
- **Trend**: Identifies direction and strength of price movement (SMA, EMA)
- **Volatility**: Measures price variation magnitude (ATR, Bollinger Bands)
- **Volume**: Analyzes trading volume patterns (OBV, Volume_SMA, VWAP)
- **Test**: Indicators used for testing architecture only

### Key Fields Explained

- **Bars Required**: Minimum historical bars needed for calculation
- **Confidence Threshold**: Minimum confidence % for pattern detection to trigger
- **Risk Level**: Estimated risk of false signals (Low/Medium/High)
- **Timeframes**: Supported bar intervals (Intraday=1min, Hourly, Daily, Weekly, Monthly)
- **Period**: Lookback window for indicator calculations
- **Output Type**: Data type returned (Numeric, Percentage)

### TickStockPL Integration

All pattern detection and indicator calculation logic resides in **TickStockPL** (Producer).
TickStockAppV2 (Consumer) receives results via Redis pub-sub channels:
- `tickstock:patterns:streaming` - Real-time pattern detections
- `tickstock:patterns:detected` - High confidence patterns (≥80%)
- `tickstock:indicators:streaming` - Real-time indicator values

### Database Storage

Pattern/Indicator definitions stored in `pattern_definitions` and `indicator_definitions` tables.
Detection results stored by timeframe:
- `intraday_patterns` / `intraday_indicators` (1-minute bars)
- `hourly_patterns` (60-minute bars)
- `daily_patterns` / `daily_indicators` (daily bars)
- `weekly_patterns` / `monthly_patterns` (aggregated timeframes)

### Enabling/Disabling

To enable a pattern or indicator:
1. Update `enabled` field in database definition table
2. Restart TickStockPL services to reload configuration
3. Monitor Redis channels for incoming detections

**Note**: Test patterns/indicators (AlwaysDetected, AlwaysTrue) should remain enabled only in development environments.

---

## References

- Pattern Library Specification: `docs/planning/patterns_library_patterns.md`
- Database Schema: `docs/data/data_table_definitions.md`
- Redis Integration: `docs/architecture/redis-integration.md`
- TickStockPL Code Reference: `/C:/Users/McDude/TickStockPL/src/patterns/`

---

**Last Updated**: 2025-10-22
**Maintained By**: Sprint 47 Documentation Initiative
