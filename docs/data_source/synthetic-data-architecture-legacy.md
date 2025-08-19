# Synthetic Data Architecture Documentation

Last edited: August 19, 2025 at 3:45 PM
Sprint: 102 - Synthetic Data Documentation

## Overview

The TickStock Synthetic Data Architecture provides comprehensive market data simulation for testing, development, and offline analysis. The system generates realistic market events, tick data, and market behavior patterns while maintaining consistency with real market data structures and timing.

## Architecture Components

### Core Components Hierarchy

```
Synthetic Data Architecture
├── SimulatedDataProvider (Interface Implementation)
├── SyntheticDataGenerator (Event Generation)
├── SyntheticDataLoader (Universe Management)
├── SyntheticDataAdapter (RealTimeDataAdapter Integration)
└── CacheControl (Universe Data Source)
```

## SimulatedDataProvider Class Implementation

### DataProvider Interface Compliance

```python
class SimulatedDataProvider(DataProvider):
    """Provider that generates simulated stock market data with comprehensive tracing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.market_timezone = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        self.price_seeds = {}
        self.sectors = ["Technology", "Healthcare", "Financial", "Consumer", "Industrial", "Energy"]
```

**Interface Implementation Features:**
- **DataProvider compliance**: Implements standard DataProvider interface
- **Configuration-driven**: All behavior controlled via config parameters
- **Market timezone awareness**: US/Eastern timezone for market session detection
- **Sector categorization**: Realistic sector assignments for generated tickers
- **Comprehensive tracing**: Integrated monitoring and debugging support

### Price Generation System

#### Deterministic Price Seeding
```python
def get_ticker_price(self, ticker: str) -> float:
    if ticker not in self.price_seeds:
        self.price_seeds[ticker] = random.randint(1, 1000)
    base_price = 100 + (hash(ticker) % 100)
    time_factor = int(current_time / 5)
    random.seed(self.price_seeds[ticker] + time_factor)
```

**Price Generation Features:**
- **Deterministic seeding**: Consistent prices for same ticker across runs
- **Time-based variation**: Price changes based on time factor (5-second intervals)
- **Hash-based base pricing**: Ticker hash determines price range (100-200)
- **Configurable variance**: Activity level controls price volatility
- **Rate limiting**: Maximum 1 price update per 0.2 seconds per ticker

#### Activity Level Configuration
```python
activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
variance_map = {'low': 5, 'medium': 10, 'high': 20, 'opening_bell': 50}
variance = variance_map.get(activity_level, 10)

price = base_price + random.uniform(-variance, variance) + (current_time % 20) / 10
```

**Activity Level Mapping:**
- **'low'**: ±$5 variance, minimal market movement
- **'medium'**: ±$10 variance, normal market activity
- **'high'**: ±$20 variance, volatile market conditions
- **'opening_bell'**: ±$50 variance, extreme opening volatility

### Market Status Detection Logic

#### Real-Time Market Session Detection
```python
def get_market_status(self) -> str:
    utc_now = datetime.now(pytz.utc)
    eastern_now = utc_now.astimezone(self.market_timezone)
    market_status = "CLOSED"
    
    if eastern_now.weekday() < 5:  # Monday-Friday
        if eastern_now.hour == 9 and eastern_now.minute >= 30 or eastern_now.hour > 9 and eastern_now.hour < 16:
            market_status = "REGULAR"
        elif (eastern_now.hour >= 4 and eastern_now.hour < 9) or (eastern_now.hour == 9 and eastern_now.minute < 30):
            market_status = "PRE"
        elif eastern_now.hour >= 16 and eastern_now.hour < 20:
            market_status = "AFTER"
    return market_status
```

**Market Status Detection:**
- **REGULAR**: 9:30 AM - 4:00 PM ET (Monday-Friday)
- **PRE**: 4:00 AM - 9:30 AM ET (Monday-Friday)  
- **AFTER**: 4:00 PM - 8:00 PM ET (Monday-Friday)
- **CLOSED**: Weekends and outside extended hours
- **Timezone handling**: Accurate UTC to Eastern conversion

### TickData Object Creation Process

#### Comprehensive TickData Generation
```python
def generate_tick_data(self, ticker: str) -> TickData:
    current_price = self.get_ticker_price(ticker)
    current_time = time.time()
    
    # Generate realistic tick variations
    tick_variance = 0.001  # 0.1% variance for tick data
    tick_high = round(current_price * (1 + random.uniform(0, tick_variance)), 2)
    tick_low = round(current_price * (1 - random.uniform(0, tick_variance)), 2)
    tick_open = round(current_price * (1 + random.uniform(-tick_variance/2, tick_variance/2)), 2)
    
    tick = TickData(
        ticker=ticker,
        price=current_price,
        volume=tick_volume,
        timestamp=current_time,
        source='simulated',
        event_type='A',  # Aggregate
        market_status=self.get_market_status(),
        bid=round(current_price * 0.999, 2),
        ask=round(current_price * 1.001, 2),
        tick_open=tick_open,
        tick_high=tick_high,
        tick_low=tick_low,
        tick_close=current_price,
        tick_volume=tick_volume,
        tick_vwap=tick_vwap,
        vwap=tick_vwap,
        tick_start_timestamp=current_time - 1,
        tick_end_timestamp=current_time
    )
```

**TickData Population Features:**
- **OHLC generation**: Realistic open, high, low, close prices with 0.1% variance
- **Volume scaling**: Activity-based volume generation (1K-1M shares)
- **Bid/ask spread**: 0.1% spread simulation (0.999x - 1.001x current price)
- **VWAP calculation**: Volume-weighted average price with 0.2% variance
- **Timing fields**: Start/end timestamps with 1-second windows
- **Market status integration**: Real-time market session detection
- **Type consistency**: All fields properly typed for downstream processing

#### Volume Generation by Activity Level
```python
activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
volume_map = {
    'low': (1000, 10000), 
    'medium': (10000, 100000), 
    'high': (100000, 500000), 
    'opening_bell': (500000, 1000000)
}
volume_range = volume_map.get(activity_level, (10000, 100000))
tick_volume = random.randint(*volume_range)
```

## SyntheticDataGenerator Class Implementation

### Event Generation Engine

#### Universe-Based Ticker Management
```python
def __init__(self, config):
    universe = config.get('SIMULATOR_UNIVERSE', 'market_leaders:top_50')
    
    self.cache_control = CacheControl()
    self.cache_control.initialize()
    
    self.data_loader = SyntheticDataLoader(
        universe=universe,
        cache_control=self.cache_control
    )
    
    self.tickers = self.data_loader.get_all_tickers()
```

**Universe Management Features:**
- **Configurable universes**: Support for different ticker sets (market_leaders:top_50, etc.)
- **CacheControl integration**: Leverages existing universe data from database
- **Fallback handling**: Emergency ticker list if universe loading fails
- **Dynamic loading**: Universe can be switched at runtime
- **Baseline pricing**: Each ticker has realistic baseline price from historical data

### Event Generation Algorithm

#### Activity-Based Event Distribution
```python
def generate_events(self, count=1, market_status="REGULAR", activity_level="medium"):
    events = {'highs': [], 'lows': []}
    
    # Determine realistic activity based on market conditions
    if activity_level == "low":
        active_pct = 0.05  # 5% of tickers active per second
        variance = 0.05
    elif activity_level == "medium":
        active_pct = 0.10  # 10% of tickers active per second
        variance = 0.1
    elif activity_level == "high":
        active_pct = 0.20  # 20% of tickers active per second
        variance = 0.15
    else:  # opening bell
        active_pct = 0.40  # 40% of tickers active in opening minute
        variance = 0.2
    
    active_tickers_count = max(1, int(len(self.tickers) * active_pct))
    active_tickers = random.sample(self.tickers, min(active_tickers_count, len(self.tickers)))
```

**Event Distribution Strategy:**
- **Percentage-based activity**: Control how many tickers are active per time period
- **Realistic market simulation**: Activity levels match real market patterns
- **Random ticker selection**: Different tickers active each time period
- **Special ticker inclusion**: Always include high-profile tickers (TSLA, NVDA) for consistency
- **Variance scaling**: Price movement variance scales with activity level

#### Event Type Generation
```python
for ticker in active_tickers:
    current_price = self.stock_prices.get(ticker)
    is_high = random.choice([True, False])
    
    if is_high:
        step = random.uniform(0, variance) * current_price
        new_price = max(1.0, current_price + step)
        event = self._create_tick_data(ticker, new_price, market_status, current_time, True)
        events['highs'].append(event)
    else:
        step = -random.uniform(0, variance) * current_price
        new_price = max(1.0, current_price + step)
        event = self._create_tick_data(ticker, new_price, market_status, current_time, False)
        events['lows'].append(event)
    
    self.stock_prices[ticker] = new_price
```

**Event Generation Features:**
- **Binary event types**: High and low events with equal probability
- **Price continuity**: Prices evolve from previous values, not reset each time
- **Minimum price protection**: Prices cannot go below $1.00
- **State persistence**: Price changes are stored and carried forward
- **TickData creation**: Each event produces a complete TickData object

### TickData Factory Method Integration

#### Synthetic TickData Creation
```python
def _create_tick_data(self, ticker, price, market_status, current_time, is_up):
    from src.core.domain.market.tick import TickData
    
    baseline = self.data_loader.get_ticker_baseline(ticker)
    
    # Use the new from_synthetic factory method
    tick = TickData.from_synthetic(
        ticker=ticker,
        price=price,
        baseline=baseline,
        market_status=market_status,
        current_time=current_time,
        is_up=is_up
    )
```

**Factory Method Benefits:**
- **Centralized creation**: Consistent TickData object creation
- **Baseline integration**: Uses real ticker baseline data for realistic context
- **Simplified parameters**: Factory method handles complex field population
- **Type safety**: Ensures all required fields are populated correctly
- **Baseline context**: Historical context informs realistic value ranges

### Performance Monitoring and Tracing

#### Comprehensive Tracing Integration
```python
# Generator initialization tracing
if tracer.should_trace('SYSTEM'):
    tracer.trace(
        ticker='SYSTEM',
        component='SyntheticDataGenerator',
        action='initialized',
        data={
            'input_count': 0,
            'output_count': 0,
            'duration_ms': 0,
            'details': {
                'universe': universe,
                'ticker_count': len(self.tickers),
                'load_method': 'cache'
            }
        }
    )

# Individual event generation tracing
if tracer.should_trace(ticker):
    tracer.trace(
        ticker=ticker,
        component='SyntheticDataGenerator',
        action='event_generated',
        data={
            'input_count': 1,
            'output_count': 1,
            'duration_ms': 0,
            'details': {
                'event_type': 'high' if is_high else 'low',
                'current_price': current_price,
                'activity_level': activity_level
            }
        }
    )
```

**Tracing Features:**
- **Component-level tracing**: Track initialization, events, and batch operations
- **Selective tracing**: Only trace specific tickers to reduce overhead
- **Performance metrics**: Duration and throughput tracking
- **Detailed context**: Activity levels, prices, and event types captured
- **System-level overview**: Aggregate statistics for batch operations

## SyntheticDataLoader Integration

### Universe Management and CacheControl Integration

The SyntheticDataLoader provides universe management capabilities:

```python
self.data_loader = SyntheticDataLoader(
    universe=universe,
    cache_control=self.cache_control
)

self.tickers = self.data_loader.get_all_tickers()
```

**Universe Features:**
- **Database-backed**: Leverages existing CacheControl and database infrastructure  
- **Multiple universes**: Support for different ticker sets (market_leaders, tech_focus, etc.)
- **Baseline data**: Historical context for realistic price ranges
- **Sector information**: Proper sector classification for generated tickers
- **Fallback support**: Emergency ticker lists if database unavailable

## SyntheticDataAdapter Integration with RealTimeDataAdapter

### Adapter Inheritance Pattern

```python
class SyntheticDataAdapter(RealTimeDataAdapter):
    def __init__(self, config, tick_callback, status_callback):
        super().__init__(config, tick_callback, status_callback)
        self.generator = SyntheticDataGenerator(config)
        self.connected = False
```

**Integration Features:**
- **Base class inheritance**: Reuses RealTimeDataAdapter callback infrastructure
- **Generator composition**: Contains SyntheticDataGenerator for event production
- **Independent state**: Maintains own connection state separate from WebSocket
- **Configuration sharing**: Same config object used across components

### Event Generation Loop

#### Continuous Event Simulation
```python
def _simulate_events(self):
    rate = self.config.get('SYNTHETIC_DATA_RATE', 0.5)
    activity_level = self.config.get('SYNTHETIC_ACTIVITY_LEVEL', 'medium')
    update_interval = self.config.get('UPDATE_INTERVAL', 0.5)
    
    while self.connected:
        events = self.generator.generate_events(
            count=max(1, int(rate * len(self.generator.tickers))),
            activity_level=activity_level
        )
        
        for event in events["highs"] + events["lows"]:
            self.tick_callback(event)  # event is now a TickData object
        time.sleep(update_interval)
```

**Simulation Loop Features:**
- **Rate-based generation**: Event count scales with configured rate and ticker universe size
- **Activity level control**: Different market conditions simulated
- **Update interval timing**: Configurable frequency (default 0.5 seconds)
- **Event categorization**: Separate handling of high and low events
- **Type consistency**: All events are TickData objects matching WebSocket output
- **Background execution**: Daemon thread doesn't block application shutdown

## Configuration System Integration

### Configuration Parameters

```python
# Synthetic data generation control
SYNTHETIC_DATA_RATE: float = 0.5           # Events per ticker per update
SYNTHETIC_ACTIVITY_LEVEL: str = 'medium'   # low, medium, high, opening_bell
UPDATE_INTERVAL: float = 0.5               # Seconds between event batches
SIMULATOR_UNIVERSE: str = 'market_leaders:top_50'  # Universe selection
MARKET_TIMEZONE: str = 'US/Eastern'        # Market timezone for session detection

# Tracing and monitoring
ENABLE_TRACING: bool = True                # Enable comprehensive tracing
LOG_SYNTHETIC_EVENTS: bool = False         # Log individual synthetic events
```

**Configuration Categories:**
- **Generation control**: Rate, activity level, timing parameters
- **Universe selection**: Which set of tickers to simulate
- **Market timing**: Timezone and session detection parameters  
- **Debugging**: Tracing and logging control flags

### Configuration-Driven Behavior

#### Activity Level Impact
- **Event frequency**: Low (5%) to Opening Bell (40%) ticker activation per period
- **Price variance**: $5 (low) to $50 (opening_bell) maximum price movement
- **Volume ranges**: 1K-10K (low) to 500K-1M (opening_bell) share volumes
- **Market realism**: Activity levels match real market conditions

#### Universe Selection Impact
- **Ticker count**: Different universes provide different ticker counts
- **Sector distribution**: Universe affects sector representation
- **Price baselines**: Historical data provides realistic starting prices
- **Market cap representation**: Different universes represent different market segments

## DataProviderFactory Integration and Provider Selection Priority

### Factory Pattern Compatibility

The synthetic data architecture integrates seamlessly with the DataProviderFactory:

```python
# Factory selection priority (from factory.py)
providers = []
if config.get('USE_SYNTHETIC_DATA'):
    providers.append(('synthetic', SyntheticDataProvider))
if config.get('USE_POLYGON_API'):
    providers.append(('polygon', PolygonDataProvider))
providers.append(('simulated', SimulatedDataProvider))  # Always available
```

**Priority Order:**
1. **Synthetic**: Explicitly enabled via USE_SYNTHETIC_DATA flag
2. **Polygon**: Real WebSocket data via USE_POLYGON_API flag  
3. **Simulated**: Always available as fallback provider

### Uniform Interface Implementation

All synthetic data components implement consistent interfaces:

```python
# Consistent factory method interface
provider = factory.create_provider(config, tick_callback, status_callback)

# Uniform connection interface
success = provider.connect(tickers)

# Standard callback signatures
def tick_callback(tick_data: TickData) -> None:
    pass

def status_callback(status: str, extra_info: Optional[Dict] = None) -> None:
    pass
```

## Performance Characteristics and Resource Management

### Memory Management
- **Stateful price tracking**: Maintains price history for each ticker
- **Event object creation**: New TickData objects for each event
- **Universe caching**: Ticker lists and baselines cached in memory
- **Garbage collection**: Event objects eligible for GC after callback processing

### CPU Usage Patterns
- **Background thread**: Synthetic event generation in daemon thread
- **Configurable frequency**: Update interval controls CPU usage
- **Activity scaling**: CPU usage scales with activity level and ticker count
- **Tracing overhead**: Optional tracing adds minimal CPU cost

### Scalability Considerations
- **Ticker universe size**: Performance scales linearly with ticker count
- **Event generation frequency**: Higher rates increase CPU and memory usage  
- **Activity level impact**: Higher activity levels generate more events per period
- **Callback processing**: Downstream processing determines overall throughput

## Future Multi-Frequency Considerations

### Current Architecture Limitations
- **Single frequency**: All events generated at same interval (default 0.5s)
- **Uniform activity**: Same activity level applied to all tickers
- **Static configuration**: Configuration cannot change during runtime

### Extension Points for Multi-Frequency Support
- **Per-ticker configuration**: Individual ticker frequency and activity settings
- **Multiple generator instances**: Separate generators for different frequencies
- **Dynamic configuration**: Runtime configuration changes for different market conditions
- **Frequency-aware event generation**: Events tagged with intended frequency

### Configuration Schema Extensions for Sprint 101
```python
# Proposed multi-frequency configuration
WEBSOCKET_SUBSCRIPTIONS = {
    "per_second": {
        "tickers": ["AAPL", "MSFT", "TSLA"],
        "activity_level": "high"
    },
    "per_minute": {
        "tickers": ["SPY", "QQQ", "IWM"], 
        "activity_level": "medium"
    },
    "fair_market_value": {
        "tickers": ["BRK.A", "BRK.B"],
        "activity_level": "low"
    }
}
```

## Summary

The Synthetic Data Architecture provides a comprehensive simulation system that:

- **Implements DataProvider interface**: Full compatibility with existing data processing pipeline
- **Generates realistic market data**: OHLC, volume, timing, and market status simulation
- **Supports configurable activity levels**: From low-activity to opening-bell volatility
- **Integrates with universe management**: Database-backed ticker selection and baseline pricing
- **Provides comprehensive tracing**: Full monitoring and debugging capabilities
- **Maintains type consistency**: All outputs are TickData objects matching real WebSocket data
- **Scales with configuration**: Performance and behavior controlled via config parameters
- **Prepares for multi-frequency**: Architecture ready for Sprint 101 extensions

The architecture maintains backward compatibility while providing a solid foundation for multi-frequency data source support in future sprints.