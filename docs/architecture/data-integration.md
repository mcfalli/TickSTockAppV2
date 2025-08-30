# Data Integration - Simplified Architecture

**Version**: 2.0.0-simplified  
**Last Updated**: August 25, 2025  
**Status**: Post-Cleanup Data Flow

## Overview

TickStock's simplified data integration provides essential market data ingestion and real-time distribution capabilities. The system supports both live and synthetic data sources with Redis-based event streaming for TickStockPL integration.

## Data Sources

### Polygon.io Integration
- **WebSocket Connection**: Real-time tick data from Polygon.io
- **Authentication**: API key-based authentication
- **Event Types**: Aggregate (A), Trade (T), Quote (Q) events
- **Market Status**: Automatic market status detection

**Configuration**:
```bash
USE_POLYGON_API=true
POLYGON_API_KEY=your_api_key_here
```

### Synthetic Data Generation
- **Realistic Simulation**: Price movement simulation with volatility
- **Market Status**: Simulated market hours and status
- **Configurable Activity**: Low, medium, high activity levels
- **Default Universe**: 8 major tickers for testing

**Configuration**:
```bash
USE_SYNTHETIC_DATA=true
SYNTHETIC_ACTIVITY_LEVEL=medium
```

## Data Processing Flow

### 1. Data Ingestion
```
Polygon WebSocket/Synthetic → TickData Objects → Market Data Service
```

### 2. Redis Publishing
```
TickData → Redis Message → Pub-Sub Channels:
  - tickstock.all_ticks (all data)
  - tickstock.ticks.{TICKER} (per ticker)
```

### 3. WebSocket Broadcasting
```
Redis Events → WebSocket Publisher → SocketIO → Browser Clients
```

## Message Format

All data events use this standardized JSON format:

```json
{
  "event_type": "tick_data",
  "ticker": "AAPL",
  "price": 150.25,
  "volume": 1000,
  "timestamp": 1693123456.789,
  "source": "polygon",
  "market_status": "REGULAR"
}
```

## Configuration

### Environment Variables
```bash
# Data Source Selection (choose one)
USE_SYNTHETIC_DATA=true/false
USE_POLYGON_API=true/false

# Polygon Configuration
POLYGON_API_KEY=your_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Default Ticker Universe
TICKER_UNIVERSE=AAPL,GOOGL,MSFT,TSLA,AMZN,NFLX,META,NVDA
```

### Priority Logic
1. **Polygon API**: Used if `USE_POLYGON_API=true` and API key provided
2. **Synthetic Data**: Used if `USE_SYNTHETIC_DATA=true` or as fallback
3. **Default**: Falls back to synthetic data if no source configured

## Integration Points

### TickStockPL Consumer
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
subscriber = redis_client.pubsub()
subscriber.subscribe('tickstock.all_ticks')

for message in subscriber.listen():
    if message['type'] == 'message':
        tick_data = json.loads(message['data'])
        # Process tick data with TickStockPL
        process_market_data(tick_data)
```

### WebSocket Client
```javascript
const socket = io();

socket.on('tick_data', (data) => {
    console.log(`${data.ticker}: $${data.price} (${data.volume})`);
    updateUI(data);
});

// Subscribe to specific tickers
socket.emit('subscribe_tickers', {
    tickers: ['AAPL', 'GOOGL', 'MSFT']
});
```

## Performance Characteristics

### Throughput
- **Synthetic Data**: ~25-50 ticks/second configurable rate
- **Polygon WebSocket**: Real-time market speed (variable)
- **Redis Publishing**: Sub-millisecond event distribution

### Latency
- **Data Ingestion**: <10ms from source to Redis
- **WebSocket Emission**: <20ms from Redis to browser clients
- **End-to-End**: <50ms total latency for real-time updates

### Scalability
- **Redis Pub-Sub**: Horizontal scaling support
- **Multiple Consumers**: TickStockPL and WebSocket clients simultaneously
- **Geographic Distribution**: Redis replication for multi-region support

## Monitoring

### Health Checks
- **GET /health**: System status including data source connectivity
- **GET /stats**: Performance metrics and processing statistics

### Key Metrics
- **Ticks Processed**: Total tick data events processed
- **Tick Rate**: Events per second throughput
- **Redis Connectivity**: Pub-sub channel health
- **Source Status**: Data source connection status

---

This simplified data integration provides the essential functionality for real-time market data processing while maintaining high performance and easy TickStockPL integration.