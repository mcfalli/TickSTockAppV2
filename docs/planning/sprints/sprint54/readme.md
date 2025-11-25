# Sprint54
Regarding the realtime_adapter.py RealTimeDataAdapter.  We are in single connection mode.  The following mermaid flow depicts current state.  

flowchart TD
    Start([Application Startup]) --> Init[MarketDataService.__init__]

    Init --> CreateAdapter[Create RealTimeDataAdapter]
    CreateAdapter --> CheckMode{USE_MULTI_CONNECTION?}

    CheckMode -->|false| CreateSingle[Create MassiveWebSocketClient]
    CreateSingle --> Ready[Adapter Ready]

    Ready --> ServiceLoop[MarketDataService._service_loop]
    ServiceLoop --> GetUniverse[_get_universe]

    GetUniverse --> LoadKey[Read SYMBOL_UNIVERSE_KEY<br/>from .env]
    LoadKey --> CacheControl[CacheControl.get_universe_tickers<br/>universe_key]
    CacheControl --> DBQuery[(Query cache_entries table)]
    DBQuery --> TickerList[Return ticker list<br/>e.g., 70 tickers]

    TickerList --> Connect[adapter.connect universe]
    Connect --> ClientConnect[MassiveWebSocketClient.connect]

    ClientConnect --> WSApp[Create WebSocketApp<br/>wss://socket.massive.com/stocks]
    WSApp --> Thread[Start daemon thread<br/>ws.run_forever]

    Thread --> OnOpen[WebSocket _on_open callback]
    OnOpen --> SendAuth[Send auth message<br/>action: auth, params: API_KEY]

    SendAuth --> OnMsg1[WebSocket _on_message callback]
    OnMsg1 --> CheckAuth{Auth successful?}
    CheckAuth -->|Yes| Subscribe[client.subscribe tickers]
    CheckAuth -->|No| AuthFail[Log error & timeout]

    Subscribe --> SendSub[Send subscribe message<br/>action: subscribe<br/>params: A.AAPL,A.NVDA,...]
    SendSub --> Listening[WebSocket listening for data]

    Listening --> TickReceived[Massive API sends tick data]
    TickReceived --> OnMsg2[WebSocket _on_message callback]

    OnMsg2 --> ParseJSON[Parse JSON message]
    ParseJSON --> CheckType{Message type?}

    CheckType -->|A event| ParseTick[Parse per-second aggregate<br/>sym, o, h, l, c, v, t]
    CheckType -->|status| LogStatus[Log status message]
    CheckType -->|Other| LogOther[Log unknown type]

    ParseTick --> CreateTickData[Create TickData object<br/>ticker, price, volume, timestamp]
    CreateTickData --> Callback[Call on_tick_callback<br/>MarketDataService._handle_tick_data]

    Callback --> UpdateStats[Update service stats<br/>ticks_processed++]
    UpdateStats --> FallbackDetector[Feed to fallback_pattern_detector<br/>if active]

    FallbackDetector --> PublishWS[DataPublisher.publish_tick_data<br/>WebSocket to browsers]
    PublishWS --> WSClients[Connected browser clients<br/>receive real-time updates]

    PublishWS --> PublishRedis1[Publish to Redis<br/>tickstock.data.raw]
    PublishRedis1 --> PublishRedis2[Publish to Redis<br/>tickstock:market:ticks]

    PublishRedis2 --> TickStockPL[TickStockPL consumes<br/>for OHLCV aggregation]

    TickStockPL --> PatternDetection[Pattern detection &<br/>indicator calculation]
    PatternDetection --> RedisEvents[Publish events to Redis<br/>tickstock.events.patterns]

    RedisEvents --> AppConsumes[TickStockAppV2 consumes<br/>pattern events]

    LogStatus --> Listening
    LogOther --> Listening
    WSClients --> Listening

    style Start fill:#e1f5ff
    style CreateSingle fill:#ffe1e1
    style TickerList fill:#e1ffe1
    style WSApp fill:#fff4e1
    style Listening fill:#f0e1ff
    style CreateTickData fill:#e1ffe1
    style PublishWS fill:#ffe1f5
    style TickStockPL fill:#e1f5ff
    

We will alter the flow from "Parse per-second aggregate<br/>sym, o, h, l, c, v, t]" forward in how we process incoming stocks and ETFs from websockets connection.

1. OHLCV to database.  Incoming websockets is on the 1 minute timeframe.  Log to ohlcv_1min.  

Remove the tickstockPL integration and publishing to redis and remaining steps.  

In summary, the only action on incoming websockets will be to log to database.  