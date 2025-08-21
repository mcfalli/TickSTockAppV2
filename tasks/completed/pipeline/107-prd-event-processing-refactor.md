# Sprint 107 PRD: Event Processing Refactor

## Introduction/Overview

This sprint refactors the existing EventProcessor and MarketDataService to integrate with the new multi-channel architecture from Sprints 105-106. The focus is on updating the event processing pipeline to work with multiple data sources and channels while preserving existing event detection logic and maintaining compatibility with the WebSocket publishing system.

**Problem Statement:** The current EventProcessor and MarketDataService are designed for single-entry point processing through `handle_websocket_tick()`. We need to refactor these components to support multi-source data input, source-specific processing rules, and integration with the new channel-based architecture while maintaining all existing functionality.

## Goals

1. **Refactor EventProcessor**: Update EventProcessor to handle multi-source data through channel integration
2. **Update MarketDataService**: Create new entry points for different data types while maintaining existing functionality
3. **Implement Source Context**: Add source tracking and source-specific processing rules
4. **Preserve Event Detection**: Ensure existing event detection logic continues to work with new architecture
5. **Maintain WebSocket Compatibility**: Ensure event output remains compatible with existing WebSocket publisher

## User Stories

**As an Event Processor:**
- I want EventProcessor to handle data from multiple channels so I can process different data types appropriately
- I want source context preserved through processing so I can apply source-specific rules

**As a Market Data Handler:**
- I want separate entry points for tick, OHLCV, and FMV data so each type can be processed optimally
- I want backward compatibility maintained so existing WebSocket clients continue working

**As an Event Detection System:**
- I want existing detection logic preserved so event quality remains consistent
- I want source-specific rules so I can apply different detection criteria based on data source

**As a WebSocket Publisher:**
- I want event formats to remain consistent so frontend clients don't require changes
- I want event prioritization maintained so high-priority events are published immediately

## Functional Requirements

### 1. EventProcessor Refactor
1.1. Create new `handle_multi_source_data()` method for channel integration
1.2. Implement source context tracking for all processed data
1.3. Add source-specific event processing rules and filtering
1.4. Maintain backward compatibility with existing `handle_tick()` method

### 2. MarketDataService Entry Points
2.1. Create `handle_ohlcv_data()` method for OHLCV channel integration
2.2. Create `handle_fmv_data()` method for FMV channel integration
2.3. Update existing `handle_websocket_tick()` to route through channel system
2.4. Maintain statistics tracking for all data types

### 3. Source Context Management
3.1. Implement source identification and tracking through processing pipeline
3.2. Add source metadata to events for downstream processing
3.3. Create source-specific filtering and validation rules
3.4. Implement source-based event deduplication logic

### 4. Channel Integration
4.1. Integrate EventProcessor with DataChannelRouter from Sprint 105
4.2. Connect MarketDataService with channel-specific processing
4.3. Implement event aggregation from multiple channels
4.4. Create priority-based event emission coordination

### 5. Source-Specific Processing Rules
5.1. Implement OHLCV-specific event filtering (minimum 1% price moves)
5.2. Create FMV-specific confidence filtering (minimum 0.7 confidence)
5.3. Maintain existing tick-based event processing rules
5.4. Implement configurable thresholds for each source type

### 6. Backward Compatibility
6.1. Preserve existing method signatures for `handle_websocket_tick()`
6.2. Maintain current event format and structure
6.3. Ensure WebSocket publishing continues without changes
6.4. Preserve existing statistics and metrics collection

## Non-Goals (Out of Scope)

- Modifications to event detection algorithms or logic
- Changes to WebSocket client protocols or frontend systems
- Database schema changes or persistence modifications
- Performance optimization (handled in Sprint 108)
- New event types or detection patterns
- Configuration management system changes

## Design Specifications

### EventProcessor Integration
```python
class EventProcessor:
    def __init__(self, config, market_service, event_manager, **kwargs):
        # Existing initialization
        self.channel_router = DataChannelRouter(config)
        self.source_context = {}  # Track source per ticker
        
    async def handle_multi_source_data(self, data: Any, source: str):
        # New multi-channel entry point
        # Route through channels and apply source-specific rules
        
    def process_with_source_rules(self, event: Dict):
        # Apply source-specific event processing rules
```

### MarketDataService Entry Points
```python
class MarketDataService:
    async def handle_ohlcv_data(self, ohlcv_data: OHLCVData):
        # New OHLCV processing entry point
        
    async def handle_fmv_data(self, fmv_data: FMVData):
        # New FMV processing entry point
        
    def handle_websocket_tick(self, tick_data: TickData, ticker=None, timestamp=None):
        # Updated to route through channel system
```

### Source-Specific Rules
```python
SOURCE_RULES = {
    'ohlcv': {
        'min_percent_change': 1.0,  # Only process moves > 1%
        'required_volume_multiple': 1.5  # Must be 1.5x avg volume
    },
    'fmv': {
        'min_confidence': 0.7,  # Minimum confidence threshold
        'max_deviation': 5.0   # Maximum price deviation %
    },
    'tick': {
        # Existing tick processing rules
    }
}
```

## Technical Considerations

### Source Context Preservation
- Source information must be maintained throughout processing pipeline
- Events must include source metadata for downstream filtering
- Source context must be available for debugging and monitoring

### Event Format Compatibility
- All events must maintain existing `to_transport_dict()` format
- WebSocket publisher must receive events in expected format
- Event IDs and timestamps must remain consistent

### Processing Pipeline Integration
- Channel routing must happen before event detection
- Existing event detection logic must work with channel outputs
- Priority management must coordinate between channels and WebSocket publisher

### Error Handling
- Source-specific errors must be isolated and not affect other sources
- Channel integration errors must be recoverable
- Backward compatibility must be maintained even during error conditions

## Success Metrics

1. **Integration Completeness**: EventProcessor and MarketDataService fully integrated with multi-channel system
2. **Source Context Accuracy**: 100% of events include correct source metadata
3. **Backward Compatibility**: Existing functionality works unchanged with new architecture
4. **Event Processing Accuracy**: All events processed with appropriate source-specific rules
5. **WebSocket Compatibility**: No changes required to WebSocket publisher or frontend clients
6. **Performance Maintenance**: Processing performance matches or exceeds current system

## Testing Requirements

### Unit Tests
- Test EventProcessor multi-source data handling
- Test MarketDataService new entry points
- Test source-specific rule application
- Test backward compatibility of existing methods
- Test event format consistency

### Integration Tests
- Test EventProcessor integration with channel router
- Test MarketDataService integration with all channel types
- Test source context preservation through full processing pipeline
- Test event deduplication across multiple sources
- Test WebSocket publisher compatibility

### Regression Tests
- Test existing tick processing functionality remains unchanged
- Test existing WebSocket client compatibility
- Test existing event detection logic produces same results
- Test existing statistics and metrics collection

### Source-Specific Tests
- Test OHLCV source filtering and processing rules
- Test FMV source confidence filtering and deviation detection
- Test tick source processing maintains existing behavior
- Test multi-source event coordination and prioritization

## Open Questions

1. How should we handle conflicting events from multiple sources for the same ticker?
2. Should source-specific rules be configurable at runtime or compile-time?
3. How should we handle source failover scenarios (e.g., tick source fails, fallback to OHLCV)?
4. Should we implement source-based rate limiting or throttling?
5. How should we handle event ordering when multiple sources produce events simultaneously?

## Deliverables

- **EventProcessor Refactor**: Updated EventProcessor with multi-channel integration
- **MarketDataService Updates**: New entry points for OHLCV and FMV data processing
- **Source Context System**: Source tracking and metadata management throughout pipeline
- **Source-Specific Rules Engine**: Configurable processing rules for each data source
- **Integration Layer**: Connection between channels and existing event processing
- **Backward Compatibility Layer**: Preservation of existing API and functionality
- **Unit Test Suite**: Tests for all refactored components and new functionality
- **Integration Test Suite**: End-to-end testing of refactored processing pipeline