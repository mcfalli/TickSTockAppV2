# TickStockPL Streaming WebSocket Connection Failure

**Issue ID**: Sprint 40 - TickStockPL WebSocket Conflict
**Date**: October 7, 2025
**Priority**: HIGH - Blocking Live Streaming functionality
**Status**: Requires TickStockPL Developer Action

---

## Executive Summary

TickStockPL Streaming service cannot establish WebSocket connection to Massive API due to **concurrent connection conflict** with TickStockAppV2. Both applications are attempting to use the same Massive API key, but Massive allows only **ONE WebSocket connection per API key**.

---

## Error Details

### Location
- **File**: `C:\Users\McDude\TickStockPL\src\services\streaming_scheduler.py`
- **Session ID**: `67702537-3112-4c19-a3ad-f75eb7e5ba13`
- **Timestamp**: October 7, 2025, 08:43:18 ET

### Error Log (from temp_log.log)

```
Line 485: [TickStockPL Streaming] Market is currently open - starting streaming immediately
Line 492: [TickStockPL Streaming] Starting streaming session 67702537-3112-4c19-a3ad-f75eb7e5ba13
Line 496: [TickStockPL Streaming] Symbol cache loaded: 59 lists, 849 total symbols ✅
Line 498: [TickStockPL Streaming] Loaded 60 symbols from universe key: market_leaders:top_500 ✅
Line 502: [TickStockPL Streaming] DatabaseWebSocketHandler initialized with 60 symbols ✅
Line 504: [TickStockPL Streaming] Starting database-driven WebSocket handler
Line 506: [TickStockPL Streaming] Starting connection manager
Line 507: [TickStockPL Streaming] ERROR - Failed to establish WebSocket connection ❌
Line 508: [TickStockPL Streaming] ERROR - Failed to start WebSocket streaming ❌
Line 510: [TickStockPL Streaming] Stopping streaming session (market_close)
```

### Comparison: TickStockAppV2 (Working)

```
Line 295: [TickStockAppV2] MASSIVE-CLIENT: WebSocket opened, sending authentication
Line 297: [TickStockAppV2] MASSIVE-CLIENT: Authentication confirmed - connection established ✅
Line 299: [TickStockAppV2] MASSIVE-CLIENT: Subscribing to 70 tickers
Line 303: [TickStockAppV2] MASSIVE-CLIENT: All 70 ticker subscriptions confirmed ✅
Line 304-313: [TickStockAppV2] Processing ticks successfully ✅
```

---

## Root Cause Analysis

### The Conflict

Both TickStockPL and TickStockAppV2 are attempting to establish **separate WebSocket connections** to Massive:

| Application | Purpose | Connection Target | Status |
|-------------|---------|-------------------|--------|
| **TickStockAppV2** | Real-time UI updates (70 symbols) | `wss://socket.massive.com/stocks` | ✅ Connected |
| **TickStockPL** | Pattern/indicator detection (60 symbols) | `wss://socket.massive.com` | ❌ Failed |

### Massive API Limitation

**Massive.com WebSocket API allows only ONE concurrent connection per API key.**

When TickStockPL attempts to connect:
1. TickStockAppV2 already holds the active WebSocket connection
2. Massive API rejects TickStockPL's connection request
3. TickStockPL streaming service fails and shuts down immediately

### Architecture Impact

This violates the intended **loose coupling architecture**:
- TickStockPL should be the **producer** (data collection + processing)
- TickStockAppV2 should be the **consumer** (UI display only)
- Current setup has TickStockAppV2 connecting directly to Massive (tight coupling)

---

## Solution: Redis Data Forwarding Architecture

### Recommended Approach

**TickStockAppV2 should forward Massive data to TickStockPL via Redis**, not connect to Massive independently.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Massive.com                            │
│              wss://socket.massive.com                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ WebSocket (ONE connection)
                     ▼
        ┌────────────────────────────┐
        │    TickStockAppV2          │
        │  (Massive Client Only)     │
        │                            │
        │  - Connect to Massive      │
        │  - Receive tick data       │
        │  - Forward to Redis        │
        └────────────┬───────────────┘
                     │
                     │ Redis Publish
                     │ Channel: tickstock:market:ticks
                     ▼
        ┌────────────────────────────┐
        │         Redis              │
        │   (Message Broker)         │
        └────────────┬───────────────┘
                     │
                     │ Redis Subscribe
                     ▼
        ┌────────────────────────────┐
        │      TickStockPL           │
        │  (Pattern Detection)       │
        │                            │
        │  - Subscribe to Redis      │
        │  - Detect patterns         │
        │  - Calculate indicators    │
        │  - Publish results         │
        └────────────┬───────────────┘
                     │
                     │ Redis Publish
                     │ Channels: tickstock:patterns:*
                     │          tickstock:indicators:*
                     ▼
        ┌────────────────────────────┐
        │    TickStockAppV2          │
        │  (UI/WebSocket Broadcast)  │
        │                            │
        │  - Subscribe to patterns   │
        │  - Broadcast to browsers   │
        │  - Update Live Streaming   │
        └────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: TickStockAppV2 Changes (Consumer → Forwarder)

**File**: `src/core/services/market_data_service.py`

**Current** (lines 304-313):
```python
# Processes ticks for internal use only
def _on_tick(self, tick_data):
    logger.info(f"MARKET-DATA-SERVICE: Processed tick #{self.tick_count}: {symbol} @ ${price}")
    # Internal processing only
```

**New** (Forward to Redis):
```python
def _on_tick(self, tick_data):
    """Forward tick data to TickStockPL via Redis"""
    try:
        # Publish to Redis for TickStockPL consumption
        redis_event = {
            'type': 'market_tick',
            'symbol': tick_data['symbol'],
            'price': tick_data['price'],
            'volume': tick_data.get('volume', 0),
            'timestamp': tick_data['timestamp'],
            'source': 'massive'
        }

        self.redis_client.publish(
            'tickstock:market:ticks',
            json.dumps(redis_event)
        )

        self.tick_count += 1
        if self.tick_count % 100 == 0:
            logger.info(f"MARKET-DATA-SERVICE: Forwarded {self.tick_count} ticks to TickStockPL")

    except Exception as e:
        logger.error(f"MARKET-DATA-SERVICE: Failed to forward tick: {e}")
```

**Configuration** (`.env`):
```ini
# Redis channel for market tick forwarding
REDIS_MARKET_TICK_CHANNEL=tickstock:market:ticks
```

---

### Phase 2: TickStockPL Changes (WebSocket → Redis Subscriber)

**File**: `src/services/streaming_scheduler.py`

**Current** (lines 500-507):
```python
# Attempts WebSocket connection to Massive (FAILS)
self.connection_manager = ConnectionManager(polygon_url)
self.websocket_handler = DatabaseWebSocketHandler(symbols)
self.connection_manager.start()  # ERROR: Connection conflict
```

**New** (Subscribe to Redis):
```python
# Subscribe to Redis channel for market ticks
class RedisTickSubscriber:
    def __init__(self, redis_client, channel='tickstock:market:ticks'):
        self.redis_client = redis_client
        self.channel = channel
        self.pubsub = redis_client.pubsub()

    async def start(self):
        """Start subscribing to market ticks from TickStockAppV2"""
        self.pubsub.subscribe(self.channel)
        logger.info(f"STREAMING: Subscribed to {self.channel}")

        for message in self.pubsub.listen():
            if message['type'] == 'message':
                tick_data = json.loads(message['data'])
                await self._process_tick(tick_data)

    async def _process_tick(self, tick_data):
        """Process tick data (same logic as WebSocket handler)"""
        symbol = tick_data['symbol']
        price = tick_data['price']

        # Run pattern detection
        patterns = await self.pattern_detector.detect(symbol, price, tick_data)

        # Run indicator calculation
        indicators = await self.indicator_calculator.calculate(symbol, price, tick_data)

        # Publish results back to Redis
        if patterns:
            self.redis_client.publish('tickstock:patterns:streaming', json.dumps(patterns))
        if indicators:
            self.redis_client.publish('tickstock:indicators:streaming', json.dumps(indicators))
```

**Update streaming scheduler**:
```python
def _start_streaming(self, session_id):
    """Start streaming session using Redis data feed"""
    logger.info(f"Starting streaming session {session_id}")

    # Initialize components
    self.persistence_manager = StreamingPersistenceManager(...)
    self.health_monitor = StreamingHealthMonitor(...)

    # Load symbols from universe
    symbols = self._load_universe_symbols()

    # Initialize Redis tick subscriber (replaces WebSocket handler)
    self.tick_subscriber = RedisTickSubscriber(
        redis_client=self.redis_client,
        channel='tickstock:market:ticks'
    )

    # Start subscriber loop
    asyncio.create_task(self.tick_subscriber.start())

    logger.info(f"STREAMING: Started Redis tick subscriber for {len(symbols)} symbols")
```

---

### Phase 3: Configuration Updates

**TickStockAppV2 `.env`**:
```ini
# Massive API (TickStockAppV2 connects)
MASSIVE_API_KEY=your_api_key_here

# Redis forwarding
REDIS_MARKET_TICK_CHANNEL=tickstock:market:ticks
MARKET_TICK_FORWARD_ENABLED=true
```

**TickStockPL `.env`**:
```ini
# Massive API key NOT needed (consumes from Redis)
# MASSIVE_API_KEY=  # REMOVE or comment out

# Redis subscription
REDIS_MARKET_TICK_CHANNEL=tickstock:market:ticks
MARKET_TICK_SOURCE=redis  # Options: redis, websocket
```

---

## Benefits of This Solution

### 1. **Resolves Connection Conflict** ✅
- Only ONE Massive WebSocket connection (TickStockAppV2)
- TickStockPL receives data via Redis (no conflict)

### 2. **Proper Architecture** ✅
- TickStockAppV2: Data collection + UI
- TickStockPL: Data processing + pattern detection
- Redis: Message broker (loose coupling)

### 3. **Scalability** ✅
- Can add more consumers without additional Massive connections
- Redis can handle high-throughput message delivery
- Pattern detection can scale independently

### 4. **Cost Efficiency** ✅
- No need for multiple Massive API subscriptions
- Single WebSocket connection handles all symbols
- Reduced API rate limit concerns

### 5. **Reliability** ✅
- Redis message buffering prevents data loss
- If TickStockPL crashes, TickStockAppV2 continues
- Easier to debug (single data source)

---

## Testing Plan

### Step 1: Verify Current State

```bash
# Check Massive connections
redis-cli PUBSUB CHANNELS "tickstock:market:*"

# Expected: No market tick channel (not yet implemented)
```

### Step 2: Implement TickStockAppV2 Forwarding

1. Update `market_data_service.py` with Redis forwarding
2. Restart TickStockAppV2
3. Verify ticks publishing to Redis:

```bash
redis-cli SUBSCRIBE tickstock:market:ticks
```

**Expected Output**:
```
1) "message"
2) "tickstock:market:ticks"
3) "{\"type\":\"market_tick\",\"symbol\":\"AAPL\",\"price\":257.01,...}"
```

### Step 3: Implement TickStockPL Redis Subscriber

1. Update `streaming_scheduler.py` with Redis subscriber
2. Remove/comment out WebSocket connection code
3. Restart TickStockPL Streaming

### Step 4: End-to-End Verification

1. Open Live Streaming dashboard in browser
2. Verify TickStockAppV2 forwarding ticks to Redis
3. Verify TickStockPL consuming ticks from Redis
4. Verify patterns/indicators appearing in dashboard
5. Check database persistence (intraday_patterns, intraday_indicators)

---

## Alternative Solutions (Not Recommended)

### ❌ Alternative 1: Separate Massive API Keys

**Cost**: Requires purchasing additional Massive subscription
**Complexity**: Managing multiple API keys
**Architecture**: Violates loose coupling principle

### ❌ Alternative 2: Disable TickStockAppV2 Massive Connection

**Problem**: TickStockAppV2 loses real-time market data
**Impact**: UI cannot display live prices
**Not sustainable**: Defeats purpose of real-time application

### ❌ Alternative 3: Share WebSocket Connection

**Technical Challenge**: Complex state management
**Failure Mode**: Single point of failure
**Not recommended**: Tight coupling between applications

---

## Implementation Timeline

| Phase | Task | Estimated Time | Owner |
|-------|------|----------------|-------|
| 1 | TickStockAppV2 Redis forwarding | 2 hours | TickStockAppV2 Developer |
| 2 | TickStockPL Redis subscriber | 3 hours | TickStockPL Developer |
| 3 | Testing & validation | 2 hours | Both teams |
| 4 | Production deployment | 1 hour | Both teams |

**Total**: 8 hours (~1 business day)

---

## Success Criteria

- [ ] TickStockAppV2 successfully forwards ticks to Redis channel
- [ ] TickStockPL successfully subscribes to Redis channel
- [ ] No WebSocket connection conflicts
- [ ] Live Streaming dashboard displays real-time patterns/indicators
- [ ] Database tables populate correctly (intraday_patterns, intraday_indicators)
- [ ] Performance meets targets (<100ms latency end-to-end)
- [ ] System runs stable for full market session (6.5 hours)

---

## Files to Modify

### TickStockAppV2

1. `src/core/services/market_data_service.py` - Add Redis forwarding
2. `.env` - Add Redis channel configuration
3. `config/app_config.py` - Add forwarding config settings

### TickStockPL

1. `src/services/streaming_scheduler.py` - Replace WebSocket with Redis subscriber
2. `src/streaming/redis_tick_subscriber.py` - New file for Redis subscription
3. `.env` - Remove/comment Massive API key, add Redis config
4. `config/tickstockpl_config_manager.py` - Add Redis subscriber config

---

## Contact Information

**Issue Reporter**: Claude (TickStockAppV2 Developer Assistant)
**TickStockPL Developer**: [Awaiting contact details]
**Sprint**: Sprint 40 - Live Streaming Verification
**Documentation**: `docs/planning/sprints/sprint40/`

---

## Related Documentation

- **Sprint 40 Plan**: `docs/planning/sprints/sprint40/SPRINT40_PLAN.md`
- **Phase 1 Fixes**: `docs/planning/sprints/sprint40/PHASE1_FIXES_APPLIED.md`
- **TickStockPL Verification**: `C:\Users\McDude\TickStockPL\docs\planning\sprints\sprint40\SPRINT33_VERIFICATION_REPORT.md`
- **WebSocket Architecture**: `docs/architecture/websockets-integration.md`

---

**Status**: Ready for TickStockPL Developer Implementation
**Priority**: HIGH - Required for Sprint 40 completion
**Next Action**: Share this report with TickStockPL developer

---

**Generated**: October 7, 2025, 08:45 AM ET
**Sprint 40**: Live Streaming Dashboard Verification
