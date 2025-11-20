# Synthetic Data Mode - User Guide

**Sprint 41 Feature** | **Version**: 1.0 | **Last Updated**: October 7, 2025

---

## Overview

The Synthetic Data Mode enables TickStockAppV2 to generate realistic market data without requiring external API connections. This is ideal for:

- **Development**: Build features without API costs
- **Testing**: Validate pattern detection with known patterns
- **Demos**: Showcase functionality with controlled data
- **Offline Work**: Develop without internet connectivity

The synthetic data provider generates realistic tick data with:
- OHLCV bar structure
- Bid/ask spreads
- Volume fluctuations
- Time-of-day patterns
- Sector-based volatility
- Injected candlestick patterns
- Market scenarios (normal, volatile, crash, rally)

---

## Quick Start

### Enable Synthetic Data

Add to your `.env` file:

```bash
# Enable synthetic mode
USE_SYNTHETIC_DATA=true

# Basic configuration (all optional - defaults shown)
SYNTHETIC_UNIVERSE=market_leaders:top_500
SYNTHETIC_SCENARIO=normal
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_FREQUENCY=0.1
```

### Start Application

```bash
python start_all_services.py
```

You should see in logs:
```
INFO - SYNTHETIC-PROVIDER: Initializing with scenario: normal
INFO - UNIVERSE-LOADER: Loaded 29 symbols from fallback universe
INFO - SYNTHETIC-PROVIDER: Pattern injection enabled (10% frequency)
```

### Switch Back to Real Data

```bash
# In .env
USE_SYNTHETIC_DATA=false
```

Restart services. Application will now use Massive API data.

---

## Configuration Reference

### Core Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `USE_SYNTHETIC_DATA` | boolean | `false` | Enable/disable synthetic mode |
| `SYNTHETIC_UNIVERSE` | string | `market_leaders:top_500` | Universe key from cache_entries |
| `SYNTHETIC_SCENARIO` | string | `normal` | Market scenario (see below) |
| `SYNTHETIC_ACTIVITY_LEVEL` | string | `medium` | Base volatility level |

### Pattern Injection Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SYNTHETIC_PATTERN_INJECTION` | boolean | `true` | Enable pattern injection |
| `SYNTHETIC_PATTERN_FREQUENCY` | float | `0.1` | % of ticks with patterns (0.0-1.0) |
| `SYNTHETIC_PATTERN_TYPES` | string | (all) | Comma-separated pattern names |

**Pattern frequency examples:**
- `0.05` = 5% of bars (realistic - 1-2 per 20 bars)
- `0.1` = 10% of bars (testing - easier to observe)
- `0.2` = 20% of bars (stress testing - very frequent)

**Available patterns:**
- `Doji` - Indecision (open ≈ close)
- `Hammer` - Bullish reversal (long lower shadow)
- `ShootingStar` - Bearish reversal (long upper shadow)
- `BullishEngulfing` - Bullish reversal (large green candle)
- `BearishEngulfing` - Bearish reversal (large red candle)
- `Harami` - Reversal signal (small body inside prior body)

**Example - Only inject hammers and dojis:**
```bash
SYNTHETIC_PATTERN_TYPES=Doji,Hammer
```

---

## Market Scenarios

### normal (Default)
**Use Case**: General development and testing

**Characteristics**:
- Volatility: 1.0x (baseline)
- Volume: 1.0x (normal)
- Trend: Neutral (no bias)
- Spread: 0.1% (tight)

**Example**:
```bash
SYNTHETIC_SCENARIO=normal
```

**Behavior**: Realistic price movements, predictable patterns, suitable for most testing.

---

### volatile
**Use Case**: Test high-volatility handling

**Characteristics**:
- Volatility: 3.0x (high swings)
- Volume: 2.0x (increased)
- Trend: Neutral
- Spread: 0.2% (wider)

**Example**:
```bash
SYNTHETIC_SCENARIO=volatile
```

**Behavior**: Large price swings, rapid movements, stress tests pattern detection.

---

### crash
**Use Case**: Test bearish market conditions

**Characteristics**:
- Volatility: 5.0x (extreme)
- Volume: 4.0x (panic selling)
- Trend: -0.8 (strong downward)
- Spread: 0.5% (very wide)

**Example**:
```bash
SYNTHETIC_SCENARIO=crash
```

**Behavior**: Prices trending down, high volatility, wide spreads. Tests downside protection.

---

### rally
**Use Case**: Test bullish market conditions

**Characteristics**:
- Volatility: 2.0x (elevated)
- Volume: 2.5x (buying pressure)
- Trend: +0.8 (strong upward)
- Spread: 0.15% (moderate)

**Example**:
```bash
SYNTHETIC_SCENARIO=rally
```

**Behavior**: Prices trending up, elevated volume, tests bullish pattern detection.

---

### opening_bell
**Use Case**: Simulate market open conditions

**Characteristics**:
- Volatility: 4.0x (very high)
- Volume: 5.0x (extreme)
- Trend: Neutral
- Spread: 0.3% (wide)

**Example**:
```bash
SYNTHETIC_SCENARIO=opening_bell
```

**Behavior**: Extreme volatility and volume, mimics first 30 minutes of trading.

---

## Symbol Universe

### Default Universe

By default, synthetic mode uses a **29-symbol fallback universe** covering 7 sectors:

**Technology** (9 symbols):
- AAPL, MSFT, GOOGL, NVDA, META, TSLA, AMD, INTC, QQQ

**Healthcare** (4 symbols):
- UNH, JNJ, PFE, ABBV

**Financial** (6 symbols):
- JPM, BAC, WFC, GS, SPY, IWM

**Consumer** (4 symbols):
- AMZN, WMT, HD, NKE

**Communication** (3 symbols):
- DIS, NFLX, CMCSA

**Energy** (2 symbols):
- XOM, CVX

**Materials** (1 symbol):
- GLD

### Database Universe

If your database has universe data:

```bash
# Use database universe (500+ symbols)
SYNTHETIC_UNIVERSE=market_leaders:top_500
```

**Note**: If universe key not found, automatically falls back to 29-symbol universe.

### Verify Loaded Universe

Check logs on startup:
```
INFO - UNIVERSE-LOADER: Loaded 29 symbols from fallback universe
```

Or query provider statistics:
```python
from src.infrastructure.data_sources.factory import DataProviderFactory
provider = DataProviderFactory.get_provider(config)
stats = provider.get_statistics()
print(f"Universe size: {stats['universe_size']}")
```

---

## Sector-Based Behavior

Each symbol has sector-specific characteristics:

| Sector | Volatility Factor | Typical Price Range | Examples |
|--------|-------------------|---------------------|----------|
| Technology | 1.5x | $50-$300 | AAPL, NVDA, MSFT |
| Healthcare | 1.2x | $30-$200 | UNH, JNJ |
| Financial | 1.0x | $20-$150 | JPM, BAC, SPY |
| Energy | 1.3x | $30-$120 | XOM, CVX |
| Utilities | 0.6x | $50-$100 | (not in fallback) |
| Consumer | 0.9x | $25-$180 | AMZN, WMT |
| Communication | 1.2x | $40-$200 | DIS, NFLX |
| Materials | 1.1x | $35-$140 | GLD |

**Example**: NVDA (Technology) will be 1.5x more volatile than JPM (Financial).

---

## Time-of-Day Patterns

Synthetic data simulates realistic intraday patterns:

### Opening Bell (9:30-10:00 AM ET)
- Volume: 3.0x normal
- Volatility: 2.0x normal

### Mid-Day (10:00 AM-3:00 PM ET)
- Volume: 1.0x normal
- Volatility: 1.0x normal

### Lunch Lull (12:00-1:00 PM ET)
- Volume: 0.5x normal
- Volatility: 0.7x normal

### Closing Hour (3:00-4:00 PM ET)
- Volume: 2.0x normal
- Volatility: 1.5x normal

**Note**: Patterns persist even after hours but with reduced intensity.

---

## Common Use Cases

### Use Case 1: Pattern Detection Testing

**Goal**: Verify TickStockPL detects specific patterns

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=normal
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_FREQUENCY=0.2  # 20% for visibility
SYNTHETIC_PATTERN_TYPES=Doji,Hammer
```

**Steps**:
1. Start TickStockAppV2 (generates ticks)
2. Start TickStockPL (detects patterns)
3. Monitor Redis channel: `tickstock:patterns:detected`
4. Verify Doji/Hammer patterns detected

**Expected Result**: ~20% of bars should trigger pattern detections.

---

### Use Case 2: Crash Scenario Validation

**Goal**: Test how system handles market crash

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=crash
SYNTHETIC_PATTERN_INJECTION=true
```

**Observations**:
- Prices trend downward (-0.8 bias)
- High volatility (5.0x)
- Wide spreads (0.5%)
- Expect more bearish patterns (BearishEngulfing, ShootingStar)

**What to Test**:
- Alert systems trigger correctly
- Downside protection activates
- Pattern detection still accurate under volatility

---

### Use Case 3: Offline Development

**Goal**: Develop new features without internet/API

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=normal
SYNTHETIC_PATTERN_INJECTION=false  # Clean data
```

**Benefit**: Predictable data flow, no API costs, no rate limits.

---

### Use Case 4: Demo Mode

**Goal**: Showcase platform with impressive data

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=volatile
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_FREQUENCY=0.15
```

**Result**: Frequent patterns, exciting price action, realistic but active.

---

## Troubleshooting

### Issue: No Ticks Generated

**Symptoms**: No logs showing tick generation

**Checks**:
1. Verify `USE_SYNTHETIC_DATA=true` in `.env`
2. Check logs for initialization:
   ```
   INFO - SYNTHETIC-PROVIDER: Initializing
   ```
3. Restart services to pick up `.env` changes

**Solution**: Ensure config loaded correctly:
```python
from src.core.services.config_manager import get_config
print(get_config()['USE_SYNTHETIC_DATA'])  # Should print True
```

---

### Issue: No Patterns Detected

**Symptoms**: Ticks generated but no patterns detected by TickStockPL

**Checks**:
1. Verify `SYNTHETIC_PATTERN_INJECTION=true`
2. Check pattern frequency (try increasing to 0.2)
3. Verify TickStockPL is running and consuming ticks
4. Monitor Redis: `redis-cli MONITOR | findstr "tickstock:market:ticks"`

**Solution**: Increase pattern frequency for testing:
```bash
SYNTHETIC_PATTERN_FREQUENCY=0.2
```

---

### Issue: Universe Loading Failed

**Symptoms**: Logs show universe loading error

**Expected Behavior**:
```
WARN - UNIVERSE-LOADER: No symbols found for 'market_leaders:top_500', using fallback
INFO - UNIVERSE-LOADER: Using fallback universe with 29 symbols
```

**This is NORMAL**: Fallback ensures provider always works.

**To use database universe**:
1. Verify universe exists: Query `cache_entries` table
2. Use existing key: `SYNTHETIC_UNIVERSE=existing:universe:key`
3. Or keep fallback (recommended for resilience)

---

### Issue: Prices Don't Match Scenario

**Symptoms**: Crash scenario not showing downward prices

**Explanation**: Price movement is stochastic, not deterministic. Scenario affects:
- **Trend bias** (80% of movements down in crash)
- **Volatility** (larger swings)
- **Not guaranteed** (random walk still applies)

**Observation Window**: Watch 50-100 ticks to see trend.

**Verification**: Check multipliers, not prices:
```python
provider = DataProviderFactory.get_provider(config)
print(provider.volatility_multiplier)  # Should be 5.0 for crash
print(provider.trend_bias)  # Should be -0.8 for crash
```

---

## Performance Notes

### Tick Generation Speed
- **Target**: <1ms per tick
- **Actual**: <0.5ms per tick
- **No performance degradation** vs real data provider

### Pattern Injection Overhead
- **Without patterns**: ~0.3ms per tick
- **With patterns (20%)**: ~0.4ms per tick
- **Overhead**: ~33% (acceptable)

### Memory Usage
- **Universe loader**: ~5KB (29 symbols)
- **Provider overhead**: Negligible
- **No memory leaks** detected

### Initialization Time
- **Cache loading**: ~50ms
- **Universe building**: ~5ms
- **Total**: <100ms

---

## Integration with TickStockPL

### Data Flow

```
TickStockAppV2 (Synthetic Provider)
    ↓
Generate realistic tick data
    ↓
Inject patterns (if enabled)
    ↓
Publish to Redis: tickstock:market:ticks
    ↓
TickStockPL consumes ticks
    ↓
Pattern detection engine
    ↓
Publish to Redis: tickstock:patterns:detected
    ↓
TickStockAppV2 displays on dashboard
```

### Source Transparency

**TickStockPL is source-agnostic** - it cannot distinguish synthetic from real data.

Each tick includes `source` field:
- Real data: `source: 'massive'`
- Synthetic: `source: 'simulated'`

But TickStockPL processes identically.

### Validation

To verify TickStockPL detects synthetic patterns:

1. **Monitor tick channel**:
   ```bash
   redis-cli SUBSCRIBE tickstock:market:ticks
   ```

2. **Monitor pattern channel**:
   ```bash
   redis-cli SUBSCRIBE tickstock:patterns:detected
   ```

3. **Compare counts**:
   - With 10% pattern injection
   - Expect ~10% of ticks to trigger pattern detections
   - Variance is normal (statistical distribution)

---

## Best Practices

### 1. Development Workflow
- Start with `normal` scenario, no pattern injection
- Clean data for baseline testing
- Enable patterns once core functionality works

### 2. Pattern Testing
- Use 15-20% pattern frequency for visibility
- Test one pattern type at a time initially
- Verify detection before combining patterns

### 3. Scenario Testing
- Test `normal` first (baseline)
- Test `volatile` (stress test)
- Test `crash` and `rally` (bias verification)
- Test `opening_bell` (extreme conditions)

### 4. Production Prep
- Always test with `USE_SYNTHETIC_DATA=false` before deployment
- Verify real data flow works identically
- Keep synthetic mode for staging/demo environments

### 5. Debugging
- Check logs for initialization messages
- Verify `.env` changes require restart
- Use Redis MONITOR to observe data flow
- Query provider statistics for diagnostics

---

## Configuration Examples

### Minimal Configuration
```bash
USE_SYNTHETIC_DATA=true
```
Everything else uses defaults (normal scenario, 10% patterns, fallback universe).

---

### Development Configuration
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=normal
SYNTHETIC_PATTERN_INJECTION=false
```
Clean, predictable data for feature development.

---

### Testing Configuration
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=volatile
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_FREQUENCY=0.2
```
Frequent patterns, high volatility, stress testing.

---

### Demo Configuration
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=rally
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_FREQUENCY=0.15
SYNTHETIC_PATTERN_TYPES=BullishEngulfing,Hammer
```
Bullish patterns in uptrending market, visually appealing.

---

### Crash Test Configuration
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_SCENARIO=crash
SYNTHETIC_PATTERN_INJECTION=true
SYNTHETIC_PATTERN_TYPES=BearishEngulfing,ShootingStar
```
Bearish patterns in crashing market, tests downside handling.

---

## FAQ

**Q: Can I use synthetic data in production?**

A: No. Synthetic mode is for development, testing, and demos only. Always use `USE_SYNTHETIC_DATA=false` in production.

---

**Q: How realistic is the synthetic data?**

A: Very realistic for testing purposes:
- Proper OHLCV structure
- Realistic bid/ask spreads
- Time-of-day patterns
- Sector-based volatility
- Injected patterns match real candlestick definitions

However, it's still simulated and lacks:
- Real market microstructure
- News-driven events
- Institutional order flow
- Actual price discovery

---

**Q: Why use fallback universe instead of database?**

A: **Resilience**. Fallback ensures synthetic mode always works, even if:
- Database is unavailable
- Universe key doesn't exist
- Cache initialization fails

The 29-symbol fallback covers major sectors and popular symbols - sufficient for most testing.

---

**Q: Can I add custom symbols to the universe?**

A: Currently no. Universe is either:
1. Loaded from database via `SYNTHETIC_UNIVERSE` key
2. Falls back to hardcoded 29 symbols

**Future enhancement**: Custom universe file support.

---

**Q: How do I verify patterns are actually being injected?**

A: Check provider statistics:
```python
stats = provider.get_statistics()
print(f"Patterns injected: {stats['patterns_injected']}")
print(f"Pattern counts: {stats['pattern_counts']}")
```

Or monitor logs:
```
DEBUG - SYNTHETIC-PROVIDER: Injected pattern: Doji for AAPL
```

---

**Q: Can I change scenario without restarting?**

A: No. Configuration is loaded at provider initialization. Change `.env` and restart services.

---

**Q: What if I want different pattern frequencies for different patterns?**

A: Currently not supported. All enabled patterns use same frequency.

**Workaround**: Run multiple test sessions with different `SYNTHETIC_PATTERN_TYPES` configurations.

---

## Getting Help

**Issues**:
- Check logs for error messages
- Verify `.env` configuration
- Ensure services restarted after config changes

**Documentation**:
- User Guide: `docs/guides/synthetic_data_guide.md` (this file)
- Developer Guide: `docs/guides/synthetic_data_developer_guide.md`
- API Reference: `docs/api/synthetic_data_api.md`

**Testing**:
- Integration tests: `tests/integration/test_sprint41_synthetic_integration.py`
- Run tests: `python -m pytest tests/integration/test_sprint41_synthetic_integration.py -v`

---

**Last Updated**: October 7, 2025 | **Sprint**: 41 Phase 5 | **Status**: Complete ✅
