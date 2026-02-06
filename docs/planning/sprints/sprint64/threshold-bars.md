name: "Threshold Bars Visualization - Sprint 64"
description: |
  Implementation of Diverging Threshold Bar and Simple Diverging Bar components
  for visualizing advance-decline sentiment across stock market data with
  backend aggregation and frontend rendering.

---

## Goal

**Feature Goal**: Implement reusable threshold bar visualization components that display advance-decline sentiment for individual stocks and aggregated groups (sectors, ETFs, indices, universes) using backend data aggregation and pure HTML/CSS/JavaScript frontend rendering.

**Deliverable**:
- Backend API endpoint (`/api/threshold-bars`) for data aggregation and binning
- Backend service (`ThresholdBarService`) for OHLCV data processing and percentage calculations
- Frontend JavaScript module (`threshold-bar-renderer.js`) for rendering diverging bars
- Frontend CSS module (`threshold-bars.css`) for responsive bar styling
- Admin UI integration showing threshold bars for SP500, NASDAQ100, and sector views

**Success Definition**:
- API endpoint returns aggregated threshold bar data in <50ms
- Frontend renders multiple bar instances (<20 per page) smoothly
- Bars correctly visualize 4-segment (Diverging Threshold) or 2-segment (Simple) distributions
- Responsive design works on desktop (horizontal) and mobile (vertical orientation option)
- Integration tests validate end-to-end data flow from database → API → frontend rendering

---

## User Persona

**Target User**: Market analysts and traders monitoring advance-decline sentiment

**Use Case**: Quickly assess market breadth and sector rotation by viewing what percentage of stocks are advancing vs declining across different groupings (indices, sectors, ETFs) and timeframes (intraday, daily, weekly, monthly).

**User Journey**:
1. User navigates to Market Overview dashboard
2. Threshold bars display for major indices (SP500, NASDAQ100, Dow30)
3. User sees at-a-glance that 65% of SP500 stocks are advancing (>0%), with 25% showing significant advances (>10% threshold)
4. User clicks on a sector (e.g., Technology) to drill down into sector-specific bars
5. Bars update to show intraday advance-decline distribution for tech stocks

**Pain Points Addressed**:
- **Current**: Manual calculation of advance-decline ratios across multiple stocks
- **Solution**: Automated aggregation with visual percentage-based representation
- **Current**: No quick way to see "how many stocks" in each sentiment bucket
- **Solution**: Diverging bars show exact percentage distribution across 2 or 4 segments

---

## Why

- **Business Value**: Provides institutional-grade market breadth analysis without requiring expensive Bloomberg Terminal or similar tools
- **User Impact**: Enables faster pattern recognition of market rotation and sentiment shifts across sectors/indices
- **Integration**: Complements existing pattern detection by showing aggregate sentiment context for individual stock patterns
- **Problems Solved**:
  - Market breadth monitoring: Quickly identify when indices are being driven by few large-cap stocks vs broad participation
  - Sector rotation detection: Spot when money is flowing between sectors by comparing threshold bar distributions
  - Divergence identification: See when price action (index level) diverges from breadth (number of advancing stocks)

---

## What

**User-Visible Behavior**:
1. **Threshold Bar Display**: Horizontal bars showing percentage distribution of stocks relative to threshold
2. **Two Bar Types**:
   - **Diverging Threshold Bar**: 4 segments (significant decline, minor decline, minor advance, significant advance)
   - **Simple Diverging Bar**: 2 segments (decline, advance)
3. **Configurable Threshold**: Default 10% for "significant" moves, adjustable via API parameter
4. **Multiple Groupings**: Individual stocks, indices (SP500, NASDAQ100), sectors, ETFs, themes, universes
5. **Multiple Timeframes**: Intraday (since market open), daily, weekly, monthly, quarterly, annual
6. **Static and Dynamic Modes**:
   - Static: Pre-aggregated data updated on schedule (daily close, weekly close, etc.)
   - Dynamic: Real-time intraday updates via periodic polling (every 60 seconds)
7. **Responsive Design**: Horizontal bars on desktop, optional vertical orientation on mobile

**Technical Requirements**:
1. Backend calculates percentage change for each symbol in group
2. Backend bins values into 2 or 4 segments based on threshold
3. Backend returns JSON with segment percentages (e.g., `{"significant_decline": 15, "minor_decline": 20, "minor_advance": 40, "significant_advance": 25}`)
4. Frontend renders bars using flexbox with percentage-based widths
5. Frontend supports configuration via JSON parameters (type, threshold, colors, orientation)
6. Performance: Backend aggregation <50ms, frontend rendering <100ms for 20 bars

### Success Criteria

- [ ] API endpoint `/api/threshold-bars` accepts symbol, group, timeframe, threshold parameters
- [ ] API returns JSON with segment percentages totaling 100%
- [ ] Frontend renders Diverging Threshold Bar with 4 color-coded segments
- [ ] Frontend renders Simple Diverging Bar with 2 color-coded segments
- [ ] Bars scale correctly: 0% (no width) to 50% (half-width from center)
- [ ] Threshold configuration updates bar segmentation dynamically
- [ ] Integration tests validate SP500 aggregation accuracy (500 stocks binned correctly)
- [ ] Responsive design verified on 1920px desktop and 375px mobile
- [ ] Performance targets met: API <50ms, rendering 20 bars <100ms total
- [ ] Admin UI displays threshold bars for SP500, NASDAQ100, Technology sector

---

## All Needed Context

### Context Completeness Check

_"If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

**Validation**: This PRP includes:
- ✅ Exact API endpoint patterns from `src/api/rest/tier_patterns.py` and `admin_cache.py`
- ✅ Database query patterns from `src/infrastructure/database/tickstock_db.py` for OHLCV access
- ✅ RelationshipCache usage from `src/core/services/relationship_cache.py` for universe symbol loading
- ✅ Frontend rendering patterns from `web/static/js/core/chart-manager.js` and `web/static/css/components/pattern-flow.css`
- ✅ Testing patterns from `tests/api/rest/test_tickstockpl_api_refactor.py` and `tests/fixtures/market_data_fixtures.py`
- ✅ TickStock-specific gotchas: read-only database access, RelationshipCache for symbols, percentage-based bar rendering

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    # Not used for threshold bars (read-only data from database)
    - channel: "N/A"
      purpose: "Threshold bars use database queries only"

  database_access:
    mode: read-only
    tables:
      - ohlcv_1min  # Intraday data
      - ohlcv_hourly  # Hourly bars
      - ohlcv_daily  # Daily bars
      - ohlcv_weekly  # Weekly bars
      - ohlcv_monthly  # Monthly bars
      - definition_groups  # Universe/ETF/sector definitions
      - group_memberships  # Symbol memberships
    queries:
      - "SELECT close FROM ohlcv_daily WHERE symbol IN (...) AND date >= ..."
      - "SELECT close FROM ohlcv_1min WHERE symbol IN (...) AND timestamp >= ..."
      - "Time-based filtering with parameterized queries"
      - "Multi-symbol aggregation using IN clause"

  websocket_integration:
    broadcast_to: "N/A - read-only visualization, no WebSocket updates"
    message_format: "N/A"

  tickstockpl_api:
    endpoints: []  # No TickStockPL integration required
    format: "N/A"

  performance_targets:
    - metric: "API response time (threshold-bars endpoint)"
      target: "<50ms for single group (e.g., SP500)"

    - metric: "Database query time"
      target: "<30ms for multi-symbol OHLCV fetch"

    - metric: "Frontend rendering time"
      target: "<100ms for 20 bar instances"

    - metric: "Memory usage"
      target: "<50MB for page with 20 bars"
```

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# TickStockAppV2 Codebase Patterns
- file: src/api/rest/tier_patterns.py
  why: "Blueprint structure, route registration, query parameter handling"
  pattern: "Lines 41-136 (daily patterns endpoint), 382-477 (hourly patterns endpoint)"
  gotcha: "Always use @login_required decorator, return jsonify() for JSON responses"

- file: src/api/rest/admin_cache.py
  why: "Admin endpoint pattern with RelationshipCache integration"
  pattern: "Lines 20-43 (cache stats), 125-195 (cache test endpoint)"
  gotcha: "Use get_relationship_cache() singleton, cache warm/refresh patterns"

- file: src/infrastructure/database/tickstock_db.py
  why: "Database connection pool, query execution patterns"
  pattern: "Lines 105-123 (context manager), 124-148 (execute_query helper)"
  gotcha: "ALWAYS use get_connection() context manager, never manual close()"

- file: src/core/services/relationship_cache.py
  why: "Universe/ETF/sector symbol loading with <1ms cache hits"
  pattern: "Lines 429-484 (get_universe_symbols for multi-universe join)"
  gotcha: "Supports 'sp500:nasdaq100' syntax for distinct union, returns sorted list"

- file: src/api/rest/api.py
  why: "API endpoint patterns for chart data"
  pattern: "Lines 143-165 (recent ticks query), 446-490 (chart-data endpoint)"
  gotcha: "Use tickstock_db.get_connection() for queries, parameterized SQL only"

# Frontend Patterns
- file: web/static/js/core/chart-manager.js
  why: "Chart.js integration, data fetching patterns"
  pattern: "Lines 81-107 (async loadChartData), 122-191 (Chart.js initialization)"
  gotcha: "Use fetch() with CSRF token header, update charts with chart.update()"

- file: web/static/css/components/pattern-flow.css
  why: "Responsive flexbox grid layouts, mobile-first design"
  pattern: "Lines 70-137 (multi-column responsive grid with media queries)"
  gotcha: "Use flex-basis for proportional sizing, flex-shrink: 0 on center lines"

- file: web/static/css/components/gauges.css
  why: "Progress bar and percentage-based visualization patterns"
  pattern: "Lines 1-50 (gauge container styling, percentage fills)"
  gotcha: "Use percentage widths, transition: width 0.3s ease for smooth updates"

# Testing Patterns
- file: tests/api/rest/test_tickstockpl_api_refactor.py
  why: "Flask API endpoint testing structure"
  pattern: "Lines 24-47 (setup_method), 217-226 (auth testing), 310-317 (database mocking)"
  gotcha: "Use Mock(spec=CacheControl) for cache_control, disable CSRF in tests"

- file: tests/fixtures/market_data_fixtures.py
  why: "OHLCV test data generation patterns"
  pattern: "Lines 48-82 (create_ohlcv_data factory), 352-401 (batch data generator)"
  gotcha: "Use realistic OHLCV relationships (high >= low, close between open/high/low)"

- file: tests/integration/test_sprint61_universe_loading.py
  why: "RelationshipCache usage in tests, multi-universe join validation"
  pattern: "Lines 22-33 (single universe), 61-83 (multi-universe join), 132-153 (performance)"
  gotcha: "Verify sorted results, distinct unions, <1ms cache hit performance"

# External Documentation
- url: https://pandas.pydata.org/docs/reference/api/pandas.core.resample.Resampler.ohlc.html
  why: "Pandas OHLCV resampling for time-based aggregations"
  critical: "Use .resample('D').ohlc() for daily bars from 1-minute data"

- url: https://docs.sqlalchemy.org/en/20/orm/queryguide/select
  why: "SQLAlchemy 2.0 select() construct for OHLCV queries"
  critical: "Use select() instead of legacy Query API, always close sessions"

- url: https://blog.scottlogic.com/2020/10/09/charts-with-flexbox.html
  why: "Flexbox diverging bar chart implementation patterns"
  critical: "Use nested flex containers, percentage-based widths, order property"

- url: https://flask.palletsprojects.com/en/3.0.x/patterns/javascript/
  why: "Flask + JavaScript integration patterns"
  critical: "Pass CSRF token in fetch() headers, use jsonify() for responses"
```

### Current Codebase tree (relevant sections)

```bash
C:\Users\McDude\TickStockAppV2\
├── src/
│   ├── api/
│   │   └── rest/
│   │       ├── __init__.py
│   │       ├── api.py                           # Chart data endpoints
│   │       ├── tier_patterns.py                 # Pattern endpoint blueprint
│   │       ├── admin_cache.py                   # Cache management endpoints
│   │       └── main.py                          # Blueprint registration
│   ├── core/
│   │   └── services/
│   │       ├── relationship_cache.py            # Universe/ETF symbol loading
│   │       └── config_manager.py                # Configuration access
│   ├── infrastructure/
│   │   └── database/
│   │       ├── tickstock_db.py                  # Database connection pool
│   │       └── connection_pool.py               # Connection management
│   └── app.py                                   # Main Flask application
│
├── web/
│   ├── templates/
│   │   ├── dashboard/
│   │   │   └── index.html                       # Dashboard landing page
│   │   └── admin/
│   │       └── monitoring_dashboard.html        # Admin metrics display
│   └── static/
│       ├── js/
│       │   ├── core/
│       │   │   └── chart-manager.js             # Chart.js wrapper
│       │   └── services/
│       │       └── pattern-visualization.js     # Pattern rendering
│       └── css/
│           └── components/
│               ├── pattern-flow.css             # Responsive grid layouts
│               └── gauges.css                   # Progress bar styles
│
└── tests/
    ├── api/
    │   └── rest/
    │       └── test_tickstockpl_api_refactor.py # API testing patterns
    ├── fixtures/
    │   └── market_data_fixtures.py              # OHLCV test data
    └── integration/
        └── test_sprint61_universe_loading.py   # RelationshipCache tests
```

### Desired Codebase tree with files to be added and responsibility

```bash
C:\Users\McDude\TickStockAppV2\
├── src/
│   ├── api/
│   │   └── rest/
│   │       └── threshold_bars.py                # NEW: API endpoint blueprint
│   │           # Responsibilities:
│   │           # - GET /api/threshold-bars route with query params
│   │           # - Call ThresholdBarService for data aggregation
│   │           # - Return JSON with segment percentages
│   │
│   └── core/
│       └── services/
│           └── threshold_bar_service.py         # NEW: Business logic service
│               # Responsibilities:
│               # - Load symbols from RelationshipCache
│               # - Query OHLCV data from database
│               # - Calculate percentage changes
│               # - Bin values into 2 or 4 segments
│               # - Return aggregated percentages
│
├── web/
│   ├── templates/
│   │   └── admin/
│   │       └── market_overview.html             # NEW: Threshold bars admin page
│   │           # Responsibilities:
│   │           # - Container divs for threshold bar instances
│   │           # - Import threshold-bar-renderer.js
│   │           # - Initialize bars on page load
│   │
│   └── static/
│       ├── js/
│       │   └── components/
│       │       └── threshold-bar-renderer.js    # NEW: Frontend rendering module
│       │           # Responsibilities:
│       │           # - Fetch data from /api/threshold-bars
│       │           # - Render diverging bars using DOM manipulation
│       │           # - Handle configuration (type, threshold, colors)
│       │           # - Support static and dynamic update modes
│       │
│       └── css/
│           └── components/
│               └── threshold-bars.css           # NEW: Bar styling
│                   # Responsibilities:
│                   # - Flexbox layout for diverging bars
│                   # - Responsive design (horizontal/vertical)
│                   # - Color gradients for segments
│                   # - Mobile media queries
│
└── tests/
    ├── api/
    │   └── rest/
    │       └── test_threshold_bars_api.py       # NEW: API endpoint tests
    │           # Responsibilities:
    │           # - Test query parameter validation
    │           # - Test JSON response structure
    │           # - Test error handling (404, 400, 500)
    │
    ├── core/
    │   └── services/
    │       └── test_threshold_bar_service.py    # NEW: Service unit tests
    │           # Responsibilities:
    │           # - Test binning logic with mock data
    │           # - Test percentage calculations
    │           # - Test edge cases (empty data, all same value)
    │
    └── integration/
        └── test_threshold_bars_e2e.py           # NEW: End-to-end tests
            # Responsibilities:
            # - Test database → service → API → JSON flow
            # - Test SP500 aggregation accuracy
            # - Test performance (<50ms API, <100ms rendering)
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: TickStockAppV2 is CONSUMER ONLY
# - Read-only database access for OHLCV data
# - No pattern detection logic (belongs in TickStockPL)
# - No OHLCV aggregation beyond what's needed for visualization

# CRITICAL: Database Connection Management
# - ALWAYS use context manager: with db.get_connection() as conn:
# - NEVER call conn.close() manually
# - Connection pool: QueuePool with pool_size=5, max_overflow=2
# File: src/infrastructure/database/tickstock_db.py lines 58-73, 105-123

# CRITICAL: RelationshipCache Usage (Sprint 60/61)
# - Use get_relationship_cache() singleton
# - Multi-universe join: cache.get_universe_symbols('sp500:nasdaq100')
# - Returns sorted list of distinct symbols
# - <1ms cache hit, <10ms cache miss performance
# File: src/core/services/relationship_cache.py lines 429-484

# CRITICAL: OHLCV Query Performance
# - ALWAYS include symbol in WHERE clause (TimescaleDB chunk exclusion)
# - Use LIMIT clause to control result set size
# - Use parameterized queries (:symbol, :since) to prevent SQL injection
# - Example: Lines 143-165 in src/api/rest/api.py

# CRITICAL: Flask JSON Responses
# - ALWAYS use jsonify() for JSON responses (sets Content-Type header)
# - NEVER return raw dicts in Flask <2.2
# - Include error handling with proper HTTP status codes (400, 404, 500)
# File: src/api/rest/tier_patterns.py lines 415-428 (error handlers)

# CRITICAL: Frontend Performance
# - Use DocumentFragment for batch DOM updates (>10 elements)
# - Debounce resize events (250ms minimum)
# - Limit instances per page (<20 threshold bars)
# - Use percentage widths, not fixed pixels

# CRITICAL: Pandas OHLCV Resampling
# - Use .resample('D').ohlc() for daily aggregation from 1-minute data
# - ALWAYS set timestamp as index: df.set_index('timestamp', inplace=True)
# - Avoid iteration: use vectorized operations (.apply, .agg)

# CRITICAL: Percentage Calculation Edge Cases
# - Division by zero: Handle threshold=0 case
# - All values same: Returns 100% in one segment
# - Empty dataset: Return {"error": "No data available"}
# - Validate percentage sum = 100% before returning

# CRITICAL: Testing Patterns
# - Mock RelationshipCache in unit tests
# - Use real database in integration tests (test_pattern_flow_complete.py pattern)
# - Generate realistic OHLCV data (high >= low, close between)
# File: tests/fixtures/market_data_fixtures.py lines 48-82

# CRITICAL: CSS Flexbox Diverging Bars
# - Use nested flex containers (outer: row, inner: bar segments)
# - Set flex-shrink: 0 on center baseline to prevent compression
# - Use order property for visual reordering (decline segments first)
# - Calculate widths as percentage (0-50% from center)

# CRITICAL: Flask Application Context (TickStock-Specific)
# - Use current_app for runtime access to RelationshipCache
# - Don't assume module-level globals are accessible in routes
# Pattern: from flask import current_app; cache = getattr(current_app, 'relationship_cache')
# File: src/api/rest/main.py line 28 (blueprint registration pattern)
```

---

## Implementation Blueprint

### Data models and structure

```python
# Pydantic models for request validation and response serialization

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional
from enum import Enum

class BarType(str, Enum):
    """Threshold bar visualization types"""
    DIVERGING_THRESHOLD = "DivergingThresholdBar"
    SIMPLE_DIVERGING = "SimpleDivergingBar"

class Timeframe(str, Enum):
    """Supported OHLCV timeframes"""
    INTRADAY = "intraday"
    DAILY = "daily"
    HOURLY = "hourly"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

class ThresholdBarRequest(BaseModel):
    """API request parameters for threshold bar data"""

    # Data source: single symbol or group key
    data_source: str = Field(..., description="Symbol (AAPL) or group (SP500, nasdaq100, XLK)")

    # Bar configuration
    bar_type: BarType = Field(default=BarType.DIVERGING_THRESHOLD)
    timeframe: Timeframe = Field(default=Timeframe.DAILY)
    threshold: float = Field(default=0.10, ge=0.0, le=1.0, description="Threshold as decimal (0.10 = 10%)")

    # Optional filters
    period_days: Optional[int] = Field(default=1, ge=1, le=365, description="Number of days/periods to analyze")

    @validator('threshold')
    def validate_threshold_range(cls, v):
        """Ensure threshold is reasonable (0-100%)"""
        if v < 0 or v > 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0 (0% to 100%)")
        return v

class DivergingThresholdSegments(BaseModel):
    """4-segment distribution for Diverging Threshold Bar"""
    significant_decline: float = Field(..., ge=0, le=100)
    minor_decline: float = Field(..., ge=0, le=100)
    minor_advance: float = Field(..., ge=0, le=100)
    significant_advance: float = Field(..., ge=0, le=100)

    @validator('significant_advance')
    def validate_sum_100(cls, v, values):
        """Ensure all segments sum to 100%"""
        total = (
            values.get('significant_decline', 0) +
            values.get('minor_decline', 0) +
            values.get('minor_advance', 0) +
            v
        )
        if not (99.9 <= total <= 100.1):  # Allow floating point tolerance
            raise ValueError(f"Segments must sum to 100%, got {total:.2f}%")
        return v

class SimpleDivergingSegments(BaseModel):
    """2-segment distribution for Simple Diverging Bar"""
    decline: float = Field(..., ge=0, le=100)
    advance: float = Field(..., ge=0, le=100)

    @validator('advance')
    def validate_sum_100(cls, v, values):
        """Ensure segments sum to 100%"""
        total = values.get('decline', 0) + v
        if not (99.9 <= total <= 100.1):
            raise ValueError(f"Segments must sum to 100%, got {total:.2f}%")
        return v

class ThresholdBarResponse(BaseModel):
    """API response with threshold bar data"""

    # Request echo
    data_source: str
    bar_type: BarType
    timeframe: Timeframe
    threshold: float

    # Aggregated data
    segments: DivergingThresholdSegments | SimpleDivergingSegments

    # Metadata
    symbol_count: int = Field(..., description="Number of symbols included in aggregation")
    calculation_time_ms: float = Field(..., description="Backend calculation time in milliseconds")

    # Optional: Individual symbol data for drill-down
    symbols_data: Optional[list[dict]] = Field(default=None, description="Per-symbol breakdown (optional)")

# ORM models (if database storage needed for cached bar data)
# NOTE: Threshold bars are calculated on-demand, no database storage required
# This is here for reference if future caching is needed

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ThresholdBarCache(Base):
    """
    OPTIONAL: Cached threshold bar calculations
    Use only if real-time calculation becomes performance bottleneck
    """
    __tablename__ = 'threshold_bar_cache'

    id = Column(Integer, primary_key=True)
    data_source = Column(String(50), nullable=False)  # 'SP500', 'nasdaq100', etc.
    bar_type = Column(String(30), nullable=False)
    timeframe = Column(String(20), nullable=False)
    threshold = Column(Float, nullable=False)

    segments = Column(JSON, nullable=False)  # Serialized segment percentages
    symbol_count = Column(Integer, nullable=False)

    calculated_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Composite index for fast lookups
    __table_args__ = (
        Index('idx_threshold_cache_lookup', 'data_source', 'bar_type', 'timeframe', 'threshold'),
    )
```

### Implementation Tasks (ordered by dependencies)

```yaml
# PHASE 1: Backend Service Layer

Task 1: CREATE src/core/services/threshold_bar_service.py
  - IMPLEMENT: ThresholdBarService class with aggregation logic
  - FOLLOW pattern: src/core/services/universe_service.py (service structure)
  - NAMING: ThresholdBarService class, calculate_threshold_bars() method
  - DATABASE ACCESS: Read-only queries via TickStockDatabase.get_connection()
  - DEPENDENCIES: RelationshipCache for symbol loading, TickStockDatabase for OHLCV queries
  - PLACEMENT: Core services layer in src/core/services/
  - KEY METHODS:
    * calculate_threshold_bars(data_source, bar_type, timeframe, threshold, period_days)
    * _load_symbols_for_data_source(data_source) - Use RelationshipCache
    * _query_ohlcv_data(symbols, timeframe, period_days) - SQL query
    * _calculate_percentage_changes(ohlcv_data, threshold) - Pandas vectorized
    * _bin_into_segments(percentage_changes, bar_type, threshold) - pd.cut()
    * _aggregate_segment_percentages(binned_data) - Calculate final percentages
  - GOTCHA: Handle edge cases (empty data, all same value, division by zero)
  - CRITICAL: Ensure percentage sum = 100% (validate in response model)

Task 2: CREATE Pydantic models for request/response
  - CREATE: Models in Task 1 file or separate src/api/rest/schemas/threshold_bars.py
  - IMPLEMENT: ThresholdBarRequest, ThresholdBarResponse, segment models
  - FOLLOW pattern: Pydantic models with Field() validators
  - VALIDATION: threshold range, segment sum = 100%, timeframe enum
  - GOTCHA: Allow floating point tolerance (99.9-100.1%) in sum validation

Task 3: ADD unit tests for ThresholdBarService
  - CREATE: tests/core/services/test_threshold_bar_service.py
  - IMPLEMENT: Test binning logic with mock OHLCV data
  - FOLLOW pattern: tests/api/rest/test_tickstockpl_api_refactor.py (Mock patterns)
  - TEST COVERAGE:
    * Happy path: SP500 with 500 symbols → correct percentages
    * Edge cases: Empty data, all same value, single symbol
    * Threshold variations: 0%, 5%, 10%, 20%
    * Timeframes: intraday, daily, weekly
  - MOCK: RelationshipCache, TickStockDatabase
  - ASSERTIONS: Percentage sum = 100%, segment values >= 0

# PHASE 2: API Layer

Task 4: CREATE src/api/rest/threshold_bars.py
  - IMPLEMENT: Flask Blueprint with GET /api/threshold-bars route
  - FOLLOW pattern: src/api/rest/tier_patterns.py (Blueprint structure, lines 41-136)
  - NAMING: threshold_bars_bp Blueprint, get_threshold_bars() route function
  - ROUTE: @threshold_bars_bp.route('/api/threshold-bars', methods=['GET'])
  - DECORATORS: @login_required (from flask_login)
  - QUERY PARAMS: data_source, bar_type, timeframe, threshold, period_days
  - CALL: ThresholdBarService.calculate_threshold_bars()
  - RESPONSE: jsonify(ThresholdBarResponse.dict())
  - ERROR HANDLING: Try-except with 400 (bad request), 404 (not found), 500 (server error)
  - PLACEMENT: API layer in src/api/rest/
  - GOTCHA: Use ThresholdBarRequest for validation, catch pydantic.ValidationError

Task 5: REGISTER Blueprint in src/api/rest/main.py
  - MODIFY: src/api/rest/main.py (existing file)
  - FOLLOW pattern: Line 28 register_main_routes() for function-based registration
  - ALTERNATIVE: Use app.register_blueprint() pattern (lines 2264-2332 in src/app.py)
  - ADD: from src.api.rest.threshold_bars import threshold_bars_bp
  - REGISTER: app.register_blueprint(threshold_bars_bp)
  - PLACEMENT: After other blueprint registrations
  - GOTCHA: Ensure blueprint registered before app.run()

Task 6: ADD API endpoint tests
  - CREATE: tests/api/rest/test_threshold_bars_api.py
  - IMPLEMENT: Flask test client with mocked ThresholdBarService
  - FOLLOW pattern: tests/api/rest/test_tickstockpl_api_refactor.py (lines 24-47 setup, 217-226 auth)
  - TEST COVERAGE:
    * Happy path: Valid query params → 200 JSON response
    * Validation: Invalid threshold → 400 error
    * Not found: Unknown data_source → 404 error
    * Auth: Unauthenticated → 401 redirect
    * Performance: Response time <50ms
  - MOCK: ThresholdBarService.calculate_threshold_bars()
  - ASSERTIONS: Response status, JSON structure, error messages

# PHASE 3: Frontend Rendering

Task 7: CREATE web/static/css/components/threshold-bars.css
  - IMPLEMENT: Flexbox-based diverging bar styles
  - FOLLOW pattern: web/static/css/components/pattern-flow.css (lines 70-137 responsive grid)
  - KEY STYLES:
    * .threshold-bar-container (outer wrapper)
    * .threshold-bar-row (single bar instance)
    * .threshold-bar-label (symbol/group name)
    * .threshold-bar-segments (flexbox container for bar)
    * .threshold-bar-segment (individual segment with color)
    * .threshold-bar-value (percentage text)
  - RESPONSIVE: Media queries for mobile (<768px) → vertical orientation option
  - COLORS:
    * Diverging Threshold: significant_decline (#B22222), minor_decline (#FF6347),
                           minor_advance (#90EE90), significant_advance (#228B22)
    * Simple Diverging: decline (#FF0000), advance (#00FF00)
  - GOTCHA: Use flex-shrink: 0 on center baseline, percentage widths only

Task 8: CREATE web/static/js/components/threshold-bar-renderer.js
  - IMPLEMENT: JavaScript module for fetching and rendering bars
  - FOLLOW pattern: web/static/js/core/chart-manager.js (lines 81-107 fetch, 259-291 DOM update)
  - KEY FUNCTIONS:
    * async fetchThresholdData(dataSource, barType, timeframe, threshold)
    * renderThresholdBar(containerId, config, data)
    * updateThresholdBar(containerId, data) - For dynamic mode
    * calculateSegmentWidths(segments, maxWidth = 50) - Scale 0-50%
  - DOM MANIPULATION: Use DocumentFragment for batch updates
  - ERROR HANDLING: Try-catch with user-friendly error messages
  - GOTCHA: Include CSRF token in fetch() headers, use await/async

Task 9: CREATE web/templates/admin/market_overview.html
  - IMPLEMENT: Admin page with threshold bar displays
  - FOLLOW pattern: web/templates/admin/monitoring_dashboard.html (metric cards, responsive layout)
  - HTML STRUCTURE:
    * Container divs for each bar group (SP500, NASDAQ100, sectors)
    * <div id="threshold-bar-sp500" class="threshold-bar-container"></div>
    * <script src="/static/js/components/threshold-bar-renderer.js"></script>
  - INITIALIZATION:
    * DOMContentLoaded event listener
    * Call renderThresholdBar() for each container
  - LAYOUT: Grid layout for multiple bars (3-4 per row on desktop)
  - GOTCHA: Ensure script loads after DOM elements

Task 10: ADD frontend integration
  - MODIFY: web/templates/dashboard/index.html (existing dashboard)
  - ADD: Link to Market Overview page
  - ALTERNATIVE: Embed threshold bars directly in dashboard
  - FOLLOW pattern: Existing navigation structure
  - GOTCHA: Check Flask route registration for new page

# PHASE 4: Integration Testing

Task 11: CREATE tests/integration/test_threshold_bars_e2e.py
  - IMPLEMENT: End-to-end test for database → API → rendering flow
  - FOLLOW pattern: tests/integration/test_pattern_flow_complete.py (lines 29-359)
  - TEST WORKFLOW:
    * Load SP500 symbols from RelationshipCache
    * Query OHLCV data from real database (or test database)
    * Call API endpoint /api/threshold-bars?data_source=SP500
    * Validate JSON response structure
    * Verify segment percentages sum to 100%
    * Check performance <50ms API response
  - ASSERTIONS:
    * Response status = 200
    * symbol_count = 500 (or actual SP500 size)
    * segments sum = 100%
    * calculation_time_ms < 50
  - GOTCHA: Use test database if available, real database otherwise

Task 12: ADD performance validation tests
  - CREATE: tests/performance/test_threshold_bars_performance.py
  - IMPLEMENT: Load testing with concurrent requests
  - FOLLOW pattern: tests/api/sprint_16/test_market_movers_api_refactor.py (lines 266-308 concurrent)
  - TEST COVERAGE:
    * Single request: <50ms API response
    * 10 concurrent requests: <100ms average, <200ms max
    * Frontend rendering: 20 bars <100ms total
    * Memory usage: <50MB for page with 20 bars
  - TOOLS: time.perf_counter() for timing, threading for concurrent requests
  - ASSERTIONS: All timing targets met

# PHASE 5: Documentation & Deployment

Task 13: UPDATE CLAUDE.md with Sprint 64 status
  - MODIFY: CLAUDE.md (lines 328-352 for usage examples)
  - ADD: Threshold bars usage section
  - DOCUMENT: API endpoint, configuration options, frontend integration
  - EXAMPLE CODE: Show how to use threshold bars in custom pages

Task 14: CREATE Sprint 64 completion documentation
  - CREATE: docs/planning/sprints/sprint64/SPRINT64_COMPLETE.md
  - DOCUMENT: Implementation results, performance metrics, lessons learned
  - INCLUDE: Screenshots of threshold bars in Market Overview page
  - NOTE: Any deferred work for BACKLOG.md
```

### Implementation Patterns & Key Details

```python
# Pattern 1: ThresholdBarService - Core Calculation Logic
# File: src/core/services/threshold_bar_service.py

import logging
import time
from typing import List, Dict
import pandas as pd
import numpy as np

from src.core.services.relationship_cache import get_relationship_cache
from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)

class ThresholdBarService:
    """Service for calculating threshold bar data from OHLCV aggregations"""

    def __init__(self):
        self.cache = get_relationship_cache()
        self.config = get_config()
        self.db = TickStockDatabase(self.config)

    def calculate_threshold_bars(
        self,
        data_source: str,
        bar_type: str,
        timeframe: str,
        threshold: float,
        period_days: int = 1
    ) -> Dict:
        """
        Calculate threshold bar data for a data source.

        PATTERN: Load symbols → Query OHLCV → Calculate changes → Bin → Aggregate
        PERFORMANCE: Target <50ms total
        """
        start_time = time.perf_counter()

        try:
            # Step 1: Load symbols from RelationshipCache
            symbols = self._load_symbols_for_data_source(data_source)
            if not symbols:
                raise ValueError(f"No symbols found for data source: {data_source}")

            logger.info(f"Loaded {len(symbols)} symbols for {data_source}")

            # Step 2: Query OHLCV data from database
            ohlcv_data = self._query_ohlcv_data(symbols, timeframe, period_days)
            if ohlcv_data.empty:
                raise ValueError(f"No OHLCV data found for {data_source} in {timeframe}")

            # Step 3: Calculate percentage changes
            percentage_changes = self._calculate_percentage_changes(ohlcv_data, timeframe)

            # Step 4: Bin into segments
            binned_data = self._bin_into_segments(percentage_changes, bar_type, threshold)

            # Step 5: Aggregate segment percentages
            segments = self._aggregate_segment_percentages(binned_data, bar_type)

            calculation_time = (time.perf_counter() - start_time) * 1000

            return {
                'data_source': data_source,
                'bar_type': bar_type,
                'timeframe': timeframe,
                'threshold': threshold,
                'segments': segments,
                'symbol_count': len(symbols),
                'calculation_time_ms': round(calculation_time, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating threshold bars: {e}")
            raise

    def _load_symbols_for_data_source(self, data_source: str) -> List[str]:
        """
        Load symbols from RelationshipCache.

        CRITICAL: Supports single symbol, universe keys, ETF symbols
        Examples: 'AAPL', 'sp500', 'nasdaq100', 'SPY', 'sp500:nasdaq100'
        """
        data_source_upper = data_source.upper()

        # Check if single symbol
        if not ':' in data_source and len(data_source) <= 5:
            # Treat as single symbol
            return [data_source_upper]

        # Try loading as universe/ETF from cache
        try:
            symbols = self.cache.get_universe_symbols(data_source)
            if symbols:
                return symbols
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")

        # Fallback: treat as single symbol
        return [data_source_upper]

    def _query_ohlcv_data(
        self,
        symbols: List[str],
        timeframe: str,
        period_days: int
    ) -> pd.DataFrame:
        """
        Query OHLCV data from database.

        CRITICAL: Use parameterized queries, include symbol in WHERE for performance
        PATTERN: Follow src/api/rest/api.py lines 143-165
        """
        # Map timeframe to table
        table_map = {
            'intraday': 'ohlcv_1min',
            'hourly': 'ohlcv_hourly',
            'daily': 'ohlcv_daily',
            'weekly': 'ohlcv_weekly',
            'monthly': 'ohlcv_monthly'
        }
        table_name = table_map.get(timeframe, 'ohlcv_daily')

        # Calculate time range
        from datetime import datetime, timedelta
        if timeframe == 'intraday':
            # Since market open today
            since_date = datetime.now().replace(hour=9, minute=30, second=0)
        else:
            since_date = datetime.now() - timedelta(days=period_days)

        # Build query with IN clause for multi-symbol
        placeholders = ','.join(['%s'] * len(symbols))
        query = f"""
            SELECT symbol, timestamp, close
            FROM {table_name}
            WHERE symbol IN ({placeholders})
              AND timestamp >= %s
            ORDER BY symbol, timestamp DESC
        """

        params = symbols + [since_date]

        # Execute query
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def _calculate_percentage_changes(
        self,
        ohlcv_data: pd.DataFrame,
        timeframe: str
    ) -> pd.Series:
        """
        Calculate percentage change for each symbol.

        PATTERN: Use pandas vectorized operations, avoid iteration
        FORMULA: ((current_close - previous_close) / previous_close) * 100
        """
        # Group by symbol and calculate change
        def calc_pct_change(group):
            if len(group) < 2:
                return 0.0  # No change if only 1 data point

            latest = group.iloc[0]['close']  # Most recent (ORDER BY timestamp DESC)
            previous = group.iloc[-1]['close']  # Earliest in period

            if previous == 0:
                return 0.0  # Avoid division by zero

            return ((latest - previous) / previous) * 100

        pct_changes = ohlcv_data.groupby('symbol').apply(calc_pct_change)
        return pct_changes

    def _bin_into_segments(
        self,
        percentage_changes: pd.Series,
        bar_type: str,
        threshold: float
    ) -> pd.Series:
        """
        Bin percentage changes into segments using pd.cut().

        CRITICAL: Follow logic gates from reference document
        """
        threshold_pct = threshold * 100  # Convert decimal to percentage

        if bar_type == 'DivergingThresholdBar':
            # 4 segments
            bins = [-float('inf'), -threshold_pct, 0, threshold_pct, float('inf')]
            labels = ['significant_decline', 'minor_decline', 'minor_advance', 'significant_advance']
        else:  # SimpleDivergingBar
            # 2 segments
            bins = [-float('inf'), 0, float('inf')]
            labels = ['decline', 'advance']

        binned = pd.cut(percentage_changes, bins=bins, labels=labels)
        return binned

    def _aggregate_segment_percentages(
        self,
        binned_data: pd.Series,
        bar_type: str
    ) -> Dict[str, float]:
        """
        Aggregate binned data into segment percentages.

        CRITICAL: Ensure sum = 100%
        """
        value_counts = binned_data.value_counts()
        total = value_counts.sum()

        if total == 0:
            # Empty data - return 0% for all segments
            if bar_type == 'DivergingThresholdBar':
                return {
                    'significant_decline': 0.0,
                    'minor_decline': 0.0,
                    'minor_advance': 0.0,
                    'significant_advance': 0.0
                }
            else:
                return {'decline': 0.0, 'advance': 0.0}

        # Calculate percentages
        percentages = (value_counts / total * 100).round(2)

        # Ensure all segments present (even if 0%)
        if bar_type == 'DivergingThresholdBar':
            segments = {
                'significant_decline': percentages.get('significant_decline', 0.0),
                'minor_decline': percentages.get('minor_decline', 0.0),
                'minor_advance': percentages.get('minor_advance', 0.0),
                'significant_advance': percentages.get('significant_advance', 0.0)
            }
        else:
            segments = {
                'decline': percentages.get('decline', 0.0),
                'advance': percentages.get('advance', 0.0)
            }

        # Normalize to ensure sum = 100% (handle rounding errors)
        total_pct = sum(segments.values())
        if total_pct > 0 and abs(total_pct - 100.0) > 0.1:
            # Adjust largest segment to make sum exactly 100%
            max_key = max(segments, key=segments.get)
            segments[max_key] = round(segments[max_key] + (100.0 - total_pct), 2)

        return segments


# Pattern 2: Flask API Endpoint
# File: src/api/rest/threshold_bars.py

from flask import Blueprint, request, jsonify
from flask_login import login_required
import logging

from src.core.services.threshold_bar_service import ThresholdBarService
from pydantic import ValidationError

logger = logging.getLogger(__name__)

threshold_bars_bp = Blueprint('threshold_bars', __name__)

@threshold_bars_bp.route('/api/threshold-bars', methods=['GET'])
@login_required
def get_threshold_bars():
    """
    GET /api/threshold-bars

    Query Parameters:
        - data_source: Symbol or group key (required)
        - bar_type: 'DivergingThresholdBar' or 'SimpleDivergingBar' (default: DivergingThresholdBar)
        - timeframe: 'intraday', 'daily', 'hourly', 'weekly', 'monthly' (default: daily)
        - threshold: Decimal threshold (default: 0.10 = 10%)
        - period_days: Number of days/periods (default: 1)

    Returns:
        JSON with segment percentages

    PATTERN: Parse params → Call service → Return JSON
    GOTCHA: Validate threshold range, handle service exceptions
    """
    try:
        # Parse query parameters
        data_source = request.args.get('data_source')
        if not data_source:
            return jsonify({'error': 'data_source parameter required'}), 400

        bar_type = request.args.get('bar_type', 'DivergingThresholdBar')
        timeframe = request.args.get('timeframe', 'daily')
        threshold = float(request.args.get('threshold', 0.10))
        period_days = int(request.args.get('period_days', 1))

        # Validate threshold
        if threshold < 0 or threshold > 1.0:
            return jsonify({'error': 'threshold must be between 0.0 and 1.0'}), 400

        # Call service
        service = ThresholdBarService()
        result = service.calculate_threshold_bars(
            data_source=data_source,
            bar_type=bar_type,
            timeframe=timeframe,
            threshold=threshold,
            period_days=period_days
        )

        # Return JSON response
        return jsonify(result), 200

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in threshold-bars endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@threshold_bars_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@threshold_bars_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


# Pattern 3: Frontend JavaScript Renderer
# File: web/static/js/components/threshold-bar-renderer.js

/**
 * Threshold Bar Renderer
 *
 * Fetches threshold bar data from API and renders diverging bars using pure HTML/CSS/JS.
 *
 * PATTERN: Fetch → Parse → Render DOM
 * GOTCHA: Use DocumentFragment for batch updates, include CSRF token
 */

class ThresholdBarRenderer {
    constructor() {
        this.csrfToken = window.csrfToken || '';
    }

    /**
     * Fetch threshold bar data from API
     *
     * PATTERN: Follow web/static/js/core/chart-manager.js lines 81-107
     */
    async fetchThresholdData(dataSource, barType = 'DivergingThresholdBar', timeframe = 'daily', threshold = 0.10) {
        try {
            const params = new URLSearchParams({
                data_source: dataSource,
                bar_type: barType,
                timeframe: timeframe,
                threshold: threshold
            });

            const response = await fetch(
                `/api/threshold-bars?${params}`,
                {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': this.csrfToken
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            console.error('Error fetching threshold data:', error);
            throw error;
        }
    }

    /**
     * Render threshold bar in container
     *
     * PATTERN: Create DOM elements with percentage-based widths
     * GOTCHA: Use DocumentFragment for batch updates
     */
    renderThresholdBar(containerId, config, data) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        // Clear existing content
        container.innerHTML = '';

        // Create bar row
        const barRow = document.createElement('div');
        barRow.className = 'threshold-bar-row';

        // Label
        const label = document.createElement('div');
        label.className = 'threshold-bar-label';
        label.textContent = data.data_source;
        barRow.appendChild(label);

        // Segments container
        const segmentsContainer = document.createElement('div');
        segmentsContainer.className = 'threshold-bar-segments';

        // Render segments based on bar type
        if (data.bar_type === 'DivergingThresholdBar') {
            this._renderDivergingThresholdSegments(segmentsContainer, data.segments);
        } else {
            this._renderSimpleDivergingSegments(segmentsContainer, data.segments);
        }

        barRow.appendChild(segmentsContainer);

        // Value (show largest segment percentage)
        const value = document.createElement('div');
        value.className = 'threshold-bar-value';
        const maxSegment = Object.entries(data.segments).reduce((a, b) => a[1] > b[1] ? a : b);
        value.textContent = `${maxSegment[1].toFixed(1)}%`;
        barRow.appendChild(value);

        // Append to container
        container.appendChild(barRow);
    }

    _renderDivergingThresholdSegments(container, segments) {
        /**
         * Render 4-segment diverging bar
         *
         * PATTERN: Decline segments (right-aligned) → Center baseline → Advance segments (left-aligned)
         * GOTCHA: Use flex order property for visual reordering
         */

        // Decline segments (render right-to-left)
        const significantDecline = this._createSegment(
            'significant_decline',
            segments.significant_decline,
            '#B22222'
        );
        significantDecline.style.order = '1';

        const minorDecline = this._createSegment(
            'minor_decline',
            segments.minor_decline,
            '#FF6347'
        );
        minorDecline.style.order = '2';

        // Center baseline
        const baseline = document.createElement('div');
        baseline.className = 'threshold-bar-baseline';
        baseline.style.order = '3';

        // Advance segments (render left-to-right)
        const minorAdvance = this._createSegment(
            'minor_advance',
            segments.minor_advance,
            '#90EE90'
        );
        minorAdvance.style.order = '4';

        const significantAdvance = this._createSegment(
            'significant_advance',
            segments.significant_advance,
            '#228B22'
        );
        significantAdvance.style.order = '5';

        // Append all segments
        container.appendChild(significantDecline);
        container.appendChild(minorDecline);
        container.appendChild(baseline);
        container.appendChild(minorAdvance);
        container.appendChild(significantAdvance);
    }

    _renderSimpleDivergingSegments(container, segments) {
        /**
         * Render 2-segment diverging bar
         */

        const decline = this._createSegment('decline', segments.decline, '#FF0000');
        decline.style.order = '1';

        const baseline = document.createElement('div');
        baseline.className = 'threshold-bar-baseline';
        baseline.style.order = '2';

        const advance = this._createSegment('advance', segments.advance, '#00FF00');
        advance.style.order = '3';

        container.appendChild(decline);
        container.appendChild(baseline);
        container.appendChild(advance);
    }

    _createSegment(name, percentage, color) {
        /**
         * Create segment div with percentage width
         *
         * CRITICAL: Width is percentage of half-bar (0-50%)
         * Scale: 0% → 0px width, 100% → 50% width
         */
        const segment = document.createElement('div');
        segment.className = `threshold-bar-segment segment-${name}`;
        segment.style.backgroundColor = color;

        // Scale to half-width (0-50%)
        const scaledWidth = (percentage / 2).toFixed(2);
        segment.style.width = `${scaledWidth}%`;

        // Add label if segment is large enough
        if (percentage > 5) {
            segment.textContent = `${percentage.toFixed(1)}%`;
        }

        return segment;
    }
}

// Export for use in HTML pages
window.ThresholdBarRenderer = ThresholdBarRenderer;


# Pattern 4: CSS Flexbox Styling
# File: web/static/css/components/threshold-bars.css

/**
 * Threshold Bar Styles
 *
 * PATTERN: Flexbox with percentage-based widths, responsive design
 * GOTCHA: flex-shrink: 0 on baseline, order property for visual reordering
 */

.threshold-bar-container {
    width: 100%;
    margin-bottom: 20px;
}

.threshold-bar-row {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    height: 40px;
}

.threshold-bar-label {
    width: 100px;
    text-align: right;
    padding-right: 15px;
    font-weight: 600;
    font-size: 14px;
    color: #333;
}

.threshold-bar-segments {
    display: flex;
    flex: 1;
    height: 100%;
    position: relative;
    background: #f5f5f5;
    border-radius: 4px;
    overflow: hidden;
}

.threshold-bar-segment {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 12px;
    transition: width 0.3s ease;
}

/* Decline segments align to right of center */
.segment-significant_decline,
.segment-minor_decline,
.segment-decline {
    margin-right: auto;
}

/* Advance segments align to left of center */
.segment-minor_advance,
.segment-significant_advance,
.segment-advance {
    margin-left: auto;
}

.threshold-bar-baseline {
    width: 2px;
    height: 100%;
    background: #333;
    flex-shrink: 0; /* CRITICAL: Don't compress */
    z-index: 10;
}

.threshold-bar-value {
    width: 70px;
    text-align: left;
    padding-left: 15px;
    font-weight: 600;
    font-size: 14px;
    color: #555;
}

/* Responsive: Mobile (<768px) */
@media (max-width: 768px) {
    .threshold-bar-row {
        height: 30px;
    }

    .threshold-bar-label {
        width: 70px;
        font-size: 12px;
        padding-right: 10px;
    }

    .threshold-bar-value {
        width: 50px;
        font-size: 12px;
        padding-left: 10px;
    }

    .threshold-bar-segment {
        font-size: 10px;
    }
}

/* Vertical orientation option (for mobile space-constrained) */
.threshold-bar-container.vertical .threshold-bar-row {
    flex-direction: column;
    height: auto;
}

.threshold-bar-container.vertical .threshold-bar-segments {
    flex-direction: column;
    width: 100%;
    height: 200px;
}

.threshold-bar-container.vertical .threshold-bar-segment {
    width: 100% !important;
    height: auto;
}

.threshold-bar-container.vertical .threshold-bar-baseline {
    width: 100%;
    height: 2px;
}
```

### Integration Points

```yaml
# TickStock-Specific Integration Points

DATABASE:
  # No migrations needed - uses existing OHLCV tables
  - tables_used:
      - ohlcv_1min
      - ohlcv_hourly
      - ohlcv_daily
      - ohlcv_weekly
      - ohlcv_monthly
      - definition_groups (via RelationshipCache)
      - group_memberships (via RelationshipCache)

  # Query patterns
  - query_location: "src/core/services/threshold_bar_service.py"
  - query_pattern: "SELECT symbol, timestamp, close FROM {table} WHERE symbol IN (...) AND timestamp >= ..."
  - performance: "<30ms for multi-symbol OHLCV fetch"

RELATIONSHIPCACHE:
  # Universe/ETF symbol loading
  - usage_location: "src/core/services/threshold_bar_service.py"
  - method_call: "cache.get_universe_symbols(data_source)"
  - supports: "Single symbol, universe keys (sp500, nasdaq100), ETF symbols (SPY), multi-universe join (sp500:nasdaq100)"
  - performance: "<1ms cache hit, <10ms cache miss"

FLASK_BLUEPRINTS:
  # REST API routes
  - blueprint_file: "src/api/rest/threshold_bars.py"
  - blueprint_name: "threshold_bars_bp"
  - register_in: "src/app.py"
  - registration_pattern: |
      from src.api.rest.threshold_bars import threshold_bars_bp
      app.register_blueprint(threshold_bars_bp)

CONFIG:
  # No new environment variables needed
  - existing_config_used:
      - DATABASE_URI (via TickStockDatabase)
      - ENVIRONMENT (via RelationshipCache)

FRONTEND:
  # JavaScript module integration
  - script_file: "web/static/js/components/threshold-bar-renderer.js"
  - css_file: "web/static/css/components/threshold-bars.css"
  - usage_in_templates: |
      <link rel="stylesheet" href="/static/css/components/threshold-bars.css">
      <script src="/static/js/components/threshold-bar-renderer.js"></script>

      <div id="threshold-bar-sp500" class="threshold-bar-container"></div>

      <script>
        const renderer = new ThresholdBarRenderer();
        renderer.fetchThresholdData('SP500', 'DivergingThresholdBar', 'daily', 0.10)
          .then(data => renderer.renderThresholdBar('threshold-bar-sp500', {}, data));
      </script>

ADMIN_UI:
  # New admin page for market overview
  - template_file: "web/templates/admin/market_overview.html"
  - route: "/admin/market-overview"
  - displays:
      - SP500 threshold bar (intraday, daily, weekly)
      - NASDAQ100 threshold bar (intraday, daily, weekly)
      - Sector threshold bars (Technology, Healthcare, Financials, etc.)
  - layout: "Responsive grid, 3-4 bars per row on desktop, 1-2 on mobile"
```

---

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting
# Run after each file creation - fix before proceeding

# File-specific validation
ruff check src/core/services/threshold_bar_service.py --fix
ruff check src/api/rest/threshold_bars.py --fix
ruff format src/core/services/threshold_bar_service.py
ruff format src/api/rest/threshold_bars.py

# Project-wide validation
ruff check src/ --fix
ruff format src/

# Expected: Zero errors. If errors exist, READ output and fix before proceeding.
```

### Level 2: Unit Tests (Component Validation)

```bash
# TickStock Standard: pytest for all testing
# Test each component as it's created

# Service unit tests
python -m pytest tests/core/services/test_threshold_bar_service.py -v

# API endpoint tests
python -m pytest tests/api/rest/test_threshold_bars_api.py -v

# Full unit test suite
python -m pytest tests/unit/ -v

# Coverage validation
python -m pytest tests/unit/ --cov=src.core.services.threshold_bar_service --cov=src.api.rest.threshold_bars --cov-report=term-missing

# Expected: All tests pass, >80% coverage on business logic
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Alternative detailed runner
python tests/integration/run_integration_tests.py

# Threshold bars end-to-end tests
python -m pytest tests/integration/test_threshold_bars_e2e.py -v

# Expected Output:
# - All tests passing
# - API response time <50ms verified
# - Segment percentages sum to 100% validated
# - Frontend rendering <100ms for 20 bars

# Performance tests
python -m pytest tests/performance/test_threshold_bars_performance.py -v

# Expected:
# - Single request: <50ms
# - 10 concurrent: <100ms average, <200ms max
# - Frontend: 20 bars <100ms total
```

### Level 4: TickStock-Specific Validation

```bash
# Architecture Compliance Validation
# CRITICAL: Verify read-only database access pattern

# Database Read-Only Enforcement
# Verify no INSERT, UPDATE, DELETE statements in threshold bar code
grep -r "INSERT INTO\|UPDATE.*SET\|DELETE FROM" src/core/services/threshold_bar_service.py src/api/rest/threshold_bars.py
# Expected: No matches

# RelationshipCache Usage Validation
# Verify cache is used for symbol loading (not direct database queries)
grep -r "get_universe_symbols\|get_etf_holdings" src/core/services/threshold_bar_service.py
# Expected: Matches found (cache usage confirmed)

# API Performance Benchmarking
# Measure actual response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5000/api/threshold-bars?data_source=SP500"
# Expected: total_time < 0.050 (50ms)

# Frontend Performance Testing
# Open browser DevTools, navigate to market overview page
# Check Performance tab for rendering metrics
# Expected: Render complete <100ms for page with 20 bars

# Manual Testing Checklist
# 1. Navigate to /admin/market-overview
# 2. Verify threshold bars render for SP500, NASDAQ100
# 3. Test different timeframes (intraday, daily, weekly)
# 4. Test different thresholds (5%, 10%, 20%)
# 5. Verify responsive design on mobile (375px width)
# 6. Check browser console for errors (should be none)
```

---

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass: `python -m pytest tests/unit/ -v`
- [ ] End-to-end tests pass: `python -m pytest tests/integration/test_threshold_bars_e2e.py -v`

### Feature Validation

- [ ] API endpoint `/api/threshold-bars` returns valid JSON
- [ ] Segment percentages sum to 100% (validated in tests)
- [ ] Diverging Threshold Bar renders 4 segments correctly
- [ ] Simple Diverging Bar renders 2 segments correctly
- [ ] Threshold parameter updates segmentation dynamically
- [ ] Frontend renders 20 bars smoothly (<100ms total)
- [ ] Responsive design works on desktop (1920px) and mobile (375px)
- [ ] Admin UI displays bars for SP500, NASDAQ100, Technology sector

### TickStock Architecture Validation

- [ ] Read-only database access confirmed (no INSERT/UPDATE/DELETE in code)
- [ ] RelationshipCache used for symbol loading (verified via grep)
- [ ] API response time <50ms (measured with curl)
- [ ] Frontend rendering <100ms for 20 bars (DevTools Performance tab)
- [ ] No Redis pub-sub usage (correct for read-only visualization)
- [ ] No TickStockPL integration (correct for database-only feature)

### Code Quality Validation

- [ ] Follows existing codebase patterns (Blueprint, service layer, context manager)
- [ ] File placement matches desired codebase tree structure
- [ ] Code structure limits followed (max 500 lines/file, 50 lines/function)
- [ ] Naming conventions: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- [ ] No hardcoded values (threshold, colors configurable via parameters)
- [ ] Comprehensive error handling (try-except with specific errors)

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Docstrings added for public methods
- [ ] Logs are informative but not verbose
- [ ] CLAUDE.md updated with threshold bars usage examples
- [ ] Sprint 64 completion documentation created

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't hardcode threshold values - use configuration parameters
- ❌ Don't use fixed pixel widths in CSS - use percentages for responsiveness
- ❌ Don't query database in loop - use IN clause for multi-symbol queries
- ❌ Don't skip validation - ensure segment percentages sum to 100%
- ❌ Don't ignore performance targets - measure and verify <50ms API, <100ms rendering

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't write to database from TickStockAppV2**
  - This is a read-only visualization feature
  - All OHLCV data is consumed from existing tables
  - Violation: INSERT INTO ohlcv_* tables

- ❌ **Don't bypass RelationshipCache for symbol loading**
  - Always use cache.get_universe_symbols() for universe/ETF members
  - Never query definition_groups or group_memberships directly
  - Violation: SELECT FROM definition_groups in threshold_bar_service.py

- ❌ **Don't use Redis pub-sub for threshold bars**
  - This feature is database-only (no real-time updates required)
  - Static data visualization updated on page load
  - Violation: Redis subscribe/publish in threshold bar code

#### Data Handling
- ❌ **Don't calculate percentage changes via iteration**
  - Use pandas vectorized operations (.groupby().apply())
  - Avoid for loops over symbols
  - Violation: for symbol in symbols: calculate_change(symbol)

- ❌ **Don't return segment percentages that don't sum to 100%**
  - Always normalize and validate sum = 100%
  - Handle rounding errors by adjusting largest segment
  - Violation: Returning {decline: 45, advance: 54} (sum = 99%)

#### Performance
- ❌ **Don't query OHLCV without symbol filter**
  - Always include symbol IN (...) in WHERE clause
  - TimescaleDB requires symbol for chunk exclusion
  - Violation: SELECT FROM ohlcv_daily WHERE timestamp >= ... (no symbol filter)

- ❌ **Don't render >20 bars without virtualization**
  - DOM performance degrades with too many elements
  - Use pagination or virtual scrolling for large lists
  - Violation: Rendering 100 bars on single page

#### Frontend
- ❌ **Don't use Chart.js for threshold bars**
  - Pure CSS flexbox is sufficient and more performant
  - No need for canvas rendering overhead
  - Violation: new Chart(ctx, {type: 'bar', ...})

- ❌ **Don't update DOM without DocumentFragment for >10 elements**
  - Batch updates to minimize reflows
  - Use DocumentFragment for multiple bar instances
  - Violation: container.appendChild() in loop without fragment

#### Testing
- ❌ **Don't skip performance validation tests**
  - Always measure API response time (<50ms target)
  - Always measure frontend rendering time (<100ms for 20 bars)
  - Violation: Only testing happy path without performance assertions

- ❌ **Don't use hardcoded test data**
  - Generate realistic OHLCV data with proper relationships
  - Use fixtures from tests/fixtures/market_data_fixtures.py
  - Violation: test_data = [{'close': 100}, {'close': 105}] (no high/low/volume)

---

## Confidence Score: 9/10

**Rationale for One-Pass Implementation Success**:

**Strengths**:
- ✅ Complete codebase patterns documented (API, database, frontend, testing)
- ✅ Exact file paths and line numbers for reference patterns
- ✅ TickStock-specific gotchas captured (RelationshipCache, read-only, performance targets)
- ✅ External documentation with specific URLs and code examples
- ✅ Dependency-ordered implementation tasks with clear responsibilities
- ✅ 4-level validation gates with specific commands
- ✅ Edge case handling documented (empty data, division by zero, sum validation)

**Minor Risk (-1 point)**:
- Frontend rendering performance for 20 bars not validated until implementation
- Possible need for pagination/virtualization if >20 bars required (not specified in requirements)
- CSS flexbox diverging bar pattern is novel (not widely documented) - may require iteration on visual design

**Mitigation**:
- Performance tests included in validation loop (Level 3)
- CSS pattern includes responsive design and mobile fallbacks
- Reference implementation from research provides solid foundation

**Overall Assessment**: This PRP provides comprehensive context for successful one-pass implementation. The executing agent has all necessary patterns, gotchas, and validation steps to implement threshold bars without significant pivots.
