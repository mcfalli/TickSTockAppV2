# 101 Polygon Reference Documentation

This document provides comprehensive Polygon.io API reference information for multi-frequency WebSocket implementation in TickStock.

## Fair Market Value (FMV)

### WebSocket Connection
- **Endpoint**: `wss://business.polygon.io/stocks`
- **Access Level**: Stocks Business plan required
- **Description**: Stream real-time Fair Market Value (FMV) data providing algorithmically derived, real-time estimates of security fair market prices

### Use Cases
- Pricing strategies
- Algorithmic modeling  
- Risk assessment
- Investor decision-making

### Subscription Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | string | Yes | Stock ticker symbol, `*` for all tickers, or comma-separated list |

### Response Attributes
| Field | Type | Description |
|-------|------|-------------|
| ev | enum | Event type: "FMV" |
| fmv | number | Fair market value (Business plan proprietary algorithm) |
| sym | string | Ticker symbol for the security |
| t | integer | Nanosecond timestamp |

### Sample FMV Response
```json
{
  "ev": "FMV",
  "fmv": 150.75,
  "sym": "AAPL",
  "t": 1610144700000000000
}
```

## Aggregates (Per Minute)

### WebSocket Connection
- **Endpoint**: `wss://socket.polygon.io/stocks`
- **Access Level**: Real-Time subscription
- **Description**: Stream minute-by-minute aggregated OHLC and volume data covering pre-market, regular, and after-hours sessions

### Use Cases
- Real-time monitoring
- Dynamic charting
- Intraday strategy development
- Automated trading

### Subscription Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | string | Yes | Stock ticker symbol, `*` for all tickers, or comma-separated list |

### Response Attributes
| Field | Type | Description |
|-------|------|-------------|
| ev | enum | Event type: "AM" |
| sym | string | Ticker symbol |
| v | integer | Tick volume |
| av | integer | Today's accumulated volume |
| op | number | Today's official opening price |
| vw | number | Tick's volume weighted average price |
| o | number | Opening price for this aggregate window |
| c | number | Closing price for this aggregate window |
| h | number | Highest price for this aggregate window |
| l | number | Lowest price for this aggregate window |
| a | number | Today's volume weighted average price |
| z | integer | Average trade size for this aggregate window |
| s | integer | Start timestamp (Unix milliseconds) |
| e | integer | End timestamp (Unix milliseconds) |
| otc | boolean | Whether ticker is OTC (omitted if false) |

### Sample Per-Minute Aggregate Response
```json
{
  "ev": "AM",
  "sym": "GTE", 
  "v": 4110,
  "av": 9470157,
  "op": 0.4372,
  "vw": 0.4488,
  "o": 0.4488,
  "c": 0.4486,
  "h": 0.4489,
  "l": 0.4486,
  "a": 0.4352,
  "z": 685,
  "s": 1610144640000,
  "e": 1610144700000
}
```

## Market Hours and Timezone

All stock market data follows standard U.S. equity trading sessions in Eastern Time (ET):

| Session | Time Range (ET) |
|---------|-----------------|
| Pre-Market | 4:00 AM - 9:30 AM |
| Regular Market | 9:30 AM - 4:00 PM |
| After-Hours | 4:00 PM - 8:00 PM |

### Important Timestamp Notes
- All timestamps are Unix timestamps (seconds since epoch, UTC)
- When converting to human-readable format, timestamps represent UTC time, not ET
- Must explicitly convert from UTC to ET for market hour alignment
- Per-minute aggregates use Unix milliseconds for start/end timestamps

## Available WebSocket Feeds for Stocks

### Core Data Streams
1. **Aggregates (Per Minute)**: OHLC bars updated every minute
2. **Aggregates (Per Second)**: Second-by-second OHLC bars for ultra-fine analysis
3. **Trades**: Every executed trade in real-time with price, size, exchange, conditions
4. **Quotes**: NBBO (National Best Bid and Offer) quotes as they update
5. **Limit Up - Limit Down (LULD)**: Real-time volatility safeguards and price bands
6. **Fair Market Value (FMV)**: Proprietary real-time FMV metric (Business plan only)

### Infrastructure and Reliability
- Co-located servers with exchanges and Securities Information Processors (SIPs)
- Redundant data centers and load balancing
- Direct connections to all major U.S. stock exchanges
- SIP-consolidated feeds for comprehensive market data
- Near-instantaneous delivery for real-time decision-making

## Subscription Message Formats

### Per-Second Aggregates (Current Implementation)
```json
{
  "action": "subscribe",
  "params": "A.AAPL,A.MSFT,A.TSLA"
}
```

### Per-Minute Aggregates (New for Sprint 101)
```json
{
  "action": "subscribe", 
  "params": "AM.AAPL,AM.MSFT,AM.TSLA"
}
```

### Fair Market Value (New for Sprint 101)
```json
{
  "action": "subscribe",
  "params": "FMV.AAPL,FMV.MSFT,FMV.TSLA"
}
```

### Multi-Frequency Subscription (Sprint 101 Goal)
```json
{
  "action": "subscribe",
  "params": "A.AAPL,AM.AAPL,FMV.AAPL,A.MSFT,AM.MSFT"
}
```

## Authentication Requirements

### Standard WebSocket (Per-Second, Per-Minute Aggregates)
- Standard Polygon API key
- Basic subscription level required

### Business WebSocket (Fair Market Value)
- Business plan subscription required
- Enhanced API key with FMV access
- Connection to `wss://business.polygon.io/stocks`

## Event Type Mapping for TickStock

| Polygon Event | TickStock Event Type | Handler Method | Description |
|---------------|---------------------|----------------|-------------|
| T | Trade | `handle_tick` | Individual trade events |
| A | PerSecondAggregate | `handle_tick` | Second-level OHLCV bars (current) |
| AM | PerMinuteAggregate | `handle_minute_bar` | Minute-level OHLCV bars (Sprint 101) |
| FMV | FairMarketValue | `handle_fmv` | Fair market value updates (Sprint 101) |
| Q | Quote | `handle_tick` | NBBO quote updates |

## Rate Limiting and Connection Limits

### WebSocket Connections
- Maximum concurrent connections per API key
- Rate limiting on subscription requests
- Connection pooling recommendations for multiple frequencies

### Subscription Limits
- Maximum tickers per subscription message
- Recommended batch sizes for large ticker lists
- Throttling strategies for high-volume subscriptions

## Error Handling and Status Messages

### Common Status Messages
```json
{
  "ev": "status",
  "status": "auth_success",
  "message": "authenticated"
}
```

### Error Response Format
```json
{
  "ev": "status", 
  "status": "error",
  "message": "error description"
}
```

### Connection Health
- Heartbeat/ping mechanisms
- Reconnection strategies for dropped connections
- Status monitoring for stream health

## Implementation Notes for TickStock

### Sprint 101 Integration Points
1. **PolygonWebSocketClient Enhancement**: Support multiple event types (A, AM, FMV)
2. **Event Processing**: Route different event types to appropriate handlers
3. **Data Publisher Integration**: Separate buffers for each frequency type
4. **Authentication Handling**: Business plan credentials for FMV access

### Sprint 102 Synthetic Data Simulation
1. **AM Event Simulation**: Generate realistic per-minute OHLCV data
2. **FMV Event Simulation**: Create correlated fair market value updates
3. **Timing Accuracy**: Respect market session schedules and realistic update frequencies
4. **Mathematical Consistency**: Ensure minute aggregates align with underlying tick data

### Configuration Integration (Sprint 100 Foundation)
1. **Multi-Frequency Subscription Config**: JSON structure for different frequency combinations
2. **Authentication Configuration**: Business plan credentials management
3. **Rate Limiting Configuration**: Throttling and connection management settings
4. **Fallback Configuration**: Graceful degradation when Business plan features unavailable