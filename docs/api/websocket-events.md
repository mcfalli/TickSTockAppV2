# WebSocket Events API

## Overview

TickStock uses WebSocket connections for real-time data delivery. All connections require authentication and deliver personalized data streams based on user preferences.

## Connection

### Endpoint
wss://your-domain.com/socket.io/

### Authentication
WebSocket connections require valid session authentication. Unauthenticated connections are immediately terminated.

### Connection Example
```javascript
const socket = io('/', {
    transports: ['websocket'],
    upgrade: false
});

socket.on('connect', () => {
    console.log('Connected to TickStock');
});
Events
Client → Server Events
connect
Establishes WebSocket connection. Requires authenticated session.
disconnect
Client-initiated disconnection.
request_filtered_data_refresh
Requests immediate data refresh with current filters applied.
Server → Client Events
status_update
System status and configuration updates.
Frequency: Event-driven (connection changes, universe updates)
Payload:
json{
    "status": "healthy",
    "connected": true,
    "provider": "Synthetic",
    "market_status": "REGULAR",
    "timestamp": "2024-12-19T10:26:30.136053",
    "avg_response_time": 0,
    "last_update": "2024-12-19T11:26:30.136053-04:00",
    "config": {
        "update_interval": 2,
        "momentum_window": 5,
        "flow_window": 30,
        "data_debug_trace": false
    },
    "universe_filtering": {
        "active_universes": {
            "market": ["DEFAULT_UNIVERSE"],
            "highlow": ["DEFAULT_UNIVERSE"]
        },
        "filter_statistics": {
            "total_events_processed": 122,
            "total_events_sent": 122,
            "total_events_filtered": 0,
            "overall_filter_rate": 0
        }
    }
}
dual_universe_stock_data
Main data event containing market events and analytics.
Frequency: Every 0.5 seconds
Payload Structure:
json{
    "core_universe_analytics": {
        "gauge_analytics": {
            "ema_net_score": 12.5,
            "current_net_score": 15.2,
            "alpha_used": 0.3,
            "sample_count": 10,
            "last_updated": "2024-12-19T14:23:45.123Z"
        },
        "current_state": {
            "net_score": 15.2,
            "activity_level": "moderate",
            "buying_count": 45000,
            "selling_count": 32000,
            "activity_count": 77000,
            "universe_size": 2800
        }
    },
    "user_universe_analytics": {
        "gauge_analytics": {
            "ema_net_score": 8.1,
            "current_net_score": 9.4,
            "alpha_used": 0.3,
            "sample_count": 8
        },
        "current_state": {
            "net_score": 8.1,
            "activity_level": "low",
            "buying_count": 12000,
            "selling_count": 8500,
            "activity_count": 20500,
            "universe_size": 762
        }
    },
    "highs": [...],
    "lows": [...],
    "trending": {...},
    "surging": [...],
    "counts": {...},
    "market_status": "REGULAR"
}
Event Objects
High/Low Event
json{
    "ticker": "AAPL",
    "price": 150.25,
    "time": "14:23:45",
    "market_status": "REGULAR",
    "count": 5,
    "label": "high",
    "percent_change": 1.2,
    "vwap": 148.75,
    "volume": 125000,
    "vwap_distance": 2.3,
    "trend_flag": "up",
    "surge_flag": null,
    "session_high_count": 12,
    "session_low_count": 3,
    "session_total_events": 15
}
Trending Stock Event
json{
    "ticker": "NVDA",
    "trend_strength": "strong",
    "trend_score": 0.85,
    "price": 892.50,
    "last_trend_update": "2024-12-19T14:23:40",
    "trend_age": 5.2
}
Surge Event
json{
    "ticker": "TSLA",
    "direction": "up",
    "magnitude": 3.2,
    "score": 78.5,
    "strength": "strong",
    "trigger_type": "price_and_volume",
    "description": "Strong upward surge detected",
    "time": "14:23:42",
    "volume_multiplier": 2.8,
    "surge_age": 3.1,
    "daily_surge_count": 4
}
Client Implementation
JavaScript Example
javascript// Connection with error handling
const socket = io('/', {
    transports: ['websocket'],
    upgrade: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5
});

// Status updates
socket.on('status_update', (data) => {
    const status = typeof data === 'string' ? JSON.parse(data) : data;
    updateConnectionStatus(status.connected);
    updateMarketStatus(status.market_status);
});

// Stock data
socket.on('dual_universe_stock_data', (data) => {
    const stockData = typeof data === 'string' ? JSON.parse(data) : data;
    
    // Update gauges
    if (stockData.core_universe_analytics) {
        updateCoreGauge(stockData.core_universe_analytics);
    }
    
    // Update events
    updateHighLowEvents(stockData.highs, stockData.lows);
    updateTrendingStocks(stockData.trending);
    updateSurgingStocks(stockData.surging);
});

// Error handling
socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
});

socket.on('disconnect', (reason) => {
    console.log('Disconnected:', reason);
});
Python Example
pythonimport socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to TickStock')

@sio.on('dual_universe_stock_data')
def on_stock_data(data):
    # Process real-time stock data
    process_market_events(data)

@sio.on('status_update')
def on_status(data):
    # Handle status updates
    update_system_status(data)

# Connect with authentication
sio.connect('https://your-domain.com', 
            auth={'token': 'your-auth-token'})
Rate Limits

Connection Limit: 5 concurrent connections per user
Message Rate: No explicit limit (server controls emission rate)
Reconnection: Max 5 attempts with exponential backoff

Error Handling
Connection Errors

401 Unauthorized - Invalid or missing authentication
429 Too Many Requests - Connection limit exceeded
503 Service Unavailable - Server temporarily unavailable

Data Errors
All data errors are logged server-side. Clients should handle:

Malformed JSON
Missing required fields
Unexpected data types

Best Practices

Always parse JSON - Data may arrive as string or object
Handle reconnection - Network interruptions are common
Debounce updates - Prevent UI thrashing with rapid updates
Monitor memory - Long-running connections can accumulate data
Use compression - Enable WebSocket compression for efficiency

Debugging
Enable Debug Logging
javascriptlocalStorage.setItem('debug', 'socket.io-client:*');
Monitor Events
javascript// Log all events
const originalEmit = socket.emit;
socket.emit = function() {
    console.log('Emitting:', arguments);
    originalEmit.apply(socket, arguments);
};

For REST API endpoints, see REST Endpoints