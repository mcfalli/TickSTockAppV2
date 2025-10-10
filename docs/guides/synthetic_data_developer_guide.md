# Synthetic Data Mode - Developer Guide

**Sprint 41 Feature** | **Version**: 1.0 | **Last Updated**: October 7, 2025

---

## Overview

This guide is for developers who want to extend or customize the synthetic data system. Topics covered:

- Architecture and design patterns
- Adding new scenarios
- Adding new candlestick patterns
- Customizing sector characteristics
- Performance optimization
- Testing strategies

---

## Architecture

### Component Overview

```
src/infrastructure/data_sources/
├── factory.py                    # DataProviderFactory - creates providers
├── base_provider.py              # BaseDataProvider - abstract interface
└── synthetic/
    ├── __init__.py
    ├── provider.py               # SimulatedDataProvider - main implementation
    └── universe_loader.py        # UniverseLoader - symbol universe management
```

### Class Relationships

```
BaseDataProvider (Abstract)
    ↑
    └── SimulatedDataProvider
            ├── Uses: UniverseLoader
            ├── Uses: CacheControl (via UniverseLoader)
            └── Publishes: TickData objects

DataProviderFactory
    └── Creates: SimulatedDataProvider or PolygonDataProvider
                 based on USE_SYNTHETIC_DATA config
```

### Design Patterns

**1. Factory Pattern**
- `DataProviderFactory.get_provider(config)` creates appropriate provider
- Client code never instantiates providers directly
- Easy to swap implementations

**2. Strategy Pattern**
- Different scenarios implement different volatility/volume strategies
- Loaded at runtime based on configuration
- No conditional logic in tick generation

**3. Template Method Pattern**
- `generate_tick_data()` defines structure
- Subcomponents handle specifics (pattern injection, price calculation)
- Easy to extend without modifying core logic

---

## Adding New Scenarios

### Step 1: Define Scenario Parameters

Edit `src/infrastructure/data_sources/synthetic/provider.py`:

```python
def _load_scenario(self):
    """Load scenario-specific parameters."""
    scenarios = {
        'normal': {...},
        'volatile': {...},
        # ... existing scenarios

        # NEW SCENARIO
        'pre_market': {
            'volatility_multiplier': 2.5,
            'volume_multiplier': 0.3,  # Low volume pre-market
            'trend_bias': 0.2,         # Slight upward bias
            'spread_pct': 0.003        # Wider spreads
        }
    }
```

### Step 2: Document Scenario Behavior

Add to user guide with:
- **Use Case**: When to use this scenario
- **Characteristics**: Multipliers and behaviors
- **Example Configuration**: `.env` settings
- **Expected Behavior**: What to observe

### Step 3: Add Test Case

Edit `tests/integration/test_sprint41_synthetic_integration.py`:

```python
def test_scenario_volatility(self, config):
    """Test that scenario multipliers are set correctly."""
    scenarios = {
        'normal': (1.0, 0.0),
        # ... existing scenarios
        'pre_market': (2.5, 0.2),  # Add new scenario
    }

    for scenario, (expected_vol, expected_trend) in scenarios.items():
        test_config = config.copy()
        test_config['SYNTHETIC_SCENARIO'] = scenario
        provider = DataProviderFactory.get_provider(test_config)

        assert provider.volatility_multiplier == expected_vol
        assert provider.trend_bias == expected_trend
```

### Step 4: Verify

Run tests:
```bash
python -m pytest tests/integration/test_sprint41_synthetic_integration.py::TestSyntheticDataIntegration::test_scenario_volatility -v
```

### Scenario Design Guidelines

**Volatility Multiplier** (0.5x - 5.0x):
- `0.5-0.8`: Low volatility (utilities, stable markets)
- `1.0`: Normal market conditions
- `2.0-3.0`: Elevated volatility (earnings season, Fed announcements)
- `4.0-5.0`: Extreme volatility (crash, panic)

**Volume Multiplier** (0.3x - 5.0x):
- `0.3-0.5`: Low volume (pre-market, holidays)
- `1.0`: Normal volume
- `2.0-3.0`: Elevated (institutional activity)
- `4.0-5.0`: Extreme (panic selling, squeeze)

**Trend Bias** (-1.0 to +1.0):
- `-0.8 to -1.0`: Strong downtrend (crash)
- `-0.3 to -0.5`: Mild downtrend
- `0.0`: Neutral (random walk)
- `+0.3 to +0.5`: Mild uptrend
- `+0.8 to +1.0`: Strong uptrend (rally)

**Spread Percentage** (0.001 - 0.01):
- `0.001` (0.1%): Tight spreads (liquid stocks)
- `0.002` (0.2%): Normal spreads
- `0.005` (0.5%): Wide spreads (volatility)
- `0.01` (1.0%): Very wide (illiquid, crisis)

---

## Adding New Candlestick Patterns

### Step 1: Define Pattern Structure

Edit `src/infrastructure/data_sources/synthetic/provider.py`:

```python
PATTERNS = {
    'Doji': PatternDefinition(...),
    # ... existing patterns

    # NEW PATTERN - Spinning Top
    'SpinningTop': PatternDefinition(
        name='SpinningTop',
        open_pct=0.998,    # Small body (2% range)
        high_pct=1.01,     # Upper shadow (1%)
        low_pct=0.99,      # Lower shadow (1%)
        close_pct=1.002    # Close slightly above open
    )
}
```

### Pattern Definition Parameters

- **open_pct**: Open price as % of base price
- **high_pct**: High price as % of base price
- **low_pct**: Low price as % of base price
- **close_pct**: Close price as % of base price

**Base price** is calculated from prior tick's close + trend/volatility.

### Step 2: Understand Pattern Anatomy

```
High (high_pct)
    ↑
    |----  Upper shadow
    |
  Close (close_pct)
    |----  Body
  Open (open_pct)
    |
    |----  Lower shadow
    ↓
Low (low_pct)
```

**Example - Hammer (Bullish Reversal)**:
```python
'Hammer': PatternDefinition(
    name='Hammer',
    open_pct=0.998,    # Small body
    high_pct=1.001,    # Tiny upper shadow (0.1%)
    low_pct=0.98,      # Long lower shadow (2%)
    close_pct=1.0      # Close at top of body
)
```

This creates:
- **Long lower shadow** (2% below open)
- **Small body** (0.2% range)
- **Tiny upper shadow** (0.1% above close)
- **Bullish signal** (price recovered from lows)

### Step 3: Add to Configuration

Edit `src/core/services/config_manager.py`:

```python
DEFAULTS = {
    # ...
    'SYNTHETIC_PATTERN_TYPES': 'Doji,Hammer,ShootingStar,BullishEngulfing,BearishEngulfing,Harami,SpinningTop',
}
```

### Step 4: Test Pattern Injection

Create test to verify pattern structure:

```python
def test_new_pattern_structure():
    """Verify SpinningTop pattern structure."""
    provider = DataProviderFactory.get_provider({
        'USE_SYNTHETIC_DATA': True,
        'SYNTHETIC_PATTERN_INJECTION': True,
        'SYNTHETIC_PATTERN_TYPES': 'SpinningTop'
    })

    # Generate many ticks to get pattern
    for _ in range(100):
        tick = provider.generate_tick_data('AAPL')

        if tick.pattern_injected == 'SpinningTop':
            # Verify pattern structure
            body_size = abs(tick.tick_close - tick.tick_open)
            upper_shadow = tick.tick_high - max(tick.tick_open, tick.tick_close)
            lower_shadow = min(tick.tick_open, tick.tick_close) - tick.tick_low

            # SpinningTop should have small body, equal shadows
            assert body_size < tick.tick_close * 0.005  # <0.5% body
            assert abs(upper_shadow - lower_shadow) < tick.tick_close * 0.005
            break
```

### Pattern Design Guidelines

**Doji Patterns** (Indecision):
- Very small body (open ≈ close)
- Equal or near-equal shadows
- Signals potential reversal

**Hammer/Hanging Man** (Reversal):
- Small body at top
- Long lower shadow (2x body)
- Minimal upper shadow

**Shooting Star** (Bearish Reversal):
- Small body at bottom
- Long upper shadow (2x body)
- Minimal lower shadow

**Engulfing Patterns** (Strong Reversal):
- Large body (3-5% range)
- Completely "engulfs" prior candle
- Strong directional signal

**Harami Patterns** (Trend Pause):
- Small body inside prior body
- Signals consolidation
- Potential reversal

### Validation Checklist

Before adding pattern to production:

- [ ] Pattern definition follows real candlestick anatomy
- [ ] OHLC relationship valid (High ≥ Open/Close, Low ≤ Open/Close)
- [ ] Pattern injected correctly (verify in logs)
- [ ] TickStockPL detects pattern (if applicable)
- [ ] Pattern documented in user guide
- [ ] Test case added to integration suite

---

## Customizing Sector Characteristics

### Edit Sector Definitions

File: `src/infrastructure/data_sources/synthetic/universe_loader.py`

```python
SECTOR_CHARACTERISTICS = {
    'Technology': {
        'volatility_factor': 1.5,           # 1.5x volatility
        'typical_price_range': (50, 300)    # $50-$300
    },
    # ... existing sectors

    # NEW SECTOR
    'Cryptocurrency': {
        'volatility_factor': 3.0,           # Very volatile
        'typical_price_range': (100, 50000) # Wide range
    }
}
```

### Sector Characteristics

**volatility_factor** (0.5 - 3.0):
- Applied on top of scenario multiplier
- Tech stocks: 1.5x (AAPL, NVDA)
- Utilities: 0.6x (stable)
- Crypto: 3.0x (very volatile)

**typical_price_range** (min, max):
- Used for baseline price generation
- Tech: $50-$300 (growth stocks)
- Utilities: $50-$100 (dividend stocks)
- Financial: $20-$150 (banks, ETFs)

### Update Sector Distribution

Edit `_populate_symbols_from_tickers()`:

```python
sectors = [
    ('Technology', 0.25),      # 25%
    ('Healthcare', 0.15),      # 15%
    # ... existing sectors
    ('Cryptocurrency', 0.05),  # 5% (NEW)
]
```

**Note**: Weights must sum to 1.0 or close to it.

### Add Symbols to Fallback Universe

Edit `_use_fallback_universe()`:

```python
fallback_symbols = {
    # ... existing symbols

    # Cryptocurrency
    'BTC': ('Cryptocurrency', 45000.0),
    'ETH': ('Cryptocurrency', 3000.0),
}
```

### Test Sector Volatility

```python
def test_crypto_sector_volatility():
    """Verify Cryptocurrency sector has 3.0x volatility."""
    loader = UniverseLoader()
    crypto_symbols = loader.get_symbols_by_sector('Cryptocurrency')

    assert len(crypto_symbols) > 0

    for symbol in crypto_symbols:
        info = loader.get_symbol_info(symbol)
        assert info.volatility_factor == 3.0
```

---

## Performance Optimization

### Current Performance

- **Tick generation**: <0.5ms per tick
- **Pattern injection**: ~33% overhead
- **Memory**: <10KB per provider
- **Initialization**: <100ms

### Optimization Guidelines

**1. Avoid Database Queries in Hot Path**

```python
# BAD - queries database per tick
def generate_tick_data(self, ticker):
    info = self.cache.get_symbol_info(ticker)  # DB query
    return self._generate_tick(info)

# GOOD - load once at initialization
def __init__(self):
    self.universe_loader = UniverseLoader()  # Loads once

def generate_tick_data(self, ticker):
    info = self.universe_loader.get_symbol_info(ticker)  # Hash lookup
    return self._generate_tick(info)
```

**2. Minimize Random Number Generation**

```python
# BAD - many random calls
variance = random.uniform(-0.01, 0.01)
volume_var = random.uniform(-0.2, 0.2)
spread_var = random.uniform(0.0, 0.001)

# GOOD - batch random generation
rand_values = [random.uniform(0, 1) for _ in range(3)]
variance = (rand_values[0] - 0.5) * 0.02
volume_var = (rand_values[1] - 0.5) * 0.4
spread_var = rand_values[2] * 0.001
```

**3. Cache Calculations**

```python
# BAD - recalculates every tick
def _get_time_multiplier(self):
    current_time = datetime.now()
    # ... complex time zone calculations

# GOOD - cache for 1 minute
@lru_cache(maxsize=1)
def _get_time_multiplier_cached(self, minute_key):
    # ... calculations
    return multipliers

def _get_time_multiplier(self):
    minute_key = datetime.now().minute
    return self._get_time_multiplier_cached(minute_key)
```

**4. Avoid String Operations in Hot Path**

```python
# BAD - string formatting per tick
logger.debug(f"Generated tick for {ticker} at {price}")

# GOOD - only log if debug enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Generated tick for {ticker} at {price}")
```

### Profiling

Use cProfile to identify bottlenecks:

```python
import cProfile
import pstats

def profile_tick_generation():
    provider = DataProviderFactory.get_provider(config)

    profiler = cProfile.Profile()
    profiler.enable()

    # Generate 1000 ticks
    for _ in range(1000):
        provider.generate_tick_data('AAPL')

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

profile_tick_generation()
```

Look for functions consuming >5% of total time.

---

## Testing Strategies

### Unit Tests

Test individual components in isolation:

```python
def test_universe_loader_initialization():
    """Test UniverseLoader initializes correctly."""
    loader = UniverseLoader('market_leaders:top_500')
    assert len(loader.tickers) > 0
    assert len(loader.get_sectors()) > 0

def test_sector_assignment():
    """Test sector assignment is deterministic."""
    loader = UniverseLoader()

    # Same ticker should always get same sector
    sector1 = loader.get_symbol_info('AAPL').sector
    sector2 = loader.get_symbol_info('AAPL').sector
    assert sector1 == sector2
```

### Integration Tests

Test complete flows:

```python
def test_end_to_end_tick_generation():
    """Test complete tick generation flow."""
    config = {
        'USE_SYNTHETIC_DATA': True,
        'SYNTHETIC_SCENARIO': 'normal',
        'SYNTHETIC_PATTERN_INJECTION': True
    }

    provider = DataProviderFactory.get_provider(config)
    tick = provider.generate_tick_data('AAPL')

    # Validate tick structure
    assert tick.ticker == 'AAPL'
    assert tick.price > 0
    assert tick.tick_high >= tick.tick_open
    assert tick.tick_low <= tick.tick_open
    assert tick.bid < tick.ask
```

### Statistical Tests

Test stochastic behavior over many samples:

```python
def test_pattern_injection_frequency():
    """Test pattern injection occurs at configured frequency."""
    provider = DataProviderFactory.get_provider({
        'USE_SYNTHETIC_DATA': True,
        'SYNTHETIC_PATTERN_INJECTION': True,
        'SYNTHETIC_PATTERN_FREQUENCY': 0.2
    })

    patterns_injected = 0
    total_ticks = 1000

    for _ in range(total_ticks):
        tick = provider.generate_tick_data('AAPL')
        if tick.pattern_injected:
            patterns_injected += 1

    # Expect 20% ± variance
    expected = total_ticks * 0.2
    variance = expected * 0.3  # Allow 30% variance

    assert expected - variance <= patterns_injected <= expected + variance
```

### Test Configuration vs Runtime Behavior

**ALWAYS test configuration correctness, not random outcomes:**

```python
# BAD - tests random price ranges (flaky)
def test_crash_volatility_bad():
    provider = get_provider({'SYNTHETIC_SCENARIO': 'crash'})
    ranges = [get_price_range(provider, 'AAPL') for _ in range(10)]
    avg_range = sum(ranges) / len(ranges)
    assert avg_range > 5.0  # FLAKY - may fail due to randomness

# GOOD - tests configuration (deterministic)
def test_crash_volatility_good():
    provider = get_provider({'SYNTHETIC_SCENARIO': 'crash'})
    assert provider.volatility_multiplier == 5.0
    assert provider.trend_bias == -0.8
```

### Mock External Dependencies

When testing provider, mock database calls:

```python
@patch('src.infrastructure.cache.cache_control.CacheControl')
def test_universe_loader_fallback(mock_cache):
    """Test fallback when database unavailable."""
    mock_cache.return_value.get_universe_tickers.return_value = []

    loader = UniverseLoader('nonexistent:universe')

    # Should fall back to hardcoded universe
    assert len(loader.tickers) == 29
    assert 'AAPL' in loader.tickers
```

---

## Code Quality Standards

### Follow Project Standards

From CLAUDE.md:

- **Files**: Max 500 lines per file
- **Functions**: Max 50 lines per function
- **Classes**: Max 500 lines per class
- **Line Length**: Max 100 characters
- **Complexity**: Cyclomatic complexity <10

### Naming Conventions

- **Variables/Functions**: `snake_case` (e.g., `generate_tick_data`)
- **Classes**: `PascalCase` (e.g., `SimulatedDataProvider`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `PATTERNS`)
- **Private**: `_underscore_prefix` (e.g., `_inject_pattern`)

### Documentation

Every function should have docstring:

```python
def generate_tick_data(self, ticker: str) -> TickData:
    """Generate realistic synthetic tick data.

    Args:
        ticker: Stock symbol (e.g., 'AAPL')

    Returns:
        TickData object with OHLCV, bid/ask, volume

    Raises:
        ValueError: If ticker not in universe
    """
```

### Type Hints

Use type hints for all public methods:

```python
from typing import List, Dict, Optional

def get_symbols_by_sector(self, sector: str) -> List[str]:
    """Get all symbols in a specific sector."""
    return [ticker for ticker, info in self.symbols.items()
            if info.sector == sector]
```

### Error Handling

Always fail fast with clear messages:

```python
# BAD - silent failure
def get_symbol_info(self, ticker):
    if ticker in self.symbols:
        return self.symbols[ticker]
    return None  # Caller doesn't know why

# GOOD - explicit failure
def get_symbol_info(self, ticker: str) -> SymbolInfo:
    if ticker not in self.symbols:
        raise ValueError(f"Symbol {ticker} not found in universe")
    return self.symbols[ticker]
```

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Trace Tick Generation

Add to `provider.py`:

```python
def generate_tick_data(self, ticker: str) -> TickData:
    logger.debug(f"Generating tick for {ticker}")

    # ... generation logic

    if pattern_data:
        logger.debug(f"Injected pattern: {pattern_data['name']}")

    logger.debug(f"Tick: O={tick_open:.2f} H={tick_high:.2f} "
                 f"L={tick_low:.2f} C={tick_close:.2f}")

    return tick_data
```

### Monitor Provider Statistics

```python
provider = DataProviderFactory.get_provider(config)

# Generate some ticks
for _ in range(100):
    provider.generate_tick_data('AAPL')

# Check statistics
stats = provider.get_statistics()
print(f"Ticks generated: {stats['ticks_generated']}")
print(f"Patterns injected: {stats['patterns_injected']}")
print(f"Pattern breakdown: {stats['pattern_counts']}")
print(f"Universe size: {stats['universe_size']}")
```

### Validate Tick Structure

```python
def validate_tick(tick: TickData):
    """Validate tick structure for debugging."""
    assert tick.tick_high >= tick.tick_open, "High must be >= Open"
    assert tick.tick_high >= tick.tick_close, "High must be >= Close"
    assert tick.tick_low <= tick.tick_open, "Low must be <= Open"
    assert tick.tick_low <= tick.tick_close, "Low must be <= Close"
    assert tick.bid < tick.ask, "Bid must be < Ask"
    assert tick.volume > 0, "Volume must be positive"
```

---

## Common Pitfalls

### 1. Testing Random Behavior

**Pitfall**: Testing actual price ranges or movement patterns

**Solution**: Test configuration values, not runtime randomness

```python
# WRONG
assert crash_price_range > normal_price_range

# RIGHT
assert provider.volatility_multiplier == 5.0
```

### 2. Modifying State in Tests

**Pitfall**: Tests modify shared provider instance

**Solution**: Use pytest fixtures with proper scope

```python
@pytest.fixture(scope="function")  # New instance per test
def provider(config):
    return DataProviderFactory.get_provider(config)
```

### 3. Hardcoding Configuration

**Pitfall**: Hardcoded values instead of using config

**Solution**: Always reference config_manager

```python
# WRONG
pattern_frequency = 0.1

# RIGHT
pattern_frequency = get_config()['SYNTHETIC_PATTERN_FREQUENCY']
```

### 4. Ignoring Time Zones

**Pitfall**: Time-of-day multipliers using local time instead of market time

**Solution**: Always use market time (ET) for calculations

```python
# WRONG
current_hour = datetime.now().hour

# RIGHT
import pytz
et_tz = pytz.timezone('America/New_York')
current_hour = datetime.now(et_tz).hour
```

### 5. Over-Engineering

**Pitfall**: Adding complex features "just in case"

**Solution**: Follow YAGNI (You Aren't Gonna Need It)

Only add features when explicitly needed for a use case.

---

## Extension Points

### 1. Custom Price Models

Current: Simple random walk with trend bias

**Extension**: Implement mean-reversion models:

```python
def _calculate_price_with_mean_reversion(self, ticker, current_price):
    """Calculate price with mean reversion to baseline."""
    baseline = self.universe_loader.get_symbol_info(ticker).baseline_price

    # Pull price toward baseline (mean reversion)
    mean_reversion_strength = 0.05
    price_deviation = current_price - baseline
    mean_reversion_adj = -price_deviation * mean_reversion_strength

    # Apply random walk
    random_adj = random.uniform(-0.01, 0.01) * current_price

    new_price = current_price + mean_reversion_adj + random_adj
    return new_price
```

### 2. Custom Volume Models

Current: Random variance with time-of-day multipliers

**Extension**: Implement price-volume correlation:

```python
def _calculate_volume_with_correlation(self, price_change_pct):
    """Calculate volume correlated with price movement."""
    base_volume = 100000

    # Higher volume on larger price moves
    volume_multiplier = 1.0 + abs(price_change_pct) * 10

    # Add randomness
    volume_variance = random.uniform(0.8, 1.2)

    return int(base_volume * volume_multiplier * volume_variance)
```

### 3. Event-Based Scenarios

Current: Static scenario parameters

**Extension**: Dynamic scenario transitions:

```python
class EventDrivenScenario:
    """Scenario that transitions based on events."""

    def __init__(self):
        self.state = 'normal'
        self.transitions = {
            'normal': {'trigger': self._check_volatility_spike, 'next': 'volatile'},
            'volatile': {'trigger': self._check_calm_down, 'next': 'normal'}
        }

    def update(self, tick_data):
        """Update scenario based on market data."""
        transition = self.transitions[self.state]
        if transition['trigger'](tick_data):
            self.state = transition['next']
            logger.info(f"Scenario transition: {self.state}")
```

### 4. Multi-Timeframe Aggregation

Current: Single tick generation

**Extension**: Generate ticks with historical context:

```python
class MultiTimeframeProvider(SimulatedDataProvider):
    """Provider that maintains historical bars."""

    def __init__(self, config):
        super().__init__(config)
        self.bars_1min = {}  # ticker -> list of 1-min bars
        self.bars_5min = {}  # ticker -> list of 5-min bars

    def generate_tick_data(self, ticker):
        tick = super().generate_tick_data(ticker)

        # Aggregate into bars
        self._update_bars(ticker, tick)

        return tick
```

---

## Contributing

### Pull Request Checklist

- [ ] Code follows project style guide (CLAUDE.md)
- [ ] All functions have docstrings
- [ ] Type hints added to public methods
- [ ] Unit tests added for new functionality
- [ ] Integration tests pass (`python -m pytest tests/integration/`)
- [ ] Performance benchmarks run (no degradation)
- [ ] Documentation updated (user guide and/or developer guide)
- [ ] No hardcoded credentials or secrets

### Code Review Focus Areas

1. **Correctness**: Does it work as intended?
2. **Performance**: Any bottlenecks introduced?
3. **Testing**: Adequate test coverage?
4. **Documentation**: Clear and complete?
5. **Style**: Follows project conventions?

---

## Resources

### Related Documentation

- **User Guide**: `docs/guides/synthetic_data_guide.md`
- **API Reference**: `docs/api/synthetic_data_api.md`
- **Architecture**: `docs/architecture/README.md`
- **Testing Guide**: `docs/guides/testing.md`

### Code Files

- **Provider**: `src/infrastructure/data_sources/synthetic/provider.py`
- **Universe Loader**: `src/infrastructure/data_sources/synthetic/universe_loader.py`
- **Factory**: `src/infrastructure/data_sources/factory.py`
- **Config Manager**: `src/core/services/config_manager.py`

### Tests

- **Integration Tests**: `tests/integration/test_sprint41_synthetic_integration.py`
- **Run Tests**: `python -m pytest tests/integration/ -v`

---

**Last Updated**: October 7, 2025 | **Sprint**: 41 Phase 5 | **Status**: Complete ✅
