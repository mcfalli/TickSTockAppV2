# Sprint 72: Database Integration - Implementation Plan

**Date**: February 9, 2026
**Objective**: Replace mock OHLCV data with real TimescaleDB queries to make REST API production-ready
**Estimated Effort**: 4-6 hours
**Priority**: HIGH (blocks production usage)

## Current State

### What Works ✅
- REST API endpoints (8 endpoints, 18/18 tests passing)
- Pydantic v2 validation
- Service layer (AnalysisService, PatternDetectionService, IndicatorLoader)
- Pattern detection (8 patterns)
- Indicator calculation (8 indicators)

### What's Mock ❌
- OHLCV data in analysis routes (currently using synthetic pandas DataFrames)
- POST `/api/analysis/symbol` - Mock data
- POST `/api/analysis/universe` - Mock data

## Goal

**Transform**:
```python
# Current (Mock)
mock_data = pd.DataFrame({
    'open': [100] * 200,
    'high': [102] * 200,
    'low': [99] * 200,
    'close': [101] * 200,
    'volume': [1000000] * 200
})
```

**Into**:
```python
# Target (Real)
df = database.query_ohlcv(
    symbol='AAPL',
    timeframe='daily',
    limit=200
)
```

## Database Structure

### Existing Tables (From TickStockPL)
- `stock_prices_1day` - Daily OHLCV data (TimescaleDB hypertable)
- `stock_prices_1hour` - Hourly OHLCV data
- `stock_prices_1min` - Intraday OHLCV data

### Expected Schema
```sql
CREATE TABLE stock_prices_1day (
    time TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    PRIMARY KEY (time, symbol)
);
```

## Implementation Plan

### Phase 1: Database Service Layer (1-2 hours)
**File**: `src/analysis/data/ohlcv_data_service.py` (NEW)

**Purpose**: Centralized OHLCV data access with connection pooling

**Functions**:
1. `get_ohlcv_data(symbol, timeframe, limit, start_date, end_date)` → pd.DataFrame
2. `get_latest_ohlcv(symbol, timeframe)` → pd.Series
3. `validate_symbol_exists(symbol)` → bool
4. `get_available_symbols(timeframe)` → list[str]

**Database Connection**:
- Use existing `TickStockDB` class from `src.infrastructure.database.tickstock_db`
- Connection pooling already implemented
- Read-only user: `app_readwrite`

**Timeframe Mapping**:
```python
TIMEFRAME_TABLE_MAP = {
    'daily': 'stock_prices_1day',
    'hourly': 'stock_prices_1hour',
    'intraday': 'stock_prices_1min',
    '1min': 'stock_prices_1min',
    'weekly': 'stock_prices_1day',    # Resample from daily
    'monthly': 'stock_prices_1day',   # Resample from daily
}
```

### Phase 2: Update Analysis Routes (1-2 hours)
**Files**:
- `src/api/routes/analysis_routes.py` (MODIFY)

**Changes**:
1. Remove mock data generation
2. Add `OHLCVDataService` integration
3. Handle database errors (404 for missing symbols, 500 for database errors)
4. Add proper error messages

**Example Transformation**:
```python
# Before (Mock)
mock_data = pd.DataFrame({...})
result = analysis_service.analyze_symbol(
    symbol=request_data.symbol,
    data=mock_data,
    ...
)

# After (Real)
try:
    data_service = OHLCVDataService()
    ohlcv_data = data_service.get_ohlcv_data(
        symbol=request_data.symbol,
        timeframe=request_data.timeframe,
        limit=200  # Last 200 bars for indicators
    )

    if ohlcv_data.empty:
        return jsonify(ErrorResponse(
            error="NotFoundError",
            message=f"No data found for symbol {request_data.symbol}"
        ).model_dump()), 404

    result = analysis_service.analyze_symbol(
        symbol=request_data.symbol,
        data=ohlcv_data,
        ...
    )
except DatabaseError as e:
    return jsonify(ErrorResponse(
        error="DatabaseError",
        message=f"Database query failed: {str(e)}"
    ).model_dump()), 500
```

### Phase 3: Performance Optimization (1 hour)
**Query Optimization**:
1. **Limit Queries**: Fetch only last 200-250 bars (sufficient for most indicators)
2. **Indexed Queries**: Use (symbol, time) composite index
3. **Batch Queries**: Single query for universe analysis
4. **Connection Pooling**: Reuse database connections

**Expected Performance**:
- Single symbol query: <20ms (200 rows)
- Universe query: <500ms (100 symbols × 200 rows)
- Total API response: <50ms (single), <1s (universe)

**Optimization Techniques**:
```python
# Use connection pooling
with db_pool.get_connection() as conn:
    df = pd.read_sql_query(query, conn)

# Efficient batch query for universe
symbols_str = "', '".join(symbols)
query = f"""
    SELECT time, symbol, open, high, low, close, volume
    FROM stock_prices_1day
    WHERE symbol IN ('{symbols_str}')
    AND time >= NOW() - INTERVAL '200 days'
    ORDER BY symbol, time DESC
"""
```

### Phase 4: Testing & Validation (1-2 hours)

#### Update Existing Tests
**Files**:
- `tests/unit/api/test_analysis_routes.py` (MODIFY)

**Changes**:
1. Mock `OHLCVDataService` instead of using inline mock data
2. Add database error test cases
3. Add "symbol not found" test cases

#### Add Integration Tests
**Files**:
- `tests/integration/test_database_integration.py` (NEW)

**Test Cases**:
1. Query real OHLCV data from database
2. Verify data format (columns, types, ordering)
3. Test performance (<50ms for 200 rows)
4. Test error handling (invalid symbols, connection failures)

#### Manual Testing
1. Start TickStockPL services (database with data)
2. Test POST `/api/analysis/symbol` with real symbols (AAPL, MSFT, etc.)
3. Verify indicator calculations with real data
4. Verify pattern detection with real data
5. Test error cases (invalid symbols, missing data)

### Phase 5: Documentation (30 min)

**Update Files**:
1. `docs/planning/sprints/sprint72/SPRINT72_COMPLETE.md`
2. `CLAUDE.md` - Add Sprint 72 status
3. `docs/planning/sprints/BACKLOG.md` - Mark database integration complete

## Error Handling Strategy

### Error Types & HTTP Status Codes
1. **Symbol Not Found** (404)
   - No data in database for requested symbol
   - Empty DataFrame returned

2. **Invalid Timeframe** (400)
   - Unsupported timeframe
   - Caught by Pydantic validation

3. **Database Connection Error** (500)
   - Connection pool exhausted
   - Database unavailable

4. **Query Timeout** (500)
   - Query exceeds 5-second timeout
   - Large universe requests

### Graceful Degradation
- Log errors to database (`error_logs` table)
- Return partial results for universe queries (skip failed symbols)
- Include warnings in response metadata

## Performance Targets

| Operation | Target | Critical? |
|-----------|--------|-----------|
| Single Symbol Query | <20ms | Yes |
| 200-Bar OHLCV Fetch | <30ms | Yes |
| Single Symbol Analysis | <100ms | Yes |
| Universe Analysis (100 symbols) | <2s | Yes |
| Database Connection | <5ms | No |

## Dependencies

### Required
- ✅ TimescaleDB running with data
- ✅ `stock_prices_1day` table populated
- ✅ Read-only database user configured
- ✅ TickStockDB connection pool

### Optional
- Redis caching (future optimization)
- Connection pooling tuning
- Query result caching

## Risks & Mitigation

### Risk 1: Database Not Populated
**Mitigation**: Check database has recent data before starting sprint
```bash
psql -U postgres -d tickstockdb -c "SELECT COUNT(*), MAX(time) FROM stock_prices_1day;"
```

### Risk 2: Performance Issues
**Mitigation**:
- Start with limit=200 (sufficient for indicators)
- Add query timeout (5 seconds)
- Monitor query performance with EXPLAIN ANALYZE

### Risk 3: Test Failures
**Mitigation**:
- Mock OHLCVDataService in unit tests
- Separate integration tests (require database)
- Document test database requirements

## Success Criteria

### Must Have ✅
- [ ] POST `/api/analysis/symbol` uses real database
- [ ] POST `/api/analysis/universe` uses real database
- [ ] Query performance <50ms for single symbol
- [ ] Error handling for missing symbols (404)
- [ ] Error handling for database errors (500)
- [ ] 18/18 API tests still passing (with mocks)
- [ ] Integration tests passing (with database)

### Nice to Have 🎯
- [ ] Connection pooling optimization
- [ ] Query result caching (5-minute TTL)
- [ ] Performance metrics logging
- [ ] Grafana dashboard for query performance

## Post-Sprint

### Immediate Next Steps (Sprint 73)
1. OpenAPI/Swagger documentation
2. JWT authentication
3. Rate limiting

### Future Enhancements
1. Redis caching for repeated queries
2. Database query optimization (materialized views)
3. Real-time data via WebSocket integration
4. Historical data backfill endpoints

---

**Sprint 72 Goal**: Make REST API production-ready with real database integration 🚀
