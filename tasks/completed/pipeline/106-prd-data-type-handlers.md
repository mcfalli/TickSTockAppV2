# Sprint 106 PRD: Data Type Handlers

## Introduction/Overview

This sprint implements the data type specific channel handlers that extend the core channel infrastructure from Sprint 105. The focus is on creating specialized processing logic for Tick, OHLCV, and FMV data types, each with their own processing rules, batching strategies, and event detection patterns while maintaining compatibility with existing event detection systems.

**Problem Statement:** With the core channel infrastructure in place, we need specialized channel implementations that understand the unique characteristics and processing requirements of each data type (real-time ticks, minute aggregates, fair market values) to provide optimal processing efficiency and clear separation of concerns.

## Goals

1. **Implement TickChannel**: Create real-time tick data processing with immediate event detection
2. **Implement OHLCVChannel**: Create minute aggregate data processing with batch optimization and aggregation logic
3. **Implement FMVChannel**: Create fair market value processing with deviation detection and confidence filtering
4. **Create Data Type Models**: Implement data structures for OHLCV and FMV data types
5. **Integrate Event Detection**: Connect channel-specific processing with existing event detection logic

## User Stories

**As a Real-Time Data Processor:**
- I want a TickChannel that processes tick data immediately so high-priority events are detected with minimal latency
- I want tick processing to integrate seamlessly with existing event detection logic

**As a Market Data Analyst:**
- I want an OHLCVChannel that efficiently processes minute aggregates so I can detect longer-term patterns and trends
- I want OHLCV processing to include volume analysis and aggregate-specific event detection

**As a Valuation Specialist:**
- I want an FMVChannel that processes fair market value data so I can detect valuation discrepancies
- I want FMV processing to include confidence filtering and deviation analysis

**As a System Maintainer:**
- I want each channel to handle its data type independently so I can troubleshoot specific data streams
- I want consistent interfaces across all channels so maintenance procedures are standardized

## Functional Requirements

### 1. TickChannel Implementation
1.1. Extend `ProcessingChannel` for real-time tick data processing
1.2. Implement immediate processing (batch_size=1, no batching delays)
1.3. Connect with existing event detection logic for tick-based events
1.4. Implement high-priority routing and minimal latency processing

### 2. OHLCVChannel Implementation
2.1. Extend `ProcessingChannel` for OHLCV aggregate data processing
2.2. Implement batch processing with configurable batch sizes (default: 100)
2.3. Create symbol-based buffering for multi-period analysis
2.4. Implement OHLCV-specific event detection (high/low closes, volume surges)

### 3. FMVChannel Implementation
3.1. Extend `ProcessingChannel` for fair market value data processing
3.2. Implement confidence-based filtering (minimum threshold: 0.8)
3.3. Create deviation detection logic (default threshold: 1.0% deviation)
3.4. Implement batch processing for efficiency (default batch_size: 50)

### 4. Data Type Models
4.1. Create `OHLCVData` model with open, high, low, close, volume, percent_change fields
4.2. Create `FMVData` model with fmv, market_price, confidence, deviation fields
4.3. Ensure all models are compatible with existing `TickData` structure
4.4. Implement serialization/deserialization methods for WebSocket transport

### 5. Event Creation Logic
5.1. Implement channel-specific event creation methods
5.2. Create `to_transport_dict()` methods for all event types
5.3. Ensure event formats are compatible with existing WebSocket publisher
5.4. Implement event ID generation and deduplication logic

### 6. Channel Configuration
6.1. Define default configurations for each channel type
6.2. Implement channel-specific validation rules
6.3. Create configurable thresholds for event detection
6.4. Support runtime configuration updates for thresholds and batch sizes

## Non-Goals (Out of Scope)

- Modifications to existing event detection algorithms
- Changes to WebSocket publishing or frontend systems  
- Database schema modifications for new data types
- Integration with EventProcessor (reserved for Sprint 107)
- Performance optimization and load testing
- Production deployment configurations

## Design Specifications

### TickChannel Specification
```python
class TickChannel(ProcessingChannel):
    - Immediate processing (no batching)
    - Direct integration with existing tick-based event detection
    - High-priority processing (priority=1)
    - Real-time metrics collection
```

### OHLCVChannel Specification  
```python
class OHLCVChannel(ProcessingChannel):
    - Batch processing (batch_size=100, timeout=100ms)
    - Symbol-based buffering for period analysis
    - Aggregate-specific event detection
    - Volume surge detection (3x average threshold)
```

### FMVChannel Specification
```python
class FMVChannel(ProcessingChannel):
    - Batch processing (batch_size=50, timeout=500ms)
    - Confidence filtering (min 0.8 threshold)
    - Deviation detection (1.0% threshold)  
    - Valuation discrepancy event creation
```

### Data Models
```python
@dataclass
class OHLCVData:
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    percent_change: float
    avg_volume: float
    timestamp: float

@dataclass  
class FMVData:
    ticker: str
    fmv: float
    market_price: float
    confidence: float
    deviation_percent: float
    timestamp: float
```

## Technical Considerations

### Event Detection Integration
- All channels must produce events compatible with existing WebSocket publisher
- Event formats must match current typed event system
- Channel-specific events must include source identification

### Performance Requirements
- TickChannel must maintain <10ms processing latency
- OHLCVChannel must handle batches of 100 items efficiently
- FMVChannel must filter low-confidence data before processing

### Memory Management
- Symbol-based buffers in OHLCVChannel must have size limits
- Batch buffers must implement overflow protection
- Old data must be purged to prevent memory leaks

### Error Handling
- Each channel must handle data validation errors gracefully
- Invalid data should be logged and discarded, not crash the channel
- Confidence filtering failures in FMVChannel should be recoverable

## Success Metrics

1. **Channel Implementation Completeness**: All three channels (Tick, OHLCV, FMV) implemented and functional
2. **Data Processing Accuracy**: Channels correctly process their respective data types without corruption
3. **Event Generation**: All channels generate events compatible with existing WebSocket system
4. **Performance Targets**: TickChannel <10ms latency, OHLCV batching efficiency >90%, FMV filtering accuracy >95%
5. **Configuration Compliance**: All channels respect their configuration settings for batching and thresholds
6. **Error Resilience**: Channels handle invalid data and processing errors without system failure

## Testing Requirements

### Unit Tests
- Test each channel's data processing logic independently
- Test event creation and format compatibility  
- Test configuration loading and validation for each channel
- Test error handling for invalid data inputs
- Test batching logic and timeout behavior

### Channel-Specific Tests
- **TickChannel**: Test immediate processing and latency requirements
- **OHLCVChannel**: Test batch processing, symbol buffering, and aggregate event detection
- **FMVChannel**: Test confidence filtering, deviation detection, and batch efficiency

### Integration Tests
- Test channel compatibility with base infrastructure from Sprint 105
- Test event format compatibility with existing systems
- Test multi-channel concurrent processing
- Test metrics collection across all channel types

## Open Questions

1. Should OHLCVChannel implement technical indicator calculations (moving averages, RSI)?
2. How should FMVChannel handle conflicting fair market value data from multiple sources?
3. Should channels support custom event detection rules through configuration?
4. How should we handle data type evolution (new fields in OHLCV or FMV)?
5. Should channels implement data persistence for historical analysis?

## Deliverables

- **TickChannel Implementation**: Complete real-time tick processing channel
- **OHLCVChannel Implementation**: Complete OHLCV aggregate processing channel with batching
- **FMVChannel Implementation**: Complete fair market value processing channel with filtering
- **Data Type Models**: `OHLCVData` and `FMVData` model classes with validation
- **Event Creation Logic**: Channel-specific event creation and transport methods
- **Channel Configurations**: Default and validation rules for all channel types
- **Unit Test Suite**: Comprehensive tests for all channel implementations
- **Integration Test Framework**: Tests for channel compatibility with core infrastructure