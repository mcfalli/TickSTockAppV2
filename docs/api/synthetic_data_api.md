# Synthetic Data API Reference

**Sprint 41 Feature** | **Version**: 1.0 | **Last Updated**: October 7, 2025

---

## Overview

API documentation for the synthetic data generation system. This reference covers:

- `SimulatedDataProvider` - Main provider class
- `UniverseLoader` - Symbol universe management
- `SymbolInfo` - Symbol data structure
- `PatternDefinition` - Pattern structure

---

## SimulatedDataProvider

**Location**: `src/infrastructure/data_sources/synthetic/provider.py`

**Inherits**: `BaseDataProvider`

**Purpose**: Generate realistic synthetic market data with configurable scenarios, patterns, and universe.

### Constructor

```python
SimulatedDataProvider(config: dict)
```

**Parameters**:
- `config` (dict): Configuration dictionary with keys:
  - `USE_SYNTHETIC_DATA` (bool): Must be `True`
  - `SYNTHETIC_UNIVERSE` (str): Universe key (default: `'market_leaders:top_500'`)
  - `SYNTHETIC_SCENARIO` (str): Scenario name (default: `'normal'`)
  - `SYNTHETIC_PATTERN_INJECTION` (bool): Enable pattern injection (default: `True`)
  - `SYNTHETIC_PATTERN_FREQUENCY` (float): Pattern frequency 0.0-1.0 (default: `0.1`)
  - `SYNTHETIC_PATTERN_TYPES` (str): Comma-separated pattern names (default: all)
  - `SYNTHETIC_ACTIVITY_LEVEL` (str): `'low'`, `'medium'`, `'high'` (default: `'medium'`)

**Raises**:
- `ValueError`: If `USE_SYNTHETIC_DATA` is not `True`
- `KeyError`: If required config keys missing

**Example**:
```python
from src.core.services.config_manager import get_config
from src.infrastructure.data_sources.synthetic.provider import SimulatedDataProvider

config = get_config()
provider = SimulatedDataProvider(config)
```

---

### Methods

#### generate_tick_data()

```python
generate_tick_data(ticker: str) -> TickData
```

Generate realistic synthetic tick data for a ticker.

**Parameters**:
- `ticker` (str): Stock symbol (e.g., `'AAPL'`)

**Returns**:
- `TickData`: Tick object with:
  - `ticker` (str): Symbol
  - `price` (float): Current price
  - `volume` (int): Tick volume
  - `timestamp` (datetime): Tick timestamp
  - `source` (str): `'simulated'`
  - `tick_open` (float): Bar open price
  - `tick_high` (float): Bar high price
  - `tick_low` (float): Bar low price
  - `tick_close` (float): Bar close price
  - `bid` (float): Bid price
  - `ask` (float): Ask price
  - `pattern_injected` (str|None): Pattern name if injected

**Raises**:
- `ValueError`: If ticker not in universe

**Example**:
```python
tick = provider.generate_tick_data('AAPL')
print(f"{tick.ticker}: ${tick.price:.2f} Vol={tick.volume}")
# Output: AAPL: $175.23 Vol=125000
```

**Rate Limiting**: Automatically enforces 0.2s minimum interval between price updates for same ticker.

---

#### is_available()

```python
is_available() -> bool
```

Check if provider is available and ready.

**Returns**:
- `bool`: Always `True` for synthetic provider

**Example**:
```python
if provider.is_available():
    print("Provider ready")
```

---

#### get_ticker_price()

```python
get_ticker_price(ticker: str, use_cache: bool = True) -> Optional[float]
```

Get current price for a ticker.

**Parameters**:
- `ticker` (str): Stock symbol
- `use_cache` (bool): Use cached price if available (default: `True`)

**Returns**:
- `float`: Current price
- `None`: If ticker not in universe

**Example**:
```python
price = provider.get_ticker_price('AAPL')
print(f"AAPL: ${price:.2f}")
```

---

#### get_ticker_details()

```python
get_ticker_details(ticker: str) -> dict
```

Get detailed information about a ticker.

**Parameters**:
- `ticker` (str): Stock symbol

**Returns**:
- `dict`: Ticker details:
  ```python
  {
      'ticker': str,
      'price': float,
      'volume': int,
      'bid': float,
      'ask': float,
      'spread': float,
      'sector': str,
      'source': 'simulated'
  }
  ```

**Raises**:
- `ValueError`: If ticker not in universe

**Example**:
```python
details = provider.get_ticker_details('AAPL')
print(f"{details['ticker']} ({details['sector']})")
print(f"Price: ${details['price']:.2f}")
print(f"Spread: {details['spread']:.4f}")
```

---

#### get_statistics()

```python
get_statistics() -> dict
```

Get provider statistics.

**Returns**:
- `dict`: Statistics:
  ```python
  {
      'ticks_generated': int,        # Total ticks generated
      'patterns_injected': int,      # Total patterns injected
      'scenario': str,               # Current scenario name
      'volatility_multiplier': float,# Scenario volatility
      'volume_multiplier': float,    # Scenario volume
      'trend_bias': float,           # Scenario trend bias
      'universe_size': int,          # Number of symbols
      'pattern_counts': {            # Counts by pattern type
          'Doji': int,
          'Hammer': int,
          # ... other patterns
      }
  }
  ```

**Example**:
```python
stats = provider.get_statistics()
print(f"Generated {stats['ticks_generated']} ticks")
print(f"Injected {stats['patterns_injected']} patterns")
print(f"Pattern breakdown: {stats['pattern_counts']}")
```

---

### Properties

#### scenario

```python
@property
scenario -> str
```

Current scenario name.

**Example**:
```python
print(f"Current scenario: {provider.scenario}")
# Output: Current scenario: normal
```

---

#### volatility_multiplier

```python
@property
volatility_multiplier -> float
```

Current volatility multiplier from scenario.

**Range**: 0.5 - 5.0

**Example**:
```python
print(f"Volatility: {provider.volatility_multiplier}x")
# Output: Volatility: 1.0x (normal)
# Output: Volatility: 5.0x (crash)
```

---

#### volume_multiplier

```python
@property
volume_multiplier -> float
```

Current volume multiplier from scenario.

**Range**: 0.3 - 5.0

---

#### trend_bias

```python
@property
trend_bias -> float
```

Current trend bias from scenario.

**Range**: -1.0 (strong down) to +1.0 (strong up)

**Example**:
```python
if provider.trend_bias > 0:
    print("Bullish scenario")
elif provider.trend_bias < 0:
    print("Bearish scenario")
else:
    print("Neutral scenario")
```

---

#### pattern_injection

```python
@property
pattern_injection -> bool
```

Whether pattern injection is enabled.

---

#### pattern_frequency

```python
@property
pattern_frequency -> float
```

Pattern injection frequency (0.0 - 1.0).

---

#### ticks_generated

```python
@property
ticks_generated -> int
```

Total number of ticks generated since initialization.

---

#### patterns_injected

```python
@property
patterns_injected -> int
```

Total number of patterns injected since initialization.

---

## UniverseLoader

**Location**: `src/infrastructure/data_sources/synthetic/universe_loader.py`

**Purpose**: Load and manage symbol universe data with sector characteristics.

### Constructor

```python
UniverseLoader(universe_key: str = 'market_leaders:top_500')
```

**Parameters**:
- `universe_key` (str): Universe key from cache_entries table (default: `'market_leaders:top_500'`)

**Behavior**:
1. Attempts to load universe from database via `CacheControl`
2. If not found or error, falls back to 29-symbol hardcoded universe
3. Assigns sectors and volatility factors to all symbols

**Example**:
```python
from src.infrastructure.data_sources.synthetic.universe_loader import UniverseLoader

loader = UniverseLoader('market_leaders:top_500')
print(f"Loaded {len(loader.tickers)} symbols")
```

---

### Methods

#### get_symbol_info()

```python
get_symbol_info(ticker: str) -> Optional[SymbolInfo]
```

Get detailed information about a symbol.

**Parameters**:
- `ticker` (str): Stock symbol (case-insensitive)

**Returns**:
- `SymbolInfo`: Symbol information object (see below)
- `None`: If symbol not in universe

**Example**:
```python
info = loader.get_symbol_info('AAPL')
print(f"{info.ticker}: {info.sector}")
print(f"Baseline: ${info.baseline_price:.2f}")
print(f"Volatility: {info.volatility_factor}x")
```

---

#### get_random_symbols()

```python
get_random_symbols(count: int) -> List[str]
```

Get random symbols from universe.

**Parameters**:
- `count` (int): Number of symbols to return

**Returns**:
- `List[str]`: List of random ticker symbols

**Behavior**: If `count >= universe_size`, returns all symbols.

**Example**:
```python
# Get 5 random symbols
symbols = loader.get_random_symbols(5)
print(symbols)
# Output: ['AAPL', 'NVDA', 'JPM', 'UNH', 'AMZN']
```

---

#### get_all_tickers()

```python
get_all_tickers() -> List[str]
```

Get all tickers in universe.

**Returns**:
- `List[str]`: All ticker symbols

**Example**:
```python
all_symbols = loader.get_all_tickers()
print(f"Universe contains {len(all_symbols)} symbols")
```

---

#### get_sectors()

```python
get_sectors() -> Set[str]
```

Get all unique sectors in universe.

**Returns**:
- `Set[str]`: Set of sector names

**Example**:
```python
sectors = loader.get_sectors()
print(f"Sectors: {', '.join(sorted(sectors))}")
# Output: Sectors: Communication, Consumer, Energy, Financial, Healthcare, Technology
```

---

#### get_symbols_by_sector()

```python
get_symbols_by_sector(sector: str) -> List[str]
```

Get all symbols in a specific sector.

**Parameters**:
- `sector` (str): Sector name (case-sensitive)

**Returns**:
- `List[str]`: List of symbols in sector

**Example**:
```python
tech_symbols = loader.get_symbols_by_sector('Technology')
print(f"Technology stocks: {', '.join(tech_symbols)}")
# Output: Technology stocks: AAPL, MSFT, GOOGL, NVDA, META, TSLA, AMD, INTC, QQQ
```

---

### Properties

#### tickers

```python
@property
tickers -> List[str]
```

List of all ticker symbols in universe.

---

#### symbols

```python
@property
symbols -> Dict[str, SymbolInfo]
```

Dictionary mapping ticker to SymbolInfo.

---

#### universe_key

```python
@property
universe_key -> str
```

Universe key used to load symbols.

---

## SymbolInfo

**Location**: `src/infrastructure/data_sources/synthetic/universe_loader.py`

**Type**: `@dataclass`

**Purpose**: Store symbol-specific information for synthetic data generation.

### Fields

```python
@dataclass
class SymbolInfo:
    ticker: str              # Stock symbol (e.g., 'AAPL')
    sector: str              # Sector name (e.g., 'Technology')
    baseline_price: float    # Baseline price for generation
    volatility_factor: float # Sector-based volatility multiplier
```

### Example

```python
info = SymbolInfo(
    ticker='AAPL',
    sector='Technology',
    baseline_price=175.0,
    volatility_factor=1.5
)

print(f"{info.ticker} ({info.sector})")
print(f"Price: ${info.baseline_price:.2f}")
print(f"Volatility: {info.volatility_factor}x")
```

---

## PatternDefinition

**Location**: `src/infrastructure/data_sources/synthetic/provider.py`

**Type**: `@dataclass`

**Purpose**: Define candlestick pattern OHLC structure.

### Fields

```python
@dataclass
class PatternDefinition:
    name: str        # Pattern name (e.g., 'Doji')
    open_pct: float  # Open price as % of base (e.g., 1.0 = 100%)
    high_pct: float  # High price as % of base
    low_pct: float   # Low price as % of base
    close_pct: float # Close price as % of base
```

### Example

```python
doji = PatternDefinition(
    name='Doji',
    open_pct=1.0,      # Open = Close (base price)
    high_pct=1.005,    # High 0.5% above
    low_pct=0.995,     # Low 0.5% below
    close_pct=1.0      # Close = Open
)
```

### Available Patterns

```python
PATTERNS = {
    'Doji': PatternDefinition(
        name='Doji',
        open_pct=1.0,
        high_pct=1.005,
        low_pct=0.995,
        close_pct=1.0
    ),
    'Hammer': PatternDefinition(
        name='Hammer',
        open_pct=0.998,
        high_pct=1.001,
        low_pct=0.98,
        close_pct=1.0
    ),
    'ShootingStar': PatternDefinition(
        name='ShootingStar',
        open_pct=1.0,
        high_pct=1.02,
        low_pct=0.999,
        close_pct=0.998
    ),
    'BullishEngulfing': PatternDefinition(
        name='BullishEngulfing',
        open_pct=0.97,
        high_pct=1.03,
        low_pct=0.965,
        close_pct=1.025
    ),
    'BearishEngulfing': PatternDefinition(
        name='BearishEngulfing',
        open_pct=1.03,
        high_pct=1.035,
        low_pct=0.97,
        close_pct=0.975
    ),
    'Harami': PatternDefinition(
        name='Harami',
        open_pct=0.995,
        high_pct=1.005,
        low_pct=0.993,
        close_pct=1.003
    )
}
```

---

## Sector Characteristics

**Location**: `src/infrastructure/data_sources/synthetic/universe_loader.py`

**Constant**: `SECTOR_CHARACTERISTICS`

### Structure

```python
SECTOR_CHARACTERISTICS = {
    'Technology': {
        'volatility_factor': 1.5,
        'typical_price_range': (50, 300)
    },
    'Healthcare': {
        'volatility_factor': 1.2,
        'typical_price_range': (30, 200)
    },
    'Financial': {
        'volatility_factor': 1.0,
        'typical_price_range': (20, 150)
    },
    'Consumer': {
        'volatility_factor': 0.9,
        'typical_price_range': (25, 180)
    },
    'Industrial': {
        'volatility_factor': 0.8,
        'typical_price_range': (40, 160)
    },
    'Energy': {
        'volatility_factor': 1.3,
        'typical_price_range': (30, 120)
    },
    'Utilities': {
        'volatility_factor': 0.6,
        'typical_price_range': (50, 100)
    },
    'Materials': {
        'volatility_factor': 1.1,
        'typical_price_range': (35, 140)
    },
    'Communication': {
        'volatility_factor': 1.2,
        'typical_price_range': (40, 200)
    },
    'RealEstate': {
        'volatility_factor': 0.7,
        'typical_price_range': (30, 120)
    },
    'Unknown': {
        'volatility_factor': 1.0,
        'typical_price_range': (50, 150)
    }
}
```

---

## Scenario Definitions

**Location**: `src/infrastructure/data_sources/synthetic/provider.py`

**Method**: `_load_scenario()`

### Structure

```python
scenarios = {
    'normal': {
        'volatility_multiplier': 1.0,
        'volume_multiplier': 1.0,
        'trend_bias': 0.0,
        'spread_pct': 0.001
    },
    'volatile': {
        'volatility_multiplier': 3.0,
        'volume_multiplier': 2.0,
        'trend_bias': 0.0,
        'spread_pct': 0.002
    },
    'crash': {
        'volatility_multiplier': 5.0,
        'volume_multiplier': 4.0,
        'trend_bias': -0.8,
        'spread_pct': 0.005
    },
    'rally': {
        'volatility_multiplier': 2.0,
        'volume_multiplier': 2.5,
        'trend_bias': 0.8,
        'spread_pct': 0.0015
    },
    'opening_bell': {
        'volatility_multiplier': 4.0,
        'volume_multiplier': 5.0,
        'trend_bias': 0.0,
        'spread_pct': 0.003
    }
}
```

---

## Activity Levels

**Location**: `src/infrastructure/data_sources/synthetic/provider.py`

**Method**: `_get_activity_multiplier()`

### Levels

```python
activity_levels = {
    'low': {
        'volatility': 0.05,  # 5% variance
        'volume': 50000      # Base volume
    },
    'medium': {
        'volatility': 0.10,  # 10% variance (default)
        'volume': 100000
    },
    'high': {
        'volatility': 0.20,  # 20% variance
        'volume': 200000
    }
}
```

---

## Time-of-Day Multipliers

**Location**: `src/infrastructure/data_sources/synthetic/provider.py`

**Method**: `_get_time_of_day_multiplier()`

### Market Hours (ET)

```python
# Opening Bell (9:30-10:00 AM)
{
    'volatility': 2.0,
    'volume': 3.0
}

# Lunch Lull (12:00-1:00 PM)
{
    'volatility': 0.7,
    'volume': 0.5
}

# Closing Hour (3:00-4:00 PM)
{
    'volatility': 1.5,
    'volume': 2.0
}

# Normal Hours (all other times)
{
    'volatility': 1.0,
    'volume': 1.0
}
```

---

## Usage Examples

### Example 1: Basic Tick Generation

```python
from src.core.services.config_manager import get_config
from src.infrastructure.data_sources.factory import DataProviderFactory

# Get provider
config = get_config()
provider = DataProviderFactory.get_provider(config)

# Generate tick
tick = provider.generate_tick_data('AAPL')

# Display tick
print(f"Ticker: {tick.ticker}")
print(f"Price: ${tick.price:.2f}")
print(f"OHLC: O=${tick.tick_open:.2f} H=${tick.tick_high:.2f} "
      f"L=${tick.tick_low:.2f} C=${tick.tick_close:.2f}")
print(f"Bid/Ask: ${tick.bid:.2f}/${tick.ask:.2f}")
print(f"Volume: {tick.volume:,}")
if tick.pattern_injected:
    print(f"Pattern: {tick.pattern_injected}")
```

### Example 2: Universe Exploration

```python
from src.infrastructure.data_sources.synthetic.universe_loader import UniverseLoader

loader = UniverseLoader()

# Get all sectors
sectors = loader.get_sectors()
print(f"Available sectors: {', '.join(sorted(sectors))}")

# Get symbols by sector
for sector in sorted(sectors):
    symbols = loader.get_symbols_by_sector(sector)
    print(f"\n{sector} ({len(symbols)} symbols):")
    for symbol in symbols[:5]:  # First 5
        info = loader.get_symbol_info(symbol)
        print(f"  {info.ticker}: ${info.baseline_price:.2f} "
              f"(vol={info.volatility_factor}x)")
```

### Example 3: Scenario Comparison

```python
scenarios = ['normal', 'volatile', 'crash', 'rally', 'opening_bell']

for scenario in scenarios:
    config = get_config()
    config['SYNTHETIC_SCENARIO'] = scenario
    provider = DataProviderFactory.get_provider(config)

    print(f"\n{scenario.upper()}:")
    print(f"  Volatility: {provider.volatility_multiplier}x")
    print(f"  Volume: {provider.volume_multiplier}x")
    print(f"  Trend Bias: {provider.trend_bias:+.1f}")
```

### Example 4: Pattern Injection Monitoring

```python
from src.infrastructure.data_sources.factory import DataProviderFactory
from src.core.services.config_manager import get_config

config = get_config()
config['SYNTHETIC_PATTERN_INJECTION'] = True
config['SYNTHETIC_PATTERN_FREQUENCY'] = 0.2

provider = DataProviderFactory.get_provider(config)

# Generate 100 ticks
patterns_found = []
for i in range(100):
    tick = provider.generate_tick_data('AAPL')
    if tick.pattern_injected:
        patterns_found.append(tick.pattern_injected)

# Display results
stats = provider.get_statistics()
print(f"Ticks generated: {stats['ticks_generated']}")
print(f"Patterns injected: {stats['patterns_injected']}")
print(f"Injection rate: {stats['patterns_injected']/stats['ticks_generated']*100:.1f}%")
print(f"\nPattern breakdown:")
for pattern, count in stats['pattern_counts'].items():
    if count > 0:
        print(f"  {pattern}: {count}")
```

---

## Error Handling

### Common Exceptions

**ValueError: Symbol not in universe**
```python
try:
    tick = provider.generate_tick_data('INVALID')
except ValueError as e:
    print(f"Error: {e}")
    # Handle: Use symbol from universe
    valid_symbols = provider.universe_loader.get_all_tickers()
    tick = provider.generate_tick_data(valid_symbols[0])
```

**KeyError: Configuration key missing**
```python
try:
    provider = SimulatedDataProvider({})  # Missing config
except KeyError as e:
    print(f"Missing config key: {e}")
    # Handle: Use defaults
    config = get_config()
    provider = SimulatedDataProvider(config)
```

---

## Performance Considerations

### Tick Generation

- **Time**: <0.5ms per tick (target <1ms)
- **Memory**: Negligible per tick
- **Rate Limit**: 0.2s minimum between updates for same ticker

### Pattern Injection

- **Overhead**: ~33% additional time when enabled
- **Frequency**: 0.1 (10%) recommended for production
- **Testing**: 0.2 (20%) for visibility

### Universe Loading

- **Initialization**: <100ms (database + building)
- **Memory**: ~5KB for 29-symbol fallback
- **Lookup**: O(1) hash lookup

---

## Thread Safety

**SimulatedDataProvider**: Thread-safe for read operations

**Not thread-safe**: Shared state updates (statistics counters)

**Recommendation**: Use separate provider instances per thread or protect with locks:

```python
import threading

lock = threading.Lock()

def generate_tick_thread_safe(provider, ticker):
    with lock:
        return provider.generate_tick_data(ticker)
```

---

## Related Documentation

- **User Guide**: `docs/guides/synthetic_data_guide.md`
- **Developer Guide**: `docs/guides/synthetic_data_developer_guide.md`
- **Architecture**: `docs/architecture/README.md`

---

**Last Updated**: October 7, 2025 | **Sprint**: 41 Phase 5 | **Status**: Complete ✅
