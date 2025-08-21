# Sprint 106 Tasks: Data Type Handlers

## Relevant Files

- `src/processing/channels/tick_channel.py` - New TickChannel implementation extending ProcessingChannel
- `src/processing/channels/ohlcv_channel.py` - New OHLCVChannel implementation for aggregate processing
- `src/processing/channels/fmv_channel.py` - New FMVChannel implementation for fair market value
- `src/shared/models/data_types.py` - New data models for OHLCVData and FMVData
- `src/processing/channels/event_creators.py` - New channel-specific event creation logic
- `tests/unit/processing/channels/test_tick_channel.py` - Unit tests for TickChannel processing
- `tests/unit/processing/channels/test_ohlcv_channel.py` - Unit tests for OHLCVChannel batching
- `tests/unit/processing/channels/test_fmv_channel.py` - Unit tests for FMVChannel filtering
- `tests/unit/shared/models/test_data_types.py` - Unit tests for new data models
- `tests/integration/channels/test_channel_event_creation.py` - Integration tests for event compatibility

### Notes

- All channels extend the ProcessingChannel base class from Sprint 105
- Data models must be compatible with existing TickData structure
- Event formats must maintain compatibility with existing WebSocket publisher
- Channel-specific processing must integrate with existing event detection logic

## Tasks

- [ ] 1.0 Implement Data Type Models
  - [ ] 1.1 Create OHLCVData model with open, high, low, close, volume, percent_change fields
  - [ ] 1.2 Create FMVData model with fmv, market_price, confidence, deviation fields
  - [ ] 1.3 Implement serialization and deserialization methods for WebSocket transport
  - [ ] 1.4 Add data validation and type checking for all model fields
  - [ ] 1.5 Create model compatibility interfaces with existing TickData structure
- [ ] 2.0 Implement TickChannel for Real-Time Processing
  - [ ] 2.1 Extend ProcessingChannel for immediate tick data processing
  - [ ] 2.2 Implement real-time processing with no batching delays (batch_size=1)
  - [ ] 2.3 Connect with existing event detection logic for tick-based events
  - [ ] 2.4 Implement high-priority routing with minimal latency requirements
  - [ ] 2.5 Add TickChannel-specific metrics and performance tracking
- [ ] 3.0 Implement OHLCVChannel for Aggregate Processing
  - [ ] 3.1 Extend ProcessingChannel for OHLCV batch processing
  - [ ] 3.2 Implement configurable batch processing (default: batch_size=100, timeout=100ms)
  - [ ] 3.3 Create symbol-based buffering for multi-period analysis
  - [ ] 3.4 Implement OHLCV-specific event detection (high/low closes, volume surges)
  - [ ] 3.5 Add aggregate-specific metrics and buffer management
- [ ] 4.0 Implement FMVChannel for Valuation Processing
  - [ ] 4.1 Extend ProcessingChannel for fair market value processing
  - [ ] 4.2 Implement confidence-based filtering (minimum threshold: 0.8)
  - [ ] 4.3 Create deviation detection logic (default threshold: 1.0% deviation)
  - [ ] 4.4 Implement batch processing for efficiency (default batch_size: 50)
  - [ ] 4.5 Add valuation-specific metrics and confidence tracking
- [ ] 5.0 Implement Channel-Specific Event Creation
  - [ ] 5.1 Create channel-specific event creation methods for each data type
  - [ ] 5.2 Implement to_transport_dict() methods for all new event types
  - [ ] 5.3 Ensure event formats are compatible with existing WebSocket publisher
  - [ ] 5.4 Implement event ID generation and deduplication logic
  - [ ] 5.5 Add source identification metadata to all generated events
- [ ] 6.0 Create Comprehensive Test Suite
  - [ ] 6.1 Write unit tests for all data type models with validation scenarios
  - [ ] 6.2 Create unit tests for TickChannel immediate processing and latency
  - [ ] 6.3 Implement unit tests for OHLCVChannel batching and symbol buffering
  - [ ] 6.4 Write unit tests for FMVChannel filtering and deviation detection
  - [ ] 6.5 Create integration tests for event format compatibility with existing systems