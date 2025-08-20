Hierarchical Call Stack - Tick Data Flow to Event Detector

  1. Data Source Layer

  File: src/infrastructure/data_sources/adapters/realtime_adapter.py
  - Classes: RealTimeDataAdapter, SyntheticDataAdapter
  - Method: connect() → establishes WebSocket connection or starts synthetic data generation
  - Method: _simulate_events() (synthetic) → generates TickData objects
  - Callback: Calls tick_callback (which is handle_websocket_tick)

  2. Core Service Layer

  File: src/core/services/market_data_service.py
  - Class: MarketDataService
  - Method: handle_websocket_tick(tick_data: TickData) ← Entry point from data source
    - Validates tick data
    - Updates market session if needed
    - Delegates to EventProcessor

  3. Event Processing Pipeline

  File: src/processing/pipeline/event_processor.py
  - Class: EventProcessor
  - Method: handle_tick(tick_data: TickData) ← Called from MarketDataService
    - Validates TickData
    - Calls TickProcessor for validation/enrichment
    - Calls _process_tick_event() for main processing

  Method: _process_tick_event(queue_data: TickData)
  - Checks if ticker is in core universe
  - Gets/creates StockData for ticker
  - Calls EventDetector for event detection

  4. Event Detection Coordinator

  File: src/processing/pipeline/event_detector.py
  - Class: EventDetector
  - Method: detect_events(ticker, tick_data, stock_details) ← Called from EventProcessor
    - Coordinates all event detection types
    - Calls individual detector methods:
        - _detect_highlow_events()
      - _detect_trend_events()
      - _detect_surge_events()

  5. Individual Event Detectors

  File: src/processing/detectors/highlow_detector.py
  - Class: HighLowDetector
  - Method: detect_highlow(tick_data: TickData, stock_data: StockData) ← Final detection logic
    - Performs actual high/low event detection
    - Creates HighLowEvent objects
    - Returns detection results

  Summary Lists

  File Hierarchy (Start → Finish)

  1. src/infrastructure/data_sources/adapters/realtime_adapter.py
  2. src/core/services/market_data_service.py
  3. src/processing/pipeline/event_processor.py
  4. src/processing/pipeline/event_detector.py
  5. src/processing/detectors/highlow_detector.py

  Method Call Chain

  1. RealTimeDataAdapter.connect() / SyntheticDataAdapter._simulate_events()
  2. MarketDataService.handle_websocket_tick()
  3. EventProcessor.handle_tick()
  4. EventProcessor._process_tick_event()
  5. EventDetector.detect_events()
  6. EventDetector._detect_highlow_events()
  7. HighLowDetector.detect_highlow()

  Key Data Flow Points

  - Data Source: TickData objects created from WebSocket or synthetic data
  - Entry Point: MarketDataService.handle_websocket_tick()
  - Processing Hub: EventProcessor._process_tick_event()
  - Detection Coordinator: EventDetector.detect_events()
  - Final Detection: HighLowDetector.detect_highlow() (and similar for trend/surge)

  The flow follows a clean pipeline architecture where each layer has specific responsibilities, from data ingestion through processing coordination to final event detection.