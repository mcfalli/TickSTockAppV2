# Sprint 42 - Architectural Realignment: OHLCV Aggregation Ownership

**Sprint Goal**: Resolve architectural boundary violations by establishing clear OHLCV aggregation ownership, eliminating duplicate processing, and enforcing true loose coupling between TickStockAppV2 (consumer) and TickStockPL (producer).

**Status**: 📋 PLANNING
**Priority**: P0 - CRITICAL ARCHITECTURE FIX
**Complexity**: MEDIUM-HIGH
**Estimated Duration**: 3-5 days
**Dependencies**: Sprint 41 (Synthetic Data Integration)

---

## Executive Summary

### Problem Statement

**CRITICAL ARCHITECTURAL VIOLATION DISCOVERED**: TickStockAppV2 is performing "producer" responsibilities (OHLCV aggregation + database writes) that violate documented role separation and create duplicate processing with TickStockPL.

**Evidence**:
1. ✅ TickStockAppV2 has `OHLCVPersistenceService` writing to `ohlcv_1min` table
2. ❌ TickStockPL lacks tick aggregation but attempts pattern detection on raw ticks
3. ❌ Both systems are (or should be) aggregating the same tick data
4. ❌ AppV2 has write access to database (violates read-only boundary)
5. ❌ Single source of truth for OHLCV data is unclear

**From Documentation**:
- `docs/about_tickstock.md:16-28`: "TickStockAppV2: Consumer & UI Management" / "TickStockPL: Producer & Processing Engine"
- `docs/architecture/README.md:34`: "TickStockAppV2: Read-only database queries for UI elements"
- `CLAUDE.md`: "Database Access: Read-only user for application... Pattern data comes via Redis pub-sub from TickStockPL"

### Proposed Solution

**Option A: Strict Role Separation (RECOMMENDED)**

**Move ALL OHLCV aggregation to TickStockPL** to align with documented architecture:

```
[Polygon/Synthetic Data]
    ↓
[TickStockAppV2: Raw Forwarder ONLY]
    └─→ Forwards raw ticks to Redis ✅ (NO aggregation, NO DB writes)

[Redis: tickstock:market:ticks]
    ↓
[TickStockPL: Producer/Processor]
    ├─→ TickAggregator: Aggregates ticks → 1-minute OHLCV bars ✅
    ├─→ Writes to ohlcv_1min table (FULL DB ACCESS) ✅
    ├─→ Runs pattern detection on completed bars ✅
    ├─→ Publishes results to Redis ✅
    └─→ TickStockAppV2 consumes for UI display ✅
```

**Benefits**:
- ✅ True loose coupling (AppV2 and TickStockPL independent)
- ✅ Clear role boundaries (Consumer vs Producer)
- ✅ Single source of truth for OHLCV data
- ✅ Matches documented architecture
- ✅ No duplicate processing
- ✅ Easier to scale independently

---

## Current State Analysis

### What's Working ✅
1. **Tick Data Flow**: AppV2 → Redis → TickStockPL
2. **Redis Pub-Sub**: `tickstock:market:ticks` channel operational
3. **Synthetic Data**: Sprint 41 delivers reliable test data
4. **WebSocket Broadcasting**: UI updates working

### What's Broken ❌
1. **Role Violation**: AppV2 performing aggregation (producer work)
2. **Database Boundary**: AppV2 has write access (violates read-only policy)
3. **Duplicate Processing**: Both systems aggregate (or should aggregate) ticks
4. **Pattern Detection**: TickStockPL tries to detect patterns on raw ticks (impossible)
5. **Data Ownership**: Unclear who owns `ohlcv_1min` table

### Evidence Files
- **AppV2 Aggregation**: `src/core/services/market_data_service.py:56-60, 203-206`
- **AppV2 DB Writes**: `src/infrastructure/database/ohlcv_persistence.py:336-346`
- **Role Definitions**: `docs/about_tickstock.md:16-28`, `docs/architecture/README.md:26-41`

---

## Sprint 42 Implementation Plan

### Phase 1: TickStockPL - Add TickAggregator (Days 1-2)

**Goal**: Implement tick aggregation in TickStockPL as the single source of truth for OHLCV data.

**Location**: TickStockPL repository

**Components to Create**:
1. **TickAggregator**: `src/streaming/tick_aggregator.py`
   - Subscribes to tick callbacks from RedisTickSubscriber
   - Aggregates ticks into 1-minute OHLCV bars per symbol
   - Detects minute boundaries (timestamp floor to minute)
   - On minute completion: Creates `OHLCVData` and notifies persistence manager

2. **Integration Points**:
   - Modify `src/streaming/redis_tick_subscriber.py`: Register TickAggregator callback
   - Modify `src/services/streaming_scheduler.py`: Initialize TickAggregator
   - Use existing `StreamingPersistenceManager.add_minute_bar()` (already implemented)

**Success Criteria**:
- ✅ TickAggregator processes 1000+ ticks/sec with <0.1ms latency
- ✅ Completed bars trigger pattern detection via `StreamingPatternJob`
- ✅ OHLCV data written to `ohlcv_1min` table by TickStockPL
- ✅ Pattern detections appear in `intraday_patterns` table

**See**: `TICKSTOCKPL_TICK_AGGREGATOR_DESIGN.md` (replacement for original finding)

---

### Phase 2: TickStockAppV2 - Remove OHLCVPersistenceService (Day 3)

**Goal**: Remove producer responsibilities from TickStockAppV2 to enforce consumer-only role.

**Location**: TickStockAppV2 repository (this repo)

**Components to Remove**:
1. **OHLCVPersistenceService**: `src/infrastructure/database/ohlcv_persistence.py`
   - Remove entire file (433 lines)
   - Remove import from `src/core/services/market_data_service.py`
   - Remove initialization (lines 56-60)
   - Remove persistence call (lines 203-206)

2. **Database Configuration**:
   - Update `config/database_config.py`: Change `app_readwrite` → `app_readonly` user
   - Verify read-only permissions in database
   - Update `.env` documentation

3. **Related Cleanup**:
   - Remove tests: `tests/infrastructure/database/test_ohlcv_persistence.py`
   - Update `market_data_service.py` stats methods (remove persistence metrics)

**Files to Modify**:
- `src/core/services/market_data_service.py`: Lines 23, 56-60, 80-83, 111-113, 203-206, 326-328, 346-349
- `config/database_config.py`: Database user configuration

**Success Criteria**:
- ✅ AppV2 only forwards raw ticks to Redis
- ✅ No database writes from AppV2
- ✅ Database connection uses read-only user
- ✅ All tests passing after removal

---

### Phase 3: Integration Testing & Validation (Day 4)

**Goal**: Verify end-to-end flow with TickStockPL as sole aggregator.

**Test Scenarios**:

1. **Tick-to-Pattern Flow**:
   ```
   AppV2 Synthetic → Redis → TickStockPL Aggregator → Pattern Detection
   ```
   - Generate 5 minutes of synthetic ticks (300 bars expected)
   - Verify 300 OHLCV bars in `ohlcv_1min` table
   - Verify pattern detections in `intraday_patterns` table
   - Verify indicator calculations in `intraday_indicators` table

2. **No Duplicate Writes**:
   - Monitor `ohlcv_1min` table during streaming
   - Confirm all inserts come from TickStockPL (check connection logs)
   - Verify no constraint violations (duplicate keys)

3. **Performance Validation**:
   - 70 symbols @ 63 ticks/sec (Sprint 41 baseline)
   - TickAggregator latency <0.1ms per tick
   - Pattern detection latency <10ms per bar
   - End-to-end latency <100ms (tick → pattern event)

4. **Database Role Verification**:
   - Attempt write from AppV2 → should fail with permission error
   - Verify read queries still work (symbol dropdowns, health checks)

**Test Queries**:
```sql
-- Verify OHLCV bars created by TickStockPL
SELECT COUNT(*) as bar_count
FROM ohlcv_1min
WHERE timestamp > NOW() - INTERVAL '10 minutes';

-- Verify pattern detections
SELECT pattern_type, COUNT(*) as detections
FROM intraday_patterns
WHERE detection_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY pattern_type
ORDER BY detections DESC;

-- Verify indicator calculations
SELECT indicator_name, COUNT(*) as calculations
FROM intraday_indicators
WHERE calculation_timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY indicator_name
ORDER BY calculations DESC;
```

**Success Criteria**:
- ✅ All integration tests passing
- ✅ No duplicate OHLCV writes
- ✅ Pattern detection functional
- ✅ Performance targets met
- ✅ AppV2 read-only enforced

---

### Phase 4: Documentation & Architecture Updates (Day 5)

**Goal**: Update all documentation to reflect corrected architecture.

**Documents to Update**:

1. **TickStockAppV2**:
   - `docs/architecture/README.md`: Emphasize read-only database access
   - `docs/about_tickstock.md`: Clarify AppV2 as pure consumer
   - `CLAUDE.md`: Update "Current Implementation Status"
   - `docs/guides/configuration.md`: Document read-only DB user

2. **TickStockPL** (via feedback document):
   - `docs/architecture/streaming-pipeline.md`: Add TickAggregator component
   - `docs/architecture/tick-aggregation.md`: NEW - Design details
   - `docs/guides/streaming.md`: Update with aggregator configuration

3. **Cross-Project**:
   - `docs/architecture/integration.md`: Update data flow diagrams
   - `docs/planning/sprints/sprint42/SPRINT42_COMPLETE.md`: Summary

**Architecture Diagrams to Update**:
```
BEFORE (INCORRECT):
[AppV2] → Aggregates OHLCV → Writes to DB ❌
[AppV2] → Forwards ticks → Redis → [TickStockPL] → Pattern Detection (no aggregation) ❌

AFTER (CORRECT):
[AppV2] → Forwards raw ticks → Redis ✅
[Redis] → [TickStockPL] → Aggregates → Writes OHLCV → Pattern Detection ✅
[TickStockPL] → Publishes results → Redis → [AppV2] → UI Display ✅
```

**Success Criteria**:
- ✅ All architecture docs consistent
- ✅ Role boundaries clearly documented
- ✅ Data flow diagrams updated
- ✅ Configuration guides accurate

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| TickStockPL aggregator bugs | HIGH | MEDIUM | Comprehensive unit tests, gradual rollout |
| Data loss during transition | HIGH | LOW | Run both systems in parallel during testing |
| Performance regression | MEDIUM | LOW | Benchmark before/after, optimize critical paths |
| Database permission issues | MEDIUM | MEDIUM | Test read-only user thoroughly before cutover |
| Integration test failures | MEDIUM | MEDIUM | Extensive pre-testing, rollback plan ready |

**Rollback Plan**:
- Keep `OHLCVPersistenceService` code in git history
- Feature flag: `ENABLE_APPV2_AGGREGATION=false` (default)
- Can revert database user permissions if needed
- TickStockPL aggregator can be disabled independently

---

## Success Metrics

### Architectural Compliance ✅
- ✅ AppV2 has NO database write access
- ✅ AppV2 performs NO data aggregation
- ✅ TickStockPL is sole owner of `ohlcv_1min` table
- ✅ Single source of truth for OHLCV data
- ✅ Clear producer/consumer boundaries

### Functional Requirements ✅
- ✅ Pattern detection operational (>0 detections per minute)
- ✅ Indicator calculations operational
- ✅ OHLCV bars created at 1-minute intervals
- ✅ WebSocket delivery to UI <100ms
- ✅ No duplicate data writes

### Performance Targets ⚡
- ✅ Tick processing: <1ms per tick
- ✅ Bar aggregation: <0.1ms per tick
- ✅ Pattern detection: <10ms per bar
- ✅ End-to-end latency: <100ms (tick → UI)
- ✅ Memory usage: <50MB for 70 symbols

### Code Quality 📊
- ✅ All integration tests passing
- ✅ No architectural violations detected
- ✅ Documentation 100% aligned
- ✅ Zero database permission errors

---

## Dependencies

### Prerequisites ✅
- ✅ Sprint 41: Synthetic data operational
- ✅ Redis pub-sub: `tickstock:market:ticks` functional
- ✅ TickStockPL streaming infrastructure exists
- ✅ StreamingPersistenceManager implemented

### Blockers ❌
- None identified (all prerequisites met)

### External Coordination
- **TickStockPL Team**: Implement TickAggregator (Phase 1)
- **Database Admin**: Create read-only user `app_readonly`
- **Testing Team**: Validate integration tests

---

## Deliverables

### Code Deliverables (TickStockPL)
1. ✅ `src/streaming/tick_aggregator.py` - NEW
2. ✅ Modified `src/streaming/redis_tick_subscriber.py`
3. ✅ Modified `src/services/streaming_scheduler.py`
4. ✅ Unit tests: `tests/unit/streaming/test_tick_aggregator.py`
5. ✅ Integration tests: `tests/integration/streaming/test_pattern_detection_flow.py`

### Code Deliverables (TickStockAppV2)
1. ✅ Removed `src/infrastructure/database/ohlcv_persistence.py`
2. ✅ Modified `src/core/services/market_data_service.py`
3. ✅ Modified `config/database_config.py`
4. ✅ Updated integration tests

### Documentation Deliverables
1. ✅ `TICKSTOCKPL_TICK_AGGREGATOR_DESIGN.md` (replacement design)
2. ✅ `IMPLEMENTATION_GUIDE.md` (step-by-step cross-app guide)
3. ✅ Updated architecture docs (both repos)
4. ✅ `SPRINT42_COMPLETE.md` (closure summary)

### Validation Deliverables
1. ✅ Integration test results
2. ✅ Performance benchmarks (before/after)
3. ✅ Database permission audit
4. ✅ Architecture compliance report

---

## Timeline

### Day 1-2: TickStockPL Implementation
**Owner**: TickStockPL Development Team

- [ ] Create `TickAggregator` class
- [ ] Integrate with `RedisTickSubscriber`
- [ ] Write unit tests
- [ ] Test with synthetic data
- [ ] Performance benchmarking

### Day 3: TickStockAppV2 Cleanup
**Owner**: TickStockAppV2 Development Team (This Repo)

- [ ] Remove `OHLCVPersistenceService`
- [ ] Update `market_data_service.py`
- [ ] Change database user to read-only
- [ ] Update configuration
- [ ] Run local tests

### Day 4: Integration Testing
**Owner**: Both Teams + QA

- [ ] End-to-end flow testing
- [ ] Performance validation
- [ ] Database permission verification
- [ ] Load testing (70+ symbols)
- [ ] Bug fixes

### Day 5: Documentation & Closure
**Owner**: Architecture Team

- [ ] Update architecture docs
- [ ] Create closure summary
- [ ] Demo to stakeholders
- [ ] Sprint retrospective

---

## Sprint Completion Criteria

### Must Have (Blocking) ✅
- [ ] TickAggregator implemented in TickStockPL
- [ ] OHLCVPersistenceService removed from AppV2
- [ ] Database user changed to read-only
- [ ] All integration tests passing
- [ ] Pattern detection operational
- [ ] Documentation updated

### Should Have (Important) 🎯
- [ ] Performance benchmarks documented
- [ ] Architecture compliance verified
- [ ] Rollback plan tested
- [ ] Monitoring dashboards updated

### Nice to Have (Optional) 💡
- [ ] Automated architecture validation tests
- [ ] Performance regression alerts
- [ ] Database query optimization
- [ ] Enhanced logging for debugging

---

## Post-Sprint Actions

### Sprint Review
- [ ] Demo corrected architecture
- [ ] Show pattern detection working end-to-end
- [ ] Present performance metrics
- [ ] Architecture compliance report

### Backlog Items
- [ ] Automated architecture boundary checks (prevent regressions)
- [ ] Enhanced monitoring for aggregation pipeline
- [ ] Multi-timeframe aggregation (5min, 15min, 1hour)
- [ ] Historical data backfill with TickAggregator

### Follow-Up Sprints
- **Sprint 43**: Enhanced pattern detection with complete OHLCV context
- **Sprint 44**: Multi-timeframe indicator calculations
- **Sprint 45**: Advanced combo pattern detection (intraday + daily)

---

## Key Decision Points

### Decision 1: Aggregation Ownership
**Decision**: TickStockPL owns ALL OHLCV aggregation
**Rationale**: Aligns with documented "producer" role, ensures single source of truth
**Alternative Rejected**: Keep dual aggregation (violates DRY, creates consistency risks)

### Decision 2: Database Access Model
**Decision**: AppV2 uses true read-only database user
**Rationale**: Enforces architectural boundaries, prevents accidental writes
**Alternative Rejected**: Keep write access (violates documented architecture)

### Decision 3: Migration Strategy
**Decision**: Clean break - remove AppV2 aggregation entirely
**Rationale**: Avoids complexity of maintaining two code paths
**Alternative Rejected**: Feature flag for gradual migration (adds technical debt)

---

## References

### Internal Documents
- `C:\Users\McDude\TickStockPL\docs\planning\sprints\sprint42\TICK_AGGREGATOR_MISSING.md` (original finding)
- `docs/architecture/README.md` (TickStockAppV2 architecture)
- `docs/about_tickstock.md` (system overview)
- `CLAUDE.md` (development guidelines)

### Related Sprints
- **Sprint 33**: Initial streaming infrastructure
- **Sprint 40**: Live streaming integration
- **Sprint 41**: Synthetic data architecture

### Technical Specifications
- Redis Pub-Sub: `docs/architecture/redis-integration.md`
- WebSocket Integration: `docs/architecture/websockets-integration.md`
- Database Schema: TickStockPL repository

---

**Document Created**: October 10, 2025
**Sprint Owner**: Architecture Team
**Priority**: P0 - Critical Architecture Fix
**Status**: 📋 READY FOR REVIEW

---

## Appendix: Architecture Violation Evidence

### Violation 1: AppV2 Database Writes
**File**: `src/infrastructure/database/ohlcv_persistence.py:336-346`
```python
INSERT INTO ohlcv_1min (symbol, timestamp, open, high, low, close, volume)
VALUES %s
ON CONFLICT (symbol, timestamp) DO UPDATE SET
    high = GREATEST(ohlcv_1min.high, EXCLUDED.high),
    ...
```
**Issue**: AppV2 writing to shared database table

### Violation 2: AppV2 Aggregation Logic
**File**: `src/infrastructure/database/ohlcv_persistence.py:42-57`
```python
@classmethod
def from_tick_data(cls, tick_data: TickData) -> 'OHLCVRecord':
    # Convert Unix timestamp to timezone-aware datetime
    dt = datetime.fromtimestamp(tick_data.timestamp, tz=timezone.utc)
    # Round down to minute boundary for 1-minute aggregation
    minute_timestamp = dt.replace(second=0, microsecond=0)
    ...
```
**Issue**: AppV2 performing aggregation (producer responsibility)

### Violation 3: Documented Role Mismatch
**File**: `docs/about_tickstock.md:16-28`
```
TickStockAppV2: Consumer & UI Management
- ❌ Does not perform pattern detection or heavy data processing
- ❌ Does not manage database schemas

TickStockPL: Producer & Processing Engine
- Core Responsibilities: Data Processing, Database Management
```
**Issue**: Current implementation contradicts documented roles

### Violation 4: Missing TickStockPL Aggregation
**Evidence**: TickStockPL `RedisTickSubscriber._process_tick()` attempts pattern detection on individual ticks without aggregation
**Issue**: Cannot detect patterns without OHLCV bars

---

**End of Sprint 42 Plan**
