# Redis Integration - TickStockPL Interface

**Version**: 2.0.0-simplified  
**Last Updated**: August 25, 2025  
**Status**: Production Ready

## Overview

Redis serves as the primary integration interface between TickStock and TickStockPL, providing scalable real-time event streaming through pub-sub messaging. This clean separation enables independent scaling and development of both systems.

## Architecture

### Redis as Message Broker
```
TickStock → Redis Pub-Sub → TickStockPL
    ↓           ↓           ↓
 Tick Data   Event Queue  Processing
 Publisher   Distribution  Consumer
```

### Key Benefits
- **Decoupled Systems**: Independent scaling and deployment
- **Real-Time Streaming**: Sub-millisecond event distribution
- **Fault Tolerance**: Redis persistence and clustering support
- **Multiple Consumers**: Support for multiple TickStockPL instances

## Channel Structure

### Primary Channels

#### All Ticks Channel
- **Channel**: `tickstock.all_ticks`
- **Purpose**: Stream all market data events
- **Usage**: Primary channel for TickStockPL consumption
- **Message Rate**: Variable based on market activity

#### Per-Ticker Channels
- **Pattern**: `tickstock.ticks.{TICKER}`
- **Purpose**: Ticker-specific data streams
- **Usage**: Selective consumption of specific securities
- **Examples**: `tickstock.ticks.AAPL`, `tickstock.ticks.GOOGL`

### Event Channels (Future)

#### Pattern Events (TickStockPL → TickStock)
- **Channel**: `tickstock.events.patterns`
- **Purpose**: TickStockPL pattern detection results
- **Usage**: Feed processed events back to TickStock
- **Direction**: TickStockPL → TickStock

## Message Format

### Standard Tick Data Message
```json
{
  "event_type": "tick_data",
  "ticker": "AAPL",
  "price": 150.25,
  "volume": 1000,
  "timestamp": 1693123456.789,
  "source": "massive",
  "market_status": "REGULAR"
}
```

### Field Specifications
- **event_type**: Always "tick_data" for market data events
- **ticker**: Stock symbol (string, uppercase)
- **price**: Current price (float, 2 decimal places)
- **volume**: Volume for this tick (integer)
- **timestamp**: Unix timestamp with milliseconds (float)
- **source**: Data source ("polygon", "synthetic", "tickstock_pl")
- **market_status**: Market state ("REGULAR", "PRE", "AFTER", "CLOSED")

## Consumer Implementation

### Basic TickStockPL Consumer
```python
import redis
import json
import time

class TickStockPLConsumer:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True
        )
        self.subscriber = self.redis_client.pubsub()
        
    def start_consuming(self):
        # Subscribe to all ticks
        self.subscriber.subscribe('tickstock.all_ticks')
        
        print("TickStockPL Consumer started...")
        
        for message in self.subscriber.listen():
            if message['type'] == 'message':
                self.process_tick_data(message['data'])
    
    def process_tick_data(self, message_data):
        try:
            tick_data = json.loads(message_data)
            
            # Extract key fields
            ticker = tick_data['ticker']
            price = tick_data['price']
            volume = tick_data['volume']
            timestamp = tick_data['timestamp']
            
            # YOUR TICKSTOCKPL LOGIC HERE
            print(f"Processing {ticker}: ${price} vol={volume}")
            
        except Exception as e:
            print(f"Error processing tick: {e}")

# Usage
consumer = TickStockPLConsumer()
consumer.start_consuming()
```

### Advanced Consumer with Pattern Publishing
```python
class AdvancedTickStockPLConsumer:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0, 
            decode_responses=True
        )
        self.subscriber = self.redis_client.pubsub()
        
    def process_tick_data(self, message_data):
        try:
            tick_data = json.loads(message_data)
            
            # Run pattern detection algorithms
            patterns = self.detect_patterns(tick_data)
            
            # Publish detected patterns back to TickStock
            for pattern in patterns:
                self.publish_pattern_event(pattern)
                
        except Exception as e:
            print(f"Error processing tick: {e}")
    
    def detect_patterns(self, tick_data):
        # YOUR PATTERN DETECTION LOGIC
        patterns = []
        
        # Example: Simple price movement pattern
        if self.is_significant_move(tick_data):
            patterns.append({
                'type': 'price_movement',
                'ticker': tick_data['ticker'],
                'confidence': 0.85,
                'direction': 'up' if tick_data['price'] > self.get_prev_price(tick_data['ticker']) else 'down'
            })
        
        return patterns
    
    def publish_pattern_event(self, pattern):
        pattern_message = {
            'event_type': 'pattern_detected',
            'ticker': pattern['ticker'],
            'pattern_type': pattern['type'],
            'confidence': pattern['confidence'],
            'timestamp': time.time(),
            'source': 'tickstock_pl'
        }
        
        self.redis_client.publish(
            'tickstock.events.patterns',
            json.dumps(pattern_message)
        )
```

## Configuration

### Redis Connection Settings
```python
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_timeout': 30,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}
```

### Environment Variables
```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Consumer Configuration
TICKSTOCKPL_CONSUMER_ID=consumer_1
TICKSTOCKPL_BATCH_SIZE=100
TICKSTOCKPL_PROCESS_TIMEOUT=30
```

## Performance Considerations

### Message Throughput
- **Market Hours**: 50-200 messages/second typical
- **High Activity**: Up to 1000+ messages/second possible
- **Off Hours**: 0-10 messages/second with synthetic data

### Memory Usage
- **Redis Memory**: ~1MB per 10,000 messages (with persistence)
- **Consumer Memory**: Dependent on processing complexity
- **Message Retention**: Configure based on requirements

### Scaling Strategies

#### Multiple Consumer Instances
```python
# Consumer group pattern for load distribution
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Create consumer group
try:
    redis_client.xgroup_create('tickstock-stream', 'tickstockpl-group', id='0', mkstream=True)
except redis.ResponseError:
    pass  # Group already exists

# Consume as part of group
messages = redis_client.xreadgroup(
    'tickstockpl-group', 
    'consumer-1',
    {'tickstock-stream': '>'},
    count=10,
    block=1000
)
```

#### Geographic Distribution
```python
# Redis Sentinel for high availability
import redis.sentinel

sentinel = redis.sentinel.Sentinel([
    ('redis-sentinel-1', 26379),
    ('redis-sentinel-2', 26379),
    ('redis-sentinel-3', 26379)
])

redis_client = sentinel.master_for('tickstock-redis', socket_timeout=0.1)
```

## Monitoring and Health

### Health Checks
```python
def check_redis_health():
    try:
        redis_client.ping()
        return {"redis": "healthy", "latency": measure_latency()}
    except Exception as e:
        return {"redis": "unhealthy", "error": str(e)}

def measure_latency():
    start = time.time()
    redis_client.ping()
    return (time.time() - start) * 1000  # ms
```

### Key Metrics to Monitor
- **Message Rate**: Messages per second consumption
- **Processing Latency**: Time from message to processing complete
- **Error Rate**: Failed message processing percentage
- **Redis Connectivity**: Connection health and latency
- **Queue Depth**: Backlog of unprocessed messages

## Troubleshooting

### Common Issues

#### Connection Issues
```bash
# Test Redis connectivity
redis-cli -h localhost -p 6379 ping

# Check TickStock Redis publishing
redis-cli -h localhost -p 6379 subscribe tickstock.all_ticks
```

#### Message Processing Issues
```python
# Debug message format
def debug_message(message_data):
    try:
        parsed = json.loads(message_data)
        print(f"Valid JSON: {parsed}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        print(f"Raw data: {message_data}")
```

#### Performance Issues
```python
# Monitor processing time
import time

def timed_processing(message_data):
    start = time.time()
    result = process_tick_data(message_data)
    duration = time.time() - start
    
    if duration > 0.1:  # Log slow processing
        print(f"Slow processing: {duration:.3f}s")
    
    return result
```

---

This Redis integration provides a robust, scalable interface for TickStockPL integration while maintaining clean separation of concerns and supporting future enhancements.