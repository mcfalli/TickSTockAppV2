# Sprint 109 PRD: Data Flow Pipeline Diagnosis

## Introduction/Overview

Sprint 109 focuses on diagnosing the complete data flow pipeline from synthetic WebSocket sources through to frontend emission. Following Sprint 108 implementation updates, synthetic data is being generated and processed but not reaching the frontend, with runtime errors occurring in the processing chain. This diagnostic sprint will trace the entire pipeline to identify breaking points and prepare actionable fixes for Sprint 110.

The goal is to restore end-to-end data flow while ensuring JSON emission compatibility with the existing frontend architecture per docs/JSON.md specifications.

## Goals

1. **Complete Pipeline Trace**: Map data flow from synthetic WebSocket ingestion → event detection → queue management → emission → frontend
2. **Break Point Identification**: Identify all runtime errors and processing failures with root cause analysis
3. **Architectural Documentation**: Document current vs. expected data flow patterns
4. **Sprint 110 Preparation**: Create actionable fix list with implementation priority
5. **JSON Compatibility**: Ensure emission format matches docs/JSON.md for seamless frontend integration

## User Stories

1. **As a developer**, I want to see exactly where data stops flowing in the pipeline so I can target fixes effectively
2. **As a system operator**, I want runtime errors clearly identified with root causes so I can understand system health
3. **As a frontend developer**, I want to receive properly formatted JSON events so the existing UI continues working without changes
4. **As a product owner**, I want the diagnostic results to inform Sprint 110 scope and timeline accurately

## Functional Requirements

1. **Data Flow Tracing**: System must trace synthetic data from WebSocket ingestion through each processing stage
2. **Error Collection**: System must capture and categorize all runtime errors with stack traces and context
3. **Architecture Mapping**: System must document current data flow vs. expected data flow patterns
4. **Breaking Point Analysis**: System must identify specific code locations where processing fails
5. **JSON Validation**: System must validate emission format against docs/JSON.md specification
6. **Fix Documentation**: System must produce prioritized list of required fixes for Sprint 110
7. **Critical Fix Implementation**: System must allow immediate fixes for blocking issues during diagnosis
8. **Performance Baseline**: System must establish performance metrics for comparison after fixes

## Non-Goals (Out of Scope)

1. **Major Refactoring**: No architectural changes or large-scale refactoring during diagnosis
2. **New Feature Development**: No new functionality additions during diagnostic phase
3. **UI Changes**: No frontend modifications unless required for testing data reception
4. **Performance Optimization**: Focus on functionality restoration, not performance improvements
5. **Database Schema Changes**: No schema modifications during diagnosis phase

## Design Considerations

- **Tracing Strategy**: Start from synthetic data sources and trace forward through pipeline
- **Error Logging**: Enhanced logging at each pipeline stage for detailed diagnosis
- **JSON Format**: Strict adherence to docs/JSON.md specification for emission compatibility
- **Minimal Disruption**: Diagnostic code should not interfere with existing functionality

## Technical Considerations

- **Component Integration**: Focus on WebSocket ingestion, event detection logic, queue management, and WebSocketManager emission
- **Sprint 108 Changes**: Review all modifications from Sprint 108 that may affect pipeline flow
- **Memory Management**: Consider memory usage during enhanced diagnostic logging
- **Thread Safety**: Ensure diagnostic code doesn't introduce race conditions
- **Rollback Plan**: Ability to quickly disable diagnostic features if they cause additional issues

## Success Metrics

1. **Complete Data Flow Map**: 100% of pipeline stages documented with data transformation points
2. **Error Identification**: All runtime errors catalogued with root cause analysis
3. **Fix List Completeness**: Sprint 110 task list contains specific, actionable fixes with effort estimates
4. **JSON Compliance**: Emission format validated against docs/JSON.md with zero format discrepancies
5. **Critical Fix Success**: Any blocking issues identified during diagnosis are resolved immediately

## Identified Runtime Errors

### Critical Error #1: AsyncIO Event Loop Thread Mismatch
**Location**: `src/core/services/market_data_service.py:705`  
**Error**: `RuntimeError: There is no current event loop in thread 'Thread-1'`  
**Root Cause**: WebSocket handler running in Thread-1 attempting to access asyncio event loop via `asyncio.get_event_loop()`  
**Impact**: Complete pipeline blockage - data cannot progress beyond WebSocket ingestion  
**Priority**: **CRITICAL** - Immediate fix required

**Code Context**:
```python
# Lines 703-708 in handle_websocket_tick method
import asyncio
if asyncio.iscoroutinefunction(self.event_processor.handle_multi_source_data):
    loop = asyncio.get_event_loop()  # ❌ FAILS HERE - no loop in Thread-1
    processing_result = loop.run_until_complete(
        self.event_processor.handle_multi_source_data(tick_data, "websocket_tick")
    )
```

**Immediate Fix Required**:
```python
# Replace lines 704-708 with thread-safe event loop handling:
if asyncio.iscoroutinefunction(self.event_processor.handle_multi_source_data):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop in thread - create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    processing_result = loop.run_until_complete(
        self.event_processor.handle_multi_source_data(tick_data, "websocket_tick")
    )
```

**Status**: ✅ **FIXED** - Applied 2025-08-21 13:08

### Critical Error #2: Channel Router Circuit Breaker Protection
**Location**: `src/processing/channels/channel_router.py`  
**Error**: `Router circuit breaker is open, rejecting request` (massive volume)  
**Root Cause**: Channel router reached 10 consecutive routing failures and opened circuit breaker protection  
**Impact**: All data routing blocked - processed events cannot reach emission pipeline  
**Priority**: **CRITICAL** - Immediate investigation required  

**Configuration Context**:
- Circuit Breaker Threshold: 10 consecutive failures
- Circuit Breaker Timeout: 60 seconds auto-recovery
- Current State: OPEN (blocking all routing requests)

**Next Action Required**: Identify why routing is failing to trigger circuit breaker.

**Status**: ✅ **FIXED** - Applied 2025-08-21 13:14

**Root Cause Found**: No TickChannel registered with channel router during startup  
**Fix Applied**: Added TickChannel registration in `market_data_service.py:208-214`  
```python
# SPRINT 109 FIX: Register TickChannel for tick data processing
from src.processing.channels.tick_channel import TickChannel
from src.processing.channels.channel_config import TickChannelConfig
tick_config = TickChannelConfig()
tick_channel = TickChannel("primary_tick", tick_config)
self.channel_router.register_channel(tick_channel)
```
**Circuit Breaker**: Re-enabled after underlying issue resolved

## Open Questions

1. **Threading Architecture**: Should WebSocket handling move to main thread or should we create event loop in worker thread?
2. **Sprint 108 Multi-Source Integration**: Was the `handle_multi_source_data` method designed to be async or sync?
3. **Event Loop Strategy**: Should we use `asyncio.new_event_loop()` or `asyncio.run()` for thread isolation?
4. **Fallback Behavior**: Is the fallback to `handle_tick()` method working correctly when multi-source fails?
5. **Thread Safety**: Are there other threading issues in the multi-source integration?
6. **Performance Impact**: What's the performance cost of different event loop strategies?

## Implementation Approach

### Phase 1: Pipeline Tracing (Days 1-2)
- Add comprehensive logging at each pipeline stage
- Document data transformations and handoffs
- Identify where data flow stops or corrupts

### Phase 2: Error Analysis (Days 2-3)
- Collect and categorize all runtime errors
- Perform root cause analysis for each error type
- Map errors to specific code locations and Sprint 108 changes

### Phase 3: Fix Planning (Days 3-4)
- Document required fixes with implementation complexity
- Implement critical blocking fixes immediately
- Prepare detailed Sprint 110 task breakdown

### Phase 4: Validation (Day 4)
- Verify JSON emission format compliance
- Test end-to-end data flow with fixes applied
- Validate frontend compatibility

---
*Created: 2025-08-21*  
*Sprint: 109*  
*Target Audience: Junior Developer*