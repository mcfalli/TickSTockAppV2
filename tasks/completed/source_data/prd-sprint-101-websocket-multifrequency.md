# Sprint 101: WebSocket Multi-Frequency Implementation

## Introduction/Overview

This sprint implements the core multi-frequency WebSocket functionality for TickStock, enabling concurrent subscriptions to per-second ticks, per-minute aggregates, and fair market value data from Polygon.io. Building on Sprint 100's configuration foundation, this sprint delivers the actual multi-stream processing capability while maintaining the existing Pull Model architecture and zero event loss guarantees.

**Problem it solves:** Enable cost optimization and different data types by supporting multiple concurrent WebSocket subscriptions with different frequencies, allowing users to subscribe to lower-cost per-minute data for some tickers while maintaining per-second data for high-priority symbols.

## Goals

1. **Multi-Stream WebSocket Support**: Implement concurrent WebSocket subscriptions for different data frequencies
2. **Parallel Stream Processing**: Route and process different frequency streams independently without interference  
3. **Pull Model Compliance**: Maintain existing Pull Model architecture for all frequency types
4. **Event Type Integration**: Support Polygon's per-second ticks, per-minute aggregates (AM), and fair market value (FMV) events
5. **Zero Event Loss**: Guarantee no data loss across all concurrent streams

## User Stories

1. **As a trader**, I want to receive per-second data for my watchlist stocks and per-minute data for market overview so that I can optimize data costs while maintaining critical real-time insights
2. **As an algorithmic trading system**, I want to process fair market value updates alongside tick data so that I can make more informed pricing decisions
3. **As a system administrator**, I want independent stream health monitoring so that I can identify issues with specific frequency streams without affecting others
4. **As a developer**, I want clear event routing so that I can add new frequency-specific processing logic without disrupting existing flows

## Functional Requirements

1. **Enhanced PolygonWebSocketClient**
   1.1. Implement multi-frequency subscription management with concurrent connections
   1.2. Support per-second tick subscriptions (existing functionality maintained)
   1.3. Support per-minute aggregate subscriptions with "AM" event handling
   1.4. Support fair market value subscriptions with "FMV" event handling
   1.5. Implement frequency-specific reconnection and health monitoring
   1.6. Maintain existing connection lifecycle management patterns

2. **Parallel Stream Processing**
   2.1. Implement DataStreamManager for routing data by frequency
   2.2. Create frequency-specific processors without shared state
   2.3. Ensure thread-safe stream isolation to prevent cross-frequency interference
   2.4. Implement stream-specific error handling and recovery
   2.5. Support dynamic stream start/stop based on configuration

3. **Event Router Enhancement**
   3.1. Route per-second ticks to existing handle_tick processing
   3.2. Route per-minute aggregates to new handle_minute_bar processing
   3.3. Route fair market value to new handle_fmv processing
   3.4. Maintain event type consistency through existing DataPublisher/WebSocketPublisher
   3.5. Implement frequency-aware event buffering with separate buffers per stream

4. **Pull Model Integration**
   4.1. Extend DataPublisher to collect events from all frequency streams
   4.2. Maintain separate event buffers for each frequency type (per-second, per-minute, FMV)
   4.3. Enhance WebSocketPublisher to pull from multiple frequency buffers
   4.4. Implement frequency-aware emission timing and batching
   4.5. Preserve existing 1000 event/type buffer limits per frequency

5. **Polygon API Integration**
   5.1. Implement proper subscription messages for per-minute aggregates
   5.2. Implement proper subscription messages for fair market value streams
   5.3. Handle Polygon's different event schemas (tick vs AM vs FMV)
   5.4. Implement proper authentication for Business plan features (FMV)
   5.5. Support ticker filtering per frequency type

## Non-Goals (Out of Scope)

- Changes to synthetic/simulated data providers (Sprint 102)
- Frontend user interface changes for frequency selection
- Database schema changes or analytics modifications
- Performance optimization beyond maintaining current levels
- RESTful data source integration
- Changes to existing event detection logic (high/low, surge, trend)

## Design Considerations

- Maintain existing Pull Model architecture patterns
- Use frequency as primary routing key throughout the pipeline
- Follow existing WebSocket connection management patterns
- Preserve event type boundaries (typed events → dicts after Worker conversion)
- Implement proper backpressure handling for different frequency streams
- Consider memory usage with multiple concurrent streams

## Technical Considerations

- Must work with configuration system from Sprint 100
- Polygon Business plan required for Fair Market Value access
- Different event schemas require separate parsing logic
- Thread safety critical for concurrent stream processing
- WebSocket connection limits and rate limiting considerations
- Proper error isolation between streams to prevent cascading failures
- Integration with existing DataProviderFactory

## Success Metrics

1. **Multi-Stream Functionality**: Successfully process concurrent per-second, per-minute, and FMV streams
2. **Zero Event Loss**: No events dropped across any frequency stream under normal load
3. **Performance Maintenance**: No degradation in existing per-second processing latency  
4. **Stream Isolation**: Failures in one frequency stream do not affect others
5. **Configuration Integration**: All frequency combinations from Sprint 100 work correctly
6. **Memory Stability**: No memory leaks with multiple concurrent streams over extended operation

## Open Questions

1. Should stream prioritization be implemented if system resources become constrained?
2. How should conflicting ticker subscriptions across frequencies be handled?
3. What level of stream health metrics should be exposed for monitoring?
4. Should there be automatic failover between frequency types for critical tickers?
5. How should timing synchronization be handled between different frequency streams?

## Acceptance Criteria

- [ ] PolygonWebSocketClient supports concurrent subscriptions to multiple frequencies
- [ ] Per-second tick processing maintains existing functionality and performance
- [ ] Per-minute aggregate processing correctly handles Polygon "AM" events
- [ ] Fair market value processing correctly handles Polygon "FMV" events  
- [ ] DataPublisher collects events from all frequency streams with separate buffering
- [ ] WebSocketPublisher emits events from all frequencies maintaining Pull Model
- [ ] Stream isolation prevents failures in one frequency from affecting others
- [ ] All configuration combinations from Sprint 100 work correctly
- [ ] No memory leaks or resource exhaustion with multiple concurrent streams
- [ ] Existing test suite passes with no modifications
- [ ] Integration tests verify multi-frequency data flow end-to-end