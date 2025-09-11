# Sprint 25 Integration Tests

**Date**: September 10, 2025  
**Purpose**: Database connectivity and WebSocket pattern event integration tests  

## Test Scripts

### Database Integration Tests
- **`test_db_simple.py`**: Basic database connectivity test for pattern tables
- **`test_db_connection.py`**: Detailed database connectivity test with error handling

**Usage**:
```bash
cd tests/integration
python test_db_simple.py
python test_db_connection.py
```

**Expected Output**:
- SUCCESS: Database connection established
- Pattern table counts displayed (daily_patterns, intraday_patterns, pattern_detections, pattern_definitions)

### WebSocket Integration Test  
- **`test_websocket_patterns.py`**: End-to-end WebSocket pattern event testing

**Purpose**: Tests the complete Redis → WebSocket → Frontend pattern flow

**Usage**:
```bash
cd tests/integration
python test_websocket_patterns.py
```

**Expected Behavior**:
1. Publishes test pattern events to Redis channel `tickstock.events.patterns`
2. Events should be received by Redis Event Subscriber 
3. Events forwarded to WebSocket broadcaster
4. Frontend TierPatternService processes real-time alerts
5. Pattern alerts appear in Pattern Dashboard

**Test Patterns Published**:
- BreakoutBO on AAPL (daily tier)
- DivergenceDO on GOOGL (intraday tier)  
- ComboPattern on TSLA (combo tier)

**Verification Steps**:
1. Open http://localhost:5000 Pattern Dashboard before running test
2. Open browser console to monitor TierPatternService logs
3. Run test script
4. Verify pattern alerts appear in correct tier columns
5. Check for browser notifications (if enabled)

## Integration with Sprint 25

These tests validate the completed Sprint 25 MVP deliverables:
- ✅ Database connectivity with TimescaleDB pattern tables
- ✅ Real-time WebSocket pattern events integration
- ✅ End-to-end Redis pub-sub → WebSocket → Frontend flow
- ✅ Multi-tier pattern dashboard functionality

## Related Documentation
- [`../../docs/architecture/websocket-pattern-events.md`](../../docs/architecture/websocket-pattern-events.md) - Complete WebSocket architecture
- [`../../docs/planning/sprints/sprint25/sprint25_definition_of_done.md`](../../docs/planning/sprints/sprint25/sprint25_definition_of_done.md) - Sprint completion status