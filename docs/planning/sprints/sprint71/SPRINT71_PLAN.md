# Sprint 71 Plan - REST API Endpoints

**Status**: In Progress
**Started**: February 9, 2026
**Sprint Type**: API Integration
**Estimated Duration**: 5-7 hours
**Parent Sprint**: Sprint 68 (Core Analysis Migration)
**Prerequisites**: Sprint 68 (Analysis Service), Sprint 69 (Patterns), Sprint 70 (Indicators)

---

## Sprint Goal

Expose analysis services (patterns + indicators) via REST API for external integrations and programmatic access.

**Success Criteria**:
- 6 REST endpoints implemented with Pydantic v2 validation
- Single symbol analysis (<50ms response)
- Universe batch analysis (<2s for 100 symbols)
- Comprehensive error handling (400/500 responses)
- 30+ API tests passing
- OpenAPI/Swagger documentation auto-generated

---

## Implementation Sequence

### Task #1: Single Symbol Analysis Endpoint (1-2 hours)
**Endpoint**: POST `/api/analysis/symbol`

**Request Model** (Pydantic v2):
```python
class SymbolAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    timeframe: str = Field(default="daily", pattern="^(daily|weekly|hourly|intraday|monthly|1min)$")
    indicators: list[str] | None = None  # ["sma", "rsi", "macd"] or None for all
    patterns: list[str] | None = None  # ["doji", "hammer"] or None for all
    calculate_all: bool = False  # If True, ignores indicators/patterns and calculates everything

    model_config = ConfigDict(str_strip_whitespace=True)
```

**Response Model**:
```python
class SymbolAnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    indicators: dict[str, Any]  # {indicator_name: {value, value_data, ...}}
    patterns: dict[str, Any]  # {pattern_name: detections[]}
    metadata: dict[str, Any]  # Calculation time, data points, etc.
```

**Implementation**:
- Use `AnalysisService` from Sprint 68
- Data fetching from database (last N bars based on timeframe)
- Error handling: ValidationError (400), AnalysisError (500)
- Performance target: <50ms response

**Tests**: 10-15 tests
- Valid request with specific indicators
- Valid request with calculate_all=True
- Invalid symbol (404)
- Invalid timeframe (400)
- Missing data (500)

### Task #2: Universe Batch Analysis Endpoint (2-3 hours)
**Endpoint**: POST `/api/analysis/universe`

**Request Model**:
```python
class UniverseAnalysisRequest(BaseModel):
    universe_key: str  # "nasdaq100", "SPY", "dow30", etc.
    timeframe: str = "daily"
    indicators: list[str] | None = None
    patterns: list[str] | None = None
    max_symbols: int | None = Field(default=None, ge=1, le=1000)
    calculate_all: bool = False
```

**Response Model**:
```python
class UniverseAnalysisResponse(BaseModel):
    universe_key: str
    timeframe: str
    timestamp: datetime
    symbols_analyzed: int
    results: dict[str, SymbolAnalysisResponse]  # {symbol: analysis}
    summary: dict[str, Any]  # Aggregate statistics
    metadata: dict[str, Any]  # Total time, cache hits, etc.
```

**Implementation**:
- Use RelationshipCache to get universe symbols
- Batch analysis using AnalysisService
- Progress tracking (optional WebSocket updates)
- Summary statistics (avg indicators, pattern counts)
- Performance target: <2s for 100 symbols

**Tests**: 10-15 tests
- Valid universe analysis
- Universe with max_symbols limit
- Invalid universe_key (404)
- Empty universe (400)
- Performance test (100 symbols)

### Task #3: Data Validation Endpoint (1 hour)
**Endpoint**: POST `/api/analysis/validate-data`

**Request Model**:
```python
class DataValidationRequest(BaseModel):
    data: str  # CSV string or JSON
    format: str = Field(default="csv", pattern="^(csv|json)$")
```

**Response Model**:
```python
class DataValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    data_points: int
    columns_found: list[str]
    metadata: dict[str, Any]
```

**Implementation**:
- Parse CSV/JSON to DataFrame
- Validate OHLC consistency
- Check for NaN values
- Verify minimum data requirements
- Performance target: <20ms

**Tests**: 5-10 tests
- Valid CSV data
- Valid JSON data
- Missing columns (400)
- Invalid OHLC (400)
- NaN values detected

### Task #4: Discovery Endpoints (30 minutes each)

#### GET `/api/indicators/available`
**Response Model**:
```python
class IndicatorsListResponse(BaseModel):
    indicators: dict[str, list[str]]  # {category: [indicator_names]}
    total_count: int
    categories: list[str]
```

**Implementation**:
- Use IndicatorLoader to get registered indicators
- Group by category (trend, momentum, volatility, volume)
- Redis cache with 1-hour TTL
- Performance target: <10ms (cached)

#### GET `/api/patterns/available`
**Response Model**:
```python
class PatternsListResponse(BaseModel):
    patterns: dict[str, list[str]]  # {category: [pattern_names]}
    total_count: int
    categories: list[str]
```

**Implementation**:
- Use PatternDetectionService to get registered patterns
- Group by category (candlestick, daily, etc.)
- Redis cache with 1-hour TTL
- Performance target: <10ms (cached)

#### GET `/api/analysis/capabilities`
**Response Model**:
```python
class CapabilitiesResponse(BaseModel):
    version: str
    indicators: dict[str, int]  # {category: count}
    patterns: dict[str, int]  # {category: count}
    supported_timeframes: list[str]
    performance_stats: dict[str, Any]
```

**Implementation**:
- Aggregate counts from indicators/patterns
- Include version info
- Add performance statistics
- Performance target: <10ms

---

## File Structure

### New Files (6)
1. `src/api/routes/analysis_routes.py` - Analysis endpoints
2. `src/api/routes/discovery_routes.py` - Discovery endpoints
3. `src/api/models/analysis_models.py` - Pydantic request/response models
4. `tests/unit/api/test_analysis_routes.py` - Analysis route tests
5. `tests/unit/api/test_discovery_routes.py` - Discovery route tests
6. `tests/unit/api/test_analysis_models.py` - Model validation tests

### Modified Files (2)
1. `app.py` - Register new blueprints
2. `src/api/__init__.py` - Export new routes

---

## Architecture Decisions

### 1. Pydantic v2 for Request/Response Validation
**Rationale**: Type safety, auto-validation, OpenAPI generation
**Impact**: Clear API contracts, automatic documentation

### 2. Blueprint Pattern for Routes
**Rationale**: Modular organization, easy to extend
**Impact**: Clean separation of concerns

### 3. Error Handling Hierarchy
**Rationale**: Consistent error responses
**Impact**: Better client experience

```python
ValidationError → 400 Bad Request
AnalysisError → 500 Internal Server Error
NotFoundError → 404 Not Found
```

### 4. Redis Caching for Discovery Endpoints
**Rationale**: Indicator/pattern lists rarely change
**Impact**: <10ms response times (cached)

---

## Testing Strategy

### Unit Tests (30+ tests)
- Request model validation (10 tests)
- Response model serialization (5 tests)
- Endpoint logic (15 tests)

### Integration Tests (Optional)
- End-to-end analysis flow
- Database integration
- Cache integration

### Performance Tests
- Single symbol: <50ms
- Universe (100 symbols): <2s
- Discovery endpoints: <10ms (cached)

---

## Success Metrics

### Functionality ✅
- [ ] All 6 endpoints implemented
- [ ] Pydantic v2 validation working
- [ ] Error handling complete
- [ ] 30+ tests passing

### Performance ✅
- [ ] Single symbol analysis: <50ms
- [ ] Universe analysis: <2s for 100 symbols
- [ ] Discovery endpoints: <10ms
- [ ] Data validation: <20ms

### Code Quality ✅
- [ ] OpenAPI/Swagger docs auto-generated
- [ ] Comprehensive error messages
- [ ] Type hints throughout
- [ ] Clean blueprint organization

---

## Estimated Effort Breakdown

| Task | Estimated | Complexity |
|------|-----------|------------|
| Single Symbol Endpoint | 1-2h | Medium |
| Universe Batch Endpoint | 2-3h | High |
| Data Validation Endpoint | 1h | Low |
| Discovery Endpoints (3) | 1.5h | Low |
| Testing | 1-2h | Medium |
| **Total** | **6.5-9.5h** | **Medium-High** |

---

## Dependencies

- ✅ Sprint 68: AnalysisService, IndicatorLoader, PatternDetectionService
- ✅ Sprint 69: 8 patterns available
- ✅ Sprint 70: 8 indicators available
- ✅ RelationshipCache: Universe symbol loading
- ✅ Redis: Caching layer
- ✅ Pydantic v2: Request/response models

---

## Next Sprint Candidates

After Sprint 71 (REST API):
- **Background Job Integration** - Async universe analysis
- **Performance Optimization** - Caching, multiprocessing
- **Additional Indicators** - OBV, VWAP, Williams %R
- **Additional Patterns** - Piercing Line, Dark Cloud Cover

---

**Sprint 71: Ready to implement** 🚀
