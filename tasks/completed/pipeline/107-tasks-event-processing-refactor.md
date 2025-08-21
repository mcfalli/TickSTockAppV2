# Sprint 107 Tasks: Event Processing Refactor

## Relevant Files

- `src/processing/pipeline/event_processor.py` - Existing EventProcessor requiring refactor for multi-channel integration
- `src/core/services/market_data_service.py` - Existing MarketDataService requiring new entry points
- `src/processing/pipeline/source_context_manager.py` - New source context tracking system
- `src/processing/rules/source_specific_rules.py` - New source-specific processing rules engine
- `src/processing/pipeline/multi_source_coordinator.py` - New multi-source event coordination
- `tests/unit/processing/pipeline/test_event_processor_refactor.py` - Unit tests for EventProcessor changes
- `tests/unit/core/services/test_market_data_service_entries.py` - Unit tests for new service entry points
- `tests/unit/processing/pipeline/test_source_context_manager.py` - Unit tests for source context tracking
- `tests/integration/processing/test_multi_source_integration.py` - Integration tests for multi-source processing
- `tests/regression/test_existing_functionality_preservation.py` - Regression tests for backward compatibility

### Notes

- All existing functionality must be preserved during refactor
- Source context must be maintained throughout the processing pipeline
- Event formats must remain compatible with existing WebSocket publisher
- Integration must work with channel infrastructure from Sprint 105-106

## Tasks

- [ ] 1.0 Refactor EventProcessor for Multi-Channel Integration
  - [ ] 1.1 Add handle_multi_source_data() method for channel integration
  - [ ] 1.2 Implement source context tracking for all processed data
  - [ ] 1.3 Create source-specific event processing rules and filtering
  - [ ] 1.4 Maintain backward compatibility with existing handle_tick() method
  - [ ] 1.5 Integrate EventProcessor with DataChannelRouter from Sprint 105
- [ ] 2.0 Update MarketDataService Entry Points
  - [ ] 2.1 Create handle_ohlcv_data() method for OHLCV channel integration
  - [ ] 2.2 Create handle_fmv_data() method for FMV channel integration
  - [ ] 2.3 Update existing handle_websocket_tick() to route through channel system
  - [ ] 2.4 Maintain statistics tracking for all data types
  - [ ] 2.5 Preserve existing method signatures and API contracts
- [ ] 3.0 Implement Source Context Management System
  - [ ] 3.1 Create source identification and tracking through processing pipeline
  - [ ] 3.2 Add source metadata to events for downstream processing
  - [ ] 3.3 Implement source-based event deduplication logic
  - [ ] 3.4 Create source context storage and retrieval mechanisms
  - [ ] 3.5 Add source context debugging and monitoring capabilities
- [ ] 4.0 Create Source-Specific Processing Rules Engine
  - [ ] 4.1 Implement OHLCV-specific event filtering (minimum 1% price moves)
  - [ ] 4.2 Create FMV-specific confidence filtering (minimum 0.7 confidence)
  - [ ] 4.3 Maintain existing tick-based event processing rules
  - [ ] 4.4 Implement configurable thresholds for each source type
  - [ ] 4.5 Add rule validation and error handling for invalid configurations
- [ ] 5.0 Implement Multi-Source Event Coordination
  - [ ] 5.1 Create event aggregation from multiple channels
  - [ ] 5.2 Implement priority-based event emission coordination
  - [ ] 5.3 Add event conflict resolution for same ticker from multiple sources
  - [ ] 5.4 Create event ordering and sequencing for consistent delivery
  - [ ] 5.5 Implement performance monitoring for multi-source processing
- [ ] 6.0 Create Comprehensive Test Suite
  - [ ] 6.1 Write unit tests for EventProcessor multi-source integration
  - [ ] 6.2 Create unit tests for MarketDataService new entry points
  - [ ] 6.3 Implement unit tests for source context preservation
  - [ ] 6.4 Write regression tests for existing functionality preservation
  - [ ] 6.5 Create integration tests for end-to-end multi-source processing