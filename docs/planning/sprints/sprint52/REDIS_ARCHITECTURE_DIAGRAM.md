# Redis Pub-Sub Architecture Diagrams

## 1. System-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         TickStock System Architecture                    │
└──────────────────────────────────────────────────────────────────────────┘

                              TickStockPL
                        (Pattern Detection System)
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              Patterns       Backtests        Health
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                                  │ Publish
                                  │ Events
                                  │
                    ┌─────────────▼─────────────┐
                    │    Redis Server 6379      │
                    │                           │
                    │  Pub-Sub Channels:       │
                    │  - tickstock:*:*         │
                    │  - tickstock.events.*    │
                    │  - tickstock.health.*    │
                    │  - tickstock.market.*    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┼──────────────────┐
                    │             │                  │
                Subscribe        │              Channels
                    │             │                  │
        ┌───────────▼───────────┐ │ ┌────────────────▼──────────┐
        │ TickStockAppV2        │ │ │ Event Types:              │
        │ (Flask App)           │ │ │ - PATTERN_DETECTED        │
        │                       │ │ │ - BACKTEST_PROGRESS       │
        │ Subscribers:          │ │ │ - STREAMING_PATTERN       │
        │ ├ RedisEventSub       │ │ │ - STREAMING_INDICATOR     │
        │ ├ MarketDataSub       │ │ │ - INDICATOR_ALERT         │
        │ ├ MonitoringSub       │ │ │ - CRITICAL_ALERT          │
        │ └ ErrorSubscriber     │ │ └──────────────────────────┘
        │                       │ │
        │ Flask-SocketIO        │ │
        │ (WebSocket Server)    │ │
        └───────────┬───────────┘ │
                    │             │
                    │ Emit        │
                    │ Events      │
                    │             │
            ┌───────▼──────────────▼──────┐
            │  Browser Clients             │
            │  (Real-time Dashboard)       │
            │  - Live Pattern Updates      │
            │  - Streaming Indicators      │
            │  - System Health Monitor     │
            │  - Backtest Progress        │
            └──────────────────────────────┘
```

---

## 2. Redis Event Subscription Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              Redis Event Subscriber Initialization                  │
└─────────────────────────────────────────────────────────────────────┘

                    RedisEventSubscriber.__init__()
                              │
                ┌─────────────┼─────────────┐
                │             │             │
         Store Redis       Store SocketIO   Store Config
         Client Instance   Instance         (Backtest Manager, etc)
                │             │             │
                └─────────────┼─────────────┘
                              │
                    Initialize 16 Event Types
                              │
                ┌─────────────▼─────────────┐
                │  self.channels = {        │
                │   'channel_name': enum    │
                │   ...                     │
                │  }                        │
                └─────────────┬─────────────┘
                              │
                              │ Call start()
                              │
                    ┌─────────▼────────┐
                    │ _test_redis_conn │
                    └─────────┬────────┘
                              │
                    ┌─────────▼────────────────┐
                    │ self.pubsub =            │
                    │ redis.pubsub()           │
                    └─────────┬────────────────┘
                              │
                    ┌─────────▼─────────────────────────┐
                    │ pubsub.subscribe(channel_list)    │
                    │ Subscribe to 16 channels at once  │
                    └─────────┬─────────────────────────┘
                              │
                    ┌─────────▼────────────────────────┐
                    │ Start subscriber_thread (daemon) │
                    │ Target: _subscriber_loop()       │
                    └─────────┬────────────────────────┘
                              │
                    Service Now Ready for Events
```

---

## 3. Message Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    Main Subscriber Loop                          │
│              (Running in background thread)                      │
└──────────────────────────────────────────────────────────────────┘

                while self.is_running:
                         │
              ┌──────────▼──────────┐
              │ pubsub.get_message  │
              │ (timeout=1.0s)      │
              └──────────┬──────────┘
                         │
                    [Receive Redis Message]
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    │              message == None     type ∈ ['subscribe', 'unsubscribe']
    │                    │                    │
    │              [continue]          [log subscription]
    │                    │                    │
    │                    │              [continue]
    │                    │                    │
    └────────────────────┼────────────────────┘
                         │
                  message['type'] == 'message'
                         │
              ┌──────────▼──────────────┐
              │ _process_message()      │
              │ (Parse JSON, extract)   │
              └──────────┬──────────────┘
                         │
              ┌──────────▼──────────────────┐
              │ 1. Decode bytes → UTF-8    │
              │ 2. Parse JSON             │
              │ 3. Extract channel        │
              │ 4. Map to EventType       │
              │ 5. Create TickStockEvent  │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────┐
              │ _handle_event()         │
              │ (Dispatch by type)      │
              └──────────┬──────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    PATTERN_DETECTED  STREAMING_PATTERN  BACKTEST_*
        │                │                │
        ▼                ▼                ▼
   _handle_pattern  _handle_streaming  _handle_backtest
        │              _pattern            │
        │                │                 │
        ├─ Extract data  ├─ Add to      ├─ Emit to all
        ├─ Filter users  │   buffer       users
        ├─ Emit to       │                │
        │   user_rooms   │             [continue]
        │                │
        └─ Update stats  │
                         │
                    (buffering
                     enabled)
                         │
              ┌──────────▼──────────────┐
              │ streaming_buffer.emit() │
              │ OR socketio.emit()      │
              └──────────┬──────────────┘
                         │
                   [Browser receives]
```

---

## 4. Event Handler Routing

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Type Routing                           │
│                  (_handle_event method)                         │
└─────────────────────────────────────────────────────────────────┘

              TickStockEvent received
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    if PATTERN_*    if BACKTEST_*   if STREAMING_*
        │               │               │
        ▼               ▼               ▼
   [Pattern             [Backtest       [Streaming
    Handlers]           Handlers]       Handlers]
        │               │               │
        ├─ Pattern      ├─ Progress    ├─ Session Start
        │  Detected     │  Update      ├─ Session Stop
        └─ Pattern      ├─ Result      ├─ Health
           Alert        │  Complete    ├─ Pattern Det
                        └─ Failure     ├─ Indicator
                                       │  Calc
                                       └─ Indicator
                                          Alert
                                       └─ Critical
                                          Alert

            Also Execute:
            Custom Handlers (user-registered)
```

---

## 5. Pattern Alert Distribution

```
┌────────────────────────────────────────────────────────────────┐
│          Pattern Alert Distribution Flow                       │
│    (Filtered by User Subscriptions & Confidence)               │
└────────────────────────────────────────────────────────────────┘

Redis Message: {"pattern": "Doji", "symbol": "NVDA", "confidence": 0.95}
                             │
                    _handle_pattern_event()
                             │
              ┌──────────────┼──────────────┐
              │              │              │
          Extract        Query Database   Convert to
          Fields         (Pattern Alert    WebSocket
                         Manager)          Format
              │              │              │
              │         Get User IDs   {type: 'pattern_alert',
              │         subscribed to   event: {
              │         'Doji' with     pattern: 'Doji',
              │         min_confidence  symbol: 'NVDA',
              │         ≤ 0.95          confidence: 0.95,
              │              │          timestamp: ...
              │         [User 1, 2, 5]  }
              │              │          }
              │              │              │
              └──────────────┼──────────────┘
                             │
                    [Filter: is User online?]
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
      User 1           User 2                  User 5
    (Online)         (Offline)              (Online)
        │                 │                    │
        │            [Queue message          │
        │             to persistent           │
        │             storage]                │
        │                 │                    │
        ▼                 ▼                    ▼
    socketio.emit    [Later when          socketio.emit
    ('pattern_alert',  user logs in,       ('pattern_alert',
     room='user_1')    retrieve)            room='user_5')
        │                 │                    │
        │                 │                    │
        └─────────────────┼────────────────────┘
                          │
                    [WebSocket]
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    Browser 1        Browser 2          Browser 5
    (Real-time)      (On login)      (Real-time)
        │                 │                 │
        ▼                 ▼                 ▼
    Update UI        Retrieve &       Update UI
    Immediately      Show Alert       Immediately
```

---

## 6. Streaming Buffer Operation

```
┌────────────────────────────────────────────────────────────────┐
│              Streaming Buffer (Sprint 33)                       │
│       Smart Batching for High-Frequency Events                 │
└────────────────────────────────────────────────────────────────┘

High-Frequency Event Stream:
Pattern Doji@NVDA
Pattern Hammer@NVDA        ──┐
Pattern Engulfing@NVDA       │
Indicator RSI@NVDA=65        ├─ Buffered
Indicator MACD@NVDA=0.5      │  (250ms)
Pattern Doji@TSLA            │
Indicator Bollinger@TSLA=98──┘
                │
         [Add to buffers]
                │
    ┌───────────┼───────────┐
    │           │           │
Pattern Buffer  │      Indicator Buffer
[Doji@NVDA]     │      [RSI@NVDA]
[Hammer@NVDA]   │      [MACD@NVDA]
[Engulfing@NVDA]│      [Bollinger@TSLA]
[Doji@TSLA]     │
    │           │           │
    │      Deduplication   │
    │      (Latest value   │
    │       per symbol-    │
    │       type key)      │
    │           │           │
    └───────────┼───────────┘
                │
         [Timer: 250ms elapsed]
                │
         _flush_all()
                │
         ┌──────┴──────┐
         │             │
    Emit Batch:   Emit Batch:
    {patterns:    {indicators:
     [4 items],    [3 items],
     count: 4,     count: 3,
     timestamp}    timestamp}
         │             │
         └──────┬──────┘
                │
         Browser receives:
         - 1 batch of 4 patterns
         - 1 batch of 3 indicators
         
         Instead of 7 individual
         WebSocket events
         
    ✅ Efficiency: 57% reduction
       (7 → 2 WebSocket events)
```

---

## 7. Error Recovery Sequence

```
┌────────────────────────────────────────────────────────────────┐
│            Redis Connection Error Recovery                     │
│          Exponential Backoff with Automatic Retry             │
└────────────────────────────────────────────────────────────────┘

_subscriber_loop() running normally
            │
            │ Redis server goes down
            │
    redis.ConnectionError
            │
    _handle_connection_error()
            │
    ┌───────┴────────────────────────┐
    │                                │
Retry Attempt 1            Wait 2^0 = 1 second
    │                                │
    └───────────┬────────────────────┘
                │
        _test_redis_connection()
                │
        ┌───────┴────────┐
        │                │
     FAIL            Continue (Redis still down)
        │                │
    Retry Attempt 2  _handle_connection_error()
        │                │
   Wait 2^1 = 2s    ┌────┴─────────────────┐
        │           │                     │
        │    Wait 2^1 = 2 seconds        │
        │           │                     │
        │    _test_redis_connection()    │
        │           │                     │
        └─────┬─────┴────────┐            │
              │              │           │
           FAIL          Continue       │
              │              │           │
              │         Retry Attempt 3  │
              │              │           │
              │         Wait 2^2 = 4s   │
              │              │           │
              │         _test_redis_conn│
              │              │           │
              └──────┬───────┴──────┐   │
                     │              │   │
                  SUCCESS       FAIL    │
                     │              │   │
                     ▼              ▼   │
                  Reconnected   Give Up │
                  Resume normal  Log    │
                  operation     Error   │
```

---

## 8. Channel Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Redis Channel Organization                         │
│                (16+ Channels)                                   │
└─────────────────────────────────────────────────────────────────┘

Redis Channels by Category:

┌─ TickStockPL Events (Prod) ──────────────────┐
│ • tickstock.events.patterns                  │
│ • tickstock.events.backtesting.progress      │
│ • tickstock.events.backtesting.results       │
│ • tickstock.health.status                    │
└──────────────────────────────────────────────┘

┌─ Sprint 5 Streaming (New Format) ────────────┐
│ • tickstock:streaming:session_started        │
│ • tickstock:streaming:session_stopped        │
│ • tickstock:streaming:health                 │
│ • tickstock:patterns:streaming               │
│ • tickstock:patterns:detected (≥80% conf)    │
│ • tickstock:indicators:streaming             │
│ • tickstock:alerts:indicators (RSI/MACD)     │
│ • tickstock:alerts:critical                  │
└──────────────────────────────────────────────┘

┌─ Market Data (Optional) ─────────────────────┐
│ • tickstock.market.prices                    │
│ • tickstock.market.ohlcv                     │
│ • tickstock.market.volume                    │
│ • tickstock.market.summary                   │
│ • tickstock.market.symbols                   │
│ • tickstock.dashboard.watchlist              │
│ • tickstock.dashboard.alerts                 │
│ • tickstock.dashboard.summary                │
└──────────────────────────────────────────────┘

┌─ Cross-System (Infrastructure) ──────────────┐
│ • tickstock:monitoring (health metrics)      │
│ • tickstock:errors (TickStockPL errors)      │
└──────────────────────────────────────────────┘

┌─ Internal (Production Use) ──────────────────┐
│ • tickstock:market:ticks (raw tick data)     │
│ • tickstock:producer:heartbeat (check alive) │
└──────────────────────────────────────────────┘


Key Patterns:
• . (dot) = Old format (backward compatible)
• : (colon) = New format (Sprint 33+, preferred)
• All channels use JSON payloads
• Pub-Sub only (no persistence by default)
```

---

## 9. Complete Message Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│               Message Lifecycle Example                        │
│      Pattern Detection Event: Doji@NVDA with 0.92 confidence   │
└────────────────────────────────────────────────────────────────┘

TIME    COMPONENT                    ACTION
────────────────────────────────────────────────────────────────

T=0s    TickStockPL                  Detects Doji pattern
                                     on NVDA (confidence 0.92)

T=0.1s  TickStockPL                  Publishes to Redis:
                                     redis.publish(
                                       'tickstock:patterns:streaming',
                                       '{"pattern":"Doji",...}'
                                     )

T=0.2s  Redis Server                 Routes message to
                                     subscribed clients

T=0.3s  TickStockAppV2               Receives message in
        (subscriber thread)           pubsub.get_message()

T=0.4s  RedisEventSubscriber         Decodes bytes to UTF-8
                                     Parses JSON
                                     Creates TickStockEvent
                                     Captures in RedisMonitor

T=0.5s  RedisEventSubscriber         Calls _handle_streaming_pattern()
                                     Extracts: Doji, NVDA, 0.92

T=0.6s  RedisEventSubscriber         Routes to StreamingBuffer
                                     (if enabled)
                                     Adds to pattern_aggregator

T=0.7s  StreamingBuffer              [Waiting for flush interval]
        (background thread)           250ms buffer cycle

T=0.8s  StreamingBuffer              [Still buffering events]

T=0.95s StreamingBuffer              250ms elapsed → triggers flush

T=1.0s  StreamingBuffer              Emits batch to WebSocket:
                                     socketio.emit(
                                       'streaming_patterns_batch',
                                       {patterns: [...], count: N}
                                     )

T=1.1s  Flask-SocketIO               Routes to all connected clients

T=1.2s  Browser (JavaScript)         Receives 'streaming_patterns_batch'
                                     
                                     socket.on('streaming_patterns_batch',
                                       (batch) => {
                                         updateChart(batch.patterns[0]);
                                       }
                                     )

T=1.3s  Browser (UI)                 Updates dashboard:
                                     • Pattern indicator on chart
                                     • Alert notification
                                     • History table
                                     
                                     User sees pattern in real-time!

────────────────────────────────────────────────────────────────
Total latency: ~1.3 seconds (T=0 to T=1.3s)
  - TickStockPL processing: ~0.1s
  - Redis publish/subscribe: ~0.2s
  - TickStockAppV2 processing: ~0.4s
  - Streaming buffer wait: ~0.4s (configurable)
  - WebSocket delivery: ~0.2s
```

---

## 10. Performance Metrics Flow

```
┌────────────────────────────────────────────────────────────────┐
│              Performance Monitoring Flow                       │
└────────────────────────────────────────────────────────────────┘

RedisEventSubscriber collects stats:

Event Flow:
    Events Received
    ↓ (-parse errors)
    Events Processed
    ↓ (-filtering)
    Events Forwarded
    ↓
    Stats Updated

Runtime Metrics:
                        ┌──────────────────────┐
                        │ events_received      │
                        │ events_processed     │
                        │ events_forwarded     │
                        │ events_dropped       │
                        │ connection_errors    │
                        │ last_event_time      │
                        │ runtime_seconds      │
                        └──────────────────────┘
                              │
                    Calculations:
                              │
                  ┌───────────┼────────────┐
                  │           │            │
            events_per_sec  success_rate   uptime
                  │           │            │
           = received/       = (received-  │
             runtime         dropped)/     │
                             received      │
                  │           │            │
                  └───────────┼────────────┘
                              │
                    API: get_stats()
                    Returns dict with
                    all metrics
                              │
                    Used by:
                    • Dashboard health view
                    • Monitoring alerts
                    • Performance reports
                    • Troubleshooting
```

---

**Diagrams Version:** 1.0  
**Last Updated:** Sprint 50  
**Architecture Visualization:** Complete Redis Pub-Sub Flow

