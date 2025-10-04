# TickStockAppV2 Integration Guide - Phase 5 (Streaming Engine)

**Sprint**: 33
**Phase**: 5 - Streaming Engine Foundation
**Purpose**: Enable TickStockAppV2 to consume real-time streaming events during market hours

## Overview

Phase 5 introduces real-time streaming capabilities that operate during market hours (9:30 AM - 4:00 PM ET). The streaming engine processes WebSocket data, aggregates to 1-minute OHLCV bars, and performs real-time pattern/indicator detection.

## New Redis Channels for Phase 5

### Session Management Channels
```python
# Streaming session lifecycle
'tickstock:streaming:session_started'    # Session start event
'tickstock:streaming:session_stopped'    # Session end event
'tickstock:streaming:health'            # Health metrics every 60s
```

### Real-time Processing Channels
```python
# Pattern detection (streaming)
'tickstock:patterns:streaming'          # All streaming pattern detections
'tickstock:patterns:detected'           # High confidence patterns (≥0.8)

# Indicator calculations (streaming)
'tickstock:indicators:streaming'        # All streaming calculations
'tickstock:alerts:indicators'           # RSI/MACD/BB alerts

# Persistence events
'tickstock:streaming:persistence'       # Batch storage confirmations

# Critical alerts
'tickstock:alerts:critical'             # System health critical issues
```

## Event Message Formats

### 1. Session Started Event
```json
{
    "event": "session_started",
    "timestamp": "2025-01-24T09:30:00Z",
    "data": {
        "session_id": "uuid-string",
        "symbol_universe_key": "market_leaders:top_500",
        "start_time": "2025-01-24T09:30:00Z",
        "trigger_type": "scheduled"
    }
}
```

### 2. Pattern Detection Event (Streaming)
```json
{
    "event": "pattern_detected",
    "session_id": "uuid-string",
    "timestamp": "2025-01-24T10:15:30Z",
    "detection": {
        "pattern_type": "Doji",
        "symbol": "AAPL",
        "timestamp": "2025-01-24T10:15:00Z",
        "confidence": 0.85,
        "parameters": {
            "open": 150.00,
            "close": 150.05,
            "body_ratio": 0.0003
        },
        "timeframe": "1min"
    }
}
```

### 3. Indicator Calculation Event (Streaming)
```json
{
    "event": "indicator_calculated",
    "session_id": "uuid-string",
    "timestamp": "2025-01-24T10:15:30Z",
    "calculation": {
        "indicator_type": "RSI",
        "symbol": "AAPL",
        "timestamp": "2025-01-24T10:15:00Z",
        "values": {
            "value": 72.5
        },
        "timeframe": "1min"
    }
}
```

### 4. Indicator Alert Event
```json
{
    "alert_type": "RSI_OVERBOUGHT",
    "symbol": "AAPL",
    "timestamp": "2025-01-24T10:15:30Z",
    "session_id": "uuid-string",
    "data": {
        "rsi": 72.5
    }
}
```

Alert types include:
- `RSI_OVERBOUGHT` (RSI > 70)
- `RSI_OVERSOLD` (RSI < 30)
- `MACD_BULLISH_CROSS`
- `MACD_BEARISH_CROSS`
- `BB_UPPER_BREAK`
- `BB_LOWER_BREAK`

### 5. Health Monitoring Event
```json
{
    "event": "streaming_health",
    "timestamp": "2025-01-24T10:30:00Z",
    "session_id": "uuid-string",
    "status": "healthy",
    "issues": [],
    "connection": {
        "active": 1,
        "failed": 0,
        "reconnections": 0
    },
    "data_flow": {
        "ticks_per_second": 850,
        "bars_per_minute": 487,
        "processing_lag_ms": 45
    },
    "resources": {
        "cpu_percent": 32.5,
        "memory_mb": 1250.0,
        "memory_percent": 15.6
    },
    "active_symbols": 487,
    "stale_symbols": {
        "count": 0,
        "symbols": []
    }
}
```

## Integration Steps for TickStockAppV2

### 1. Subscribe to Streaming Channels

```python
# app/services/redis_subscriber.py

class RedisSubscriber:
    def __init__(self):
        # Existing channels...

        # Add Phase 5 streaming channels
        self.streaming_channels = [
            'tickstock:streaming:session_started',
            'tickstock:streaming:session_stopped',
            'tickstock:streaming:health',
            'tickstock:patterns:streaming',
            'tickstock:indicators:streaming',
            'tickstock:alerts:indicators',
            'tickstock:alerts:critical'
        ]

    def subscribe(self):
        # Subscribe to streaming channels
        for channel in self.streaming_channels:
            self.pubsub.subscribe(channel)
```

### 2. Handle Streaming Pattern Events

```python
# app/services/streaming_handler.py

class StreamingEventHandler:
    def __init__(self, websocket_manager, db_connection):
        self.websocket_manager = websocket_manager
        self.db = db_connection
        self.current_session = None

    def handle_pattern_detection(self, message):
        """Handle real-time pattern detection from streaming."""
        data = json.loads(message['data'])

        # Extract detection details
        detection = data['detection']

        # Store in database (optional)
        self.store_streaming_pattern(detection)

        # Send to WebSocket clients immediately
        self.websocket_manager.broadcast({
            'type': 'streaming_pattern',
            'data': detection
        })

        # If high confidence, trigger alert
        if detection['confidence'] >= 0.8:
            self.trigger_pattern_alert(detection)

    def handle_indicator_alert(self, message):
        """Handle indicator alerts (RSI, MACD, BB)."""
        alert = json.loads(message['data'])

        # Send to WebSocket for UI notification
        self.websocket_manager.broadcast({
            'type': 'indicator_alert',
            'alert_type': alert['alert_type'],
            'symbol': alert['symbol'],
            'data': alert['data']
        })

        # Store alert for history
        self.store_indicator_alert(alert)
```

### 3. Monitor Streaming Health

```python
# app/services/health_monitor.py

class StreamingHealthMonitor:
    def __init__(self):
        self.latest_health = {}
        self.health_history = deque(maxlen=60)  # Last hour

    def handle_health_event(self, message):
        """Process streaming health metrics."""
        health = json.loads(message['data'])

        self.latest_health = health
        self.health_history.append(health)

        # Check for critical issues
        if health['status'] == 'critical':
            self.alert_critical_issue(health)

        # Update dashboard
        self.update_health_dashboard(health)

    def get_streaming_status(self):
        """Get current streaming status for API."""
        return {
            'session_id': self.latest_health.get('session_id'),
            'status': self.latest_health.get('status', 'unknown'),
            'active_symbols': self.latest_health.get('active_symbols', 0),
            'data_flow': self.latest_health.get('data_flow', {}),
            'issues': self.latest_health.get('issues', [])
        }
```

### 4. WebSocket Updates for UI

```javascript
// frontend/src/services/streamingService.js

class StreamingService {
    constructor(websocket) {
        this.ws = websocket;
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        this.ws.on('streaming_pattern', (data) => {
            // Update pattern detection UI
            this.updatePatternList(data);

            // Show notification for high confidence
            if (data.confidence >= 0.8) {
                this.showPatternNotification(data);
            }
        });

        this.ws.on('indicator_alert', (alert) => {
            // Show alert notification
            this.showIndicatorAlert(alert);

            // Update symbol dashboard
            this.updateSymbolIndicators(alert.symbol, alert.data);
        });

        this.ws.on('streaming_health', (health) => {
            // Update health status indicator
            this.updateHealthStatus(health);
        });
    }

    showIndicatorAlert(alert) {
        const messages = {
            'RSI_OVERBOUGHT': `${alert.symbol}: RSI Overbought (${alert.data.rsi})`,
            'RSI_OVERSOLD': `${alert.symbol}: RSI Oversold (${alert.data.rsi})`,
            'MACD_BULLISH_CROSS': `${alert.symbol}: MACD Bullish Crossover`,
            'MACD_BEARISH_CROSS': `${alert.symbol}: MACD Bearish Crossover`,
            'BB_UPPER_BREAK': `${alert.symbol}: Breaking Upper Bollinger Band`,
            'BB_LOWER_BREAK': `${alert.symbol}: Breaking Lower Bollinger Band`
        };

        this.notify(messages[alert.alert_type] || 'Indicator Alert');
    }
}
```

### 5. Database Schema Updates

```sql
-- Store streaming patterns for historical analysis
CREATE TABLE IF NOT EXISTS app_streaming_patterns (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    pattern_type VARCHAR(50),
    symbol VARCHAR(10),
    detection_time TIMESTAMPTZ,
    confidence DECIMAL(3,2),
    parameters JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Store indicator alerts
CREATE TABLE IF NOT EXISTS app_indicator_alerts (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    alert_type VARCHAR(50),
    symbol VARCHAR(10),
    alert_time TIMESTAMPTZ,
    alert_data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_app_streaming_patterns_symbol ON app_streaming_patterns(symbol);
CREATE INDEX idx_app_streaming_patterns_time ON app_streaming_patterns(detection_time);
CREATE INDEX idx_app_indicator_alerts_symbol ON app_indicator_alerts(symbol);
CREATE INDEX idx_app_indicator_alerts_type ON app_indicator_alerts(alert_type);
```

### 6. API Endpoints

```python
# app/routes/streaming.py

@app.route('/api/streaming/status')
def get_streaming_status():
    """Get current streaming session status."""
    monitor = get_streaming_monitor()
    return jsonify(monitor.get_streaming_status())

@app.route('/api/streaming/patterns/<symbol>')
def get_streaming_patterns(symbol):
    """Get recent streaming patterns for symbol."""
    patterns = db.query("""
        SELECT * FROM app_streaming_patterns
        WHERE symbol = %s
        AND detection_time > NOW() - INTERVAL '1 hour'
        ORDER BY detection_time DESC
    """, [symbol])
    return jsonify(patterns)

@app.route('/api/streaming/alerts')
def get_indicator_alerts():
    """Get recent indicator alerts."""
    alerts = db.query("""
        SELECT * FROM app_indicator_alerts
        WHERE alert_time > NOW() - INTERVAL '1 hour'
        ORDER BY alert_time DESC
        LIMIT 100
    """)
    return jsonify(alerts)
```

## Testing the Integration

### 1. Manual Testing During Market Hours
```bash
# Start TickStockPL streaming
python -m src.services.streaming_scheduler

# Monitor Redis events
redis-cli PSUBSCRIBE "tickstock:streaming:*" "tickstock:patterns:streaming" "tickstock:indicators:streaming"

# Check TickStockAppV2 logs
tail -f logs/tickstockapp.log | grep -E "streaming|pattern|indicator"
```

### 2. Simulate Events for Testing
```python
# test_streaming_events.py
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379)

# Simulate pattern detection
pattern_event = {
    "event": "pattern_detected",
    "session_id": "test-session",
    "timestamp": datetime.utcnow().isoformat(),
    "detection": {
        "pattern_type": "Hammer",
        "symbol": "AAPL",
        "confidence": 0.85,
        "timeframe": "1min"
    }
}

r.publish('tickstock:patterns:streaming', json.dumps(pattern_event))

# Simulate RSI alert
alert_event = {
    "alert_type": "RSI_OVERBOUGHT",
    "symbol": "TSLA",
    "timestamp": datetime.utcnow().isoformat(),
    "data": {"rsi": 75.5}
}

r.publish('tickstock:alerts:indicators', json.dumps(alert_event))
```

## Performance Considerations

1. **Event Rate**: Expect up to 500-1000 events per minute during active trading
2. **WebSocket Broadcasting**: Use debouncing for high-frequency updates
3. **Database Writes**: Batch inserts for streaming patterns/alerts
4. **Memory Usage**: Implement circular buffers for historical data
5. **Connection Management**: Handle WebSocket reconnections gracefully

## Configuration

Add to TickStockAppV2's `.env`:

```bash
# Streaming Integration
STREAMING_ENABLED=true
STREAMING_PATTERN_MIN_CONFIDENCE=0.7
STREAMING_ALERT_NOTIFICATIONS=true
STREAMING_HEALTH_CHECK_INTERVAL=60
STREAMING_MAX_HISTORY_SIZE=1000
```

## Monitoring Dashboard Components

### 1. Streaming Status Widget
- Session ID and start time
- Active/Stale symbols count
- Connection status
- Data flow rate (ticks/bars per minute)

### 2. Real-time Pattern Feed
- Live pattern detections as they occur
- Confidence indicators
- Symbol filtering

### 3. Indicator Alert Panel
- RSI extremes
- MACD crossovers
- Bollinger Band breaks
- Historical alert chart

### 4. Health Metrics Graph
- CPU/Memory usage over time
- Processing lag trends
- Connection stability

## Troubleshooting

| Issue | Check | Solution |
|-------|-------|----------|
| No streaming events | StreamingScheduler running? | Start during market hours |
| Missing patterns | Pattern definitions enabled? | Check database configuration |
| High lag | Health metrics status | Scale resources or reduce symbols |
| Connection drops | WebSocket reconnections | Check network/API limits |

## Next Steps

1. Implement UI components for streaming data
2. Add pattern/alert filtering by symbol
3. Create historical analysis views
4. Add notification preferences
5. Implement replay functionality for testing