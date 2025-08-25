# Data Sources - Simplified Architecture

**Version**: 2.0.0-simplified  
**Last Updated**: August 25, 2025  
**Status**: Post-Cleanup Data Sources

## Overview

TickStock's simplified data source architecture supports two primary data sources: live market data from Polygon.io and synthetic data generation for testing. The system uses a simple factory pattern for data source selection.

## Supported Data Sources

### 1. Polygon.io (Live Data)
- **Type**: Real-time WebSocket connection
- **Coverage**: US stock market data
- **Data Types**: Aggregates (A), Trades (T), Quotes (Q)
- **Rate Limits**: Based on Polygon.io subscription tier
- **Market Hours**: Full market hours including pre/after market

**Configuration**:
```bash
USE_POLYGON_API=true
POLYGON_API_KEY=your_api_key_here
```

### 2. Synthetic Data (Testing)
- **Type**: Simulated market data generation
- **Purpose**: Development and testing without API costs
- **Realism**: Price movements with configurable volatility
- **Market Simulation**: Realistic market hours and status
- **Performance**: Configurable tick rates and activity levels

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_ACTIVITY_LEVEL=medium  # low, medium, high
```

## Architecture

### Factory Pattern
```python
from src.infrastructure.data_sources.factory import DataProviderFactory

config = {
    'USE_POLYGON_API': True,
    'POLYGON_API_KEY': 'your_key'
}

provider = DataProviderFactory.get_provider(config)
```

### Priority Logic
1. **Polygon API**: Used if `USE_POLYGON_API=true` and valid API key provided
2. **Synthetic Data**: Used as fallback or when `USE_SYNTHETIC_DATA=true`
3. **Error Handling**: Graceful fallback to synthetic if Polygon fails

## Data Flow

### Real-Time Processing
```
Data Source → TickData Objects → Market Data Service → Redis Pub-Sub
```

### Message Format
All data sources produce standardized `TickData` objects:
```python
@dataclass
class TickData:
    ticker: str
    price: float
    volume: int
    timestamp: float
    source: str
    event_type: str
    market_status: str
```

## Configuration Reference

### Environment Variables
```bash
# Data Source Selection
USE_POLYGON_API=true/false
USE_SYNTHETIC_DATA=true/false

# Polygon Configuration
POLYGON_API_KEY=your_polygon_api_key
POLYGON_WEBSOCKET_MAX_RETRIES=5
POLYGON_WEBSOCKET_RECONNECT_DELAY=5

# Synthetic Configuration
SYNTHETIC_ACTIVITY_LEVEL=medium
SYNTHETIC_UPDATE_INTERVAL=1.0
MARKET_TIMEZONE=US/Eastern

# Default Universe
TICKER_UNIVERSE=AAPL,GOOGL,MSFT,TSLA,AMZN,NFLX,META,NVDA
```

### Provider-Specific Settings

#### Polygon Provider
- **API Key**: Required for live data access
- **WebSocket URL**: `wss://socket.polygon.io/stocks`
- **Reconnection**: Automatic with exponential backoff
- **Authentication**: API key-based authentication

#### Synthetic Provider
- **Price Generation**: Hash-based deterministic prices with variance
- **Volume Generation**: Configurable volume ranges by activity level
- **Market Status**: Time-based market status simulation
- **Rate Limiting**: Configurable update intervals

## Usage Examples

### Basic Setup
```python
from src.core.services.market_data_service import MarketDataService

config = {
    'USE_SYNTHETIC_DATA': True,
    'SYNTHETIC_ACTIVITY_LEVEL': 'medium'
}

service = MarketDataService(config)
service.start()
```

### Live Data Setup
```python
config = {
    'USE_POLYGON_API': True,
    'POLYGON_API_KEY': 'your_api_key',
    'TICKER_UNIVERSE': ['AAPL', 'GOOGL', 'MSFT']
}

service = MarketDataService(config)
service.start()
```

## Performance Characteristics

### Polygon Provider
- **Latency**: ~10-50ms from market to application
- **Throughput**: Variable based on market activity
- **Reliability**: Depends on Polygon.io service and internet connection
- **Cost**: Based on Polygon.io subscription plan

### Synthetic Provider
- **Latency**: <1ms generation time
- **Throughput**: Configurable (default ~25 ticks/second)
- **Reliability**: 100% uptime (local generation)
- **Cost**: Free (no external dependencies)

## Monitoring

### Health Checks
Both providers support health checking:
```python
provider = DataProviderFactory.get_provider(config)
is_healthy = provider.is_available()
```

### Key Metrics
- **Connection Status**: Active connection to data source
- **Message Rate**: Ticks per second received
- **Error Rate**: Failed messages or connection issues
- **Latency**: Time from market event to application

---

This simplified data source architecture provides reliable market data ingestion while maintaining flexibility for development and testing scenarios.