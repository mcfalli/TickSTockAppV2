# TickStockPL Integration Guide

**Date**: August 25, 2025  
**Version**: 2.0.0-simplified  
**Status**: Ready for Integration  

## Overview

This guide provides complete instructions for integrating TickStockPL with the simplified TickStock application. After the major cleanup (Phases 6-10), TickStock now provides a clean Redis-based interface perfect for TickStockPL consumption.

## Architecture Overview

### Simplified Data Flow
```
Market Data → TickStock → Redis Pub-Sub → TickStockPL
                ↓
            WebSocket Clients (UI)
```

### Key Components
- **TickStock**: Simplified data ingestion and Redis publishing
- **Redis**: Pub-sub message broker for real-time event streaming  
- **TickStockPL**: External processing engine (to be integrated)
- **WebSocket**: Real-time UI updates for monitoring

## Redis Integration

### Connection Configuration
```yaml
# Redis Configuration
REDIS_HOST: localhost
REDIS_PORT: 6379
REDIS_DB: 0
```

### Message Channels

#### 1. All Ticks Channel
**Channel**: `tickstock.all_ticks`  
**Purpose**: Receive all tick data from TickStock  
**Usage**: Primary channel for TickStockPL to consume all market data

#### 2. Per-Ticker Channels  
**Channel Pattern**: `tickstock.ticks.{TICKER}`  
**Purpose**: Ticker-specific data streams  
**Usage**: Selective consumption of specific ticker data

### Message Format

All Redis messages use this standardized JSON format:

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

#### Field Descriptions
- `event_type`: Always "tick_data" for tick events
- `ticker`: Stock ticker symbol (e.g., "AAPL", "GOOGL")
- `price`: Current price as float
- `volume`: Volume as integer
- `timestamp`: Unix timestamp with milliseconds
- `source`: Data source ("polygon", "synthetic", "tickstock_pl")
- `market_status`: Market status ("REGULAR", "PRE", "AFTER", "CLOSED")

## TickStockPL Integration Steps

### Step 1: Redis Connection Setup

```python
import redis
import json

# Connect to Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Create subscriber
subscriber = redis_client.pubsub()
```

### Step 2: Subscribe to TickStock Channels

```python
# Subscribe to all ticks
subscriber.subscribe('tickstock.all_ticks')

# Or subscribe to specific tickers
subscriber.subscribe('tickstock.ticks.AAPL')
subscriber.subscribe('tickstock.ticks.GOOGL')
```

### Step 3: Process Incoming Messages

```python
def process_tick_data(message_data):
    """Process tick data from TickStock."""
    try:
        tick_data = json.loads(message_data)
        
        # Extract tick information
        ticker = tick_data['ticker']
        price = tick_data['price']
        volume = tick_data['volume']
        timestamp = tick_data['timestamp']
        
        # YOUR TICKSTOCKPL PROCESSING LOGIC HERE
        # - Run pattern detection algorithms
        # - Generate trading signals
        # - Update portfolio positions
        # - Calculate risk metrics
        
        print(f"Processed {ticker}: ${price} (vol: {volume})")
        
    except Exception as e:
        print(f"Error processing tick data: {e}")

# Message consumption loop
for message in subscriber.listen():
    if message['type'] == 'message':
        process_tick_data(message['data'])
```

### Step 4: Publish Events Back to TickStock

```python
def publish_tickstockpl_event(event_data):
    """Publish TickStockPL events back to Redis."""
    
    # Create TickStockPL event message
    tickstockpl_event = {
        'event_type': 'pattern_detected',
        'ticker': event_data['ticker'],
        'pattern_type': event_data['pattern'],
        'confidence': event_data['confidence'],
        'timestamp': time.time(),
        'source': 'tickstock_pl'
    }
    
    # Publish to TickStock consumption channel
    redis_client.publish(
        'tickstock.events.patterns', 
        json.dumps(tickstockpl_event)
    )
```

## TickStock Configuration

### Environment Variables

```bash
# Data Source Configuration
USE_SYNTHETIC_DATA=true          # Use synthetic data for testing
USE_POLYGON_API=false           # Disable Polygon API for testing
POLYGON_API_KEY=your_key_here   # Polygon API key (if using real data)

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application Configuration
DEBUG=true
HOST=0.0.0.0
PORT=5000

# Ticker Universe (optional - defaults provided)
TICKER_UNIVERSE=AAPL,GOOGL,MSFT,TSLA,AMZN,NFLX,META,NVDA
```

### Starting TickStock

```bash
# Install dependencies
pip install -r requirements/base.txt

# Start Redis (if not running)
redis-server

# Start TickStock application
cd TickStockAppV2
python src/app.py
```

## Monitoring and Health Checks

### TickStock Health Endpoint
```
GET http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": 1693123456.789,
  "redis_connected": true,
  "market_service_running": true,
  "version": "2.0.0-simplified"
}
```

### TickStock Statistics Endpoint  
```
GET http://localhost:5000/stats
```

Response:
```json
{
  "app_version": "2.0.0-simplified",
  "redis_connected": true,
  "market_service": {
    "ticks_processed": 1500,
    "events_published": 1500,
    "tick_rate": 25.3,
    "redis_connected": true
  }
}
```

## Testing Integration

### 1. Test Redis Connection

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
redis_client.ping()  # Should return True
```

### 2. Test Message Consumption

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
subscriber = redis_client.pubsub()
subscriber.subscribe('tickstock.all_ticks')

# Listen for 10 messages
for i, message in enumerate(subscriber.listen()):
    if message['type'] == 'message':
        tick_data = json.loads(message['data'])
        print(f"Received: {tick_data['ticker']} @ ${tick_data['price']}")
        
        if i >= 10:
            break
```

### 3. Test Bi-Directional Communication

```python
# Consume TickStock events
def consume_tickstock_events():
    subscriber = redis_client.pubsub()
    subscriber.subscribe('tickstock.all_ticks')
    
    for message in subscriber.listen():
        if message['type'] == 'message':
            tick_data = json.loads(message['data'])
            
            # Process and potentially generate events
            if should_generate_pattern_event(tick_data):
                publish_pattern_event(tick_data)

# Publish TickStockPL events  
def publish_pattern_event(tick_data):
    pattern_event = {
        'event_type': 'pattern_detected',
        'ticker': tick_data['ticker'],
        'pattern_type': 'breakout',
        'confidence': 0.85,
        'timestamp': time.time(),
        'source': 'tickstock_pl'
    }
    
    redis_client.publish('tickstock.events.patterns', json.dumps(pattern_event))
```

## Deployment Considerations

### Production Setup

1. **Redis Configuration**
   - Use Redis Cluster for high availability
   - Configure persistence (RDB + AOF)
   - Set appropriate memory limits
   - Enable authentication

2. **TickStock Configuration** 
   - Use real Polygon API key for live data
   - Set appropriate logging levels
   - Configure environment-specific settings
   - Enable health monitoring

3. **TickStockPL Configuration**
   - Implement proper error handling and reconnection logic
   - Add metrics collection for monitoring  
   - Configure logging for debugging
   - Implement graceful shutdown procedures

### Scaling Considerations

- **Multiple TickStockPL Instances**: Use Redis consumer groups for load distribution
- **Geographic Distribution**: Consider Redis replication for multi-region setups
- **Message Throughput**: Monitor Redis memory usage and connection limits
- **Event Processing**: Implement batching for high-volume scenarios

## Troubleshooting

### Common Issues

1. **Connection Issues**
   ```bash
   # Test Redis connectivity
   redis-cli ping
   
   # Check TickStock logs
   tail -f logs/core_*.log
   ```

2. **Missing Messages**
   ```python
   # Check subscription status
   subscriber.get_message(timeout=1)
   
   # Verify channel names
   redis_client.pubsub_channels('tickstock.*')
   ```

3. **Message Format Issues**
   ```python
   # Validate JSON format
   try:
       tick_data = json.loads(message_data)
   except json.JSONDecodeError as e:
       print(f"Invalid JSON: {e}")
   ```

## Support and Resources

- **TickStock Logs**: `logs/core_*.log`
- **Redis Logs**: Check Redis server logs
- **Health Endpoint**: `GET /health` for system status
- **Statistics**: `GET /stats` for performance metrics

---

This integration guide provides everything needed to connect TickStockPL with the simplified TickStock system. The Redis pub-sub architecture enables real-time, scalable communication between the systems while maintaining clean separation of concerns.