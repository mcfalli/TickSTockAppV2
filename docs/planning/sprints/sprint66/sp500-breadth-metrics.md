name: "Market Breadth Metrics Display Control - Sprint 66"
description: |
  Comprehensive PRP for implementing reusable market breadth metrics component with 12 indicator rows
  showing up/down counts across time periods and moving average relationships.

  Generic design supporting any universe (SPY, QQQ, dow30, nasdaq100, etc.)
  Multi-page reusable component appearing 1-to-many times on various pages

  Sprint 66 - February 2026
  Architecture: On-the-fly calculation pattern (Sprint 64)
  Performance Target: <50ms calculation, <100ms API response

---

## Goal

**Feature Goal**: Implement reusable horizontal bar chart display showing market participation breadth across 12 metrics (Day Chg, Week, Month, QTR, Half Year, Year, Price/EMA10, Price/EMA20, Price/SMA50, Price/SMA200) for any stock universe with real-time updates.

**Deliverable**:
- BreadthMetricsService class with 12 calculation methods (universe-agnostic)
- REST API endpoint `/api/breadth-metrics` with universe parameter and Pydantic validation
- Frontend JavaScript renderer as reusable component (configurable title, universe, controls)
- Reusable Jinja2 template supporting multiple instances on same page
- Unit tests (30+ tests), API tests (10+ tests), e2e tests (5+ tests)

**Success Definition**:
- All 12 metrics calculate correctly for ANY universe with <50ms total time
- Frontend displays color-coded bars (green=up/above, red=down/below)
- Component can appear multiple times on same page with different universes
- Auto-refresh every 60 seconds for intraday data
- 100% test passing rate (unit + integration)
- Zero regression on existing tests

## User Persona

**Target User**: Broad-market context trader

**Use Case**: Quick assessment of market internal breadth and trend health across different universes (S&P 500, NASDAQ 100, Dow 30, etc.) before making trading decisions

**User Journey**:
1. Opens TickStock dashboard
2. Sees market breadth displays for multiple universes simultaneously
   - Example: "S&P 500 Breadth" (SPY - 504 stocks)
   - Example: "NASDAQ 100 Breadth" (QQQ - 102 stocks)
   - Example: "Dow 30 Breadth" (dow30 - 30 stocks)
3. Sees 12 horizontal bar chart rows per universe showing up/down participation
4. Identifies market regime differences across universes (tech vs broad market)
5. Makes informed trading decisions based on cross-universe breadth context

**Pain Points Addressed**:
- **Time-consuming manual analysis**: Replaces checking hundreds of individual stocks
- **Lagging indicators**: Real-time calculation from latest OHLCV data
- **Multi-timeframe blindness**: Single view shows Day/Week/Month/Quarter/Year
- **Moving average context missing**: Shows % above key EMAs/SMAs instantly
- **Cross-market comparison difficulty**: Side-by-side breadth views for S&P 500 vs NASDAQ 100 vs Dow 30

## Why

- **Business Value**: Enables traders to identify market regime transitions and divergences across universes (broad participation = sustainable trends)
- **Integration**: Leverages existing Sprint 64 Threshold Bars architecture (proven <50ms performance)
- **User Impact**: Reduces analysis time from 15-30 minutes to <5 seconds
- **Reusability**: Single component serves multiple pages (Market Overview, Sector Analysis, Index Comparison, etc.)
- **Problems Solved**:
  - Traders miss early breadth deterioration signals (divergences)
  - Manual calculation of 500+ stocks infeasible in real-time
  - Lag between market movement and breadth awareness
  - Cross-market breadth comparison requires multiple tools/tabs

## What

**User-Visible Behavior**:
- Reusable component displays 12 horizontal bar chart rows
- Each row shows: Metric label (left) | Green/Red bar (center) | Up/Down counts (right)
- Green bar width = % stocks up/above, Red bar width = % stocks down/below
- Configurable title per instance ("S&P 500 Breadth", "NASDAQ 100 Breadth", "Dow 30 Breadth", etc.)
- Optional universe selector (can be shown or hidden per instance)
- Optional refresh button (configurable per instance)
- Auto-refresh: Intraday data updates every 60 seconds (per instance)
- Loading state: Spinner while calculating
- Error state: Clear error message if calculation fails
- Multiple instances can coexist on same page with independent configurations

**Technical Requirements**:
- Calculate 12 breadth metrics from OHLCV data (no database schema changes)
- Support ANY universe (SPY, QQQ, dow30, nasdaq100, etc.) via RelationshipCache
- Return JSON with up/down/unchanged counts + percentages
- Performance: <50ms calculation, <100ms API response (regardless of universe size)
- Frontend: Pure CSS flexbox bars (no Chart.js dependency)
- Reusable Jinja2 template with instance_id, universe, title, and show_controls parameters
- JavaScript component with configurable options (universe, title, showControls)

**Component Reusability Design**:
```html
<!-- Example: Multiple instances on Market Overview page -->
{% include 'dashboard/market_breadth.html' with instance_id='spy', universe='SPY', title='S&P 500 Breadth' %}
{% include 'dashboard/market_breadth.html' with instance_id='qqq', universe='QQQ', title='NASDAQ 100 Breadth' %}
{% include 'dashboard/market_breadth.html' with instance_id='dow', universe='dow30', title='Dow 30 Breadth', show_controls=False %}
```

### Success Criteria

- [ ] BreadthMetricsService calculates all 12 metrics correctly
- [ ] Moving averages (EMA10, EMA20, SMA50, SMA200) match pandas expected values
- [ ] API endpoint `/api/breadth-metrics` returns valid JSON structure
- [ ] Pydantic validation catches invalid parameters (universe, threshold)
- [ ] Frontend renders 12 metric rows as horizontal bar charts
- [ ] Color coding: Green (#28a745) for up/above, Red (#dc3545) for down/below
- [ ] Auto-refresh works (60s interval for intraday data)
- [ ] Universe selector switches data source (SPY, QQQ, dow30)
- [ ] Unit tests pass (30+ tests covering all calculation methods)
- [ ] API tests pass (10+ tests covering validation and errors)
- [ ] Integration tests pass (5+ e2e tests with real database)
- [ ] Performance validated: <50ms calculation, <100ms API response
- [ ] Ruff linting clean (0 violations)
- [ ] Documentation updated (CLAUDE.md, API docs, SPRINT66_COMPLETE.md)
- [ ] Zero regression: Existing pattern flow tests still pass

## All Needed Context

### Context Completeness Check

_"No Prior Knowledge" Test: If someone knew nothing about this codebase, would they have everything needed to implement this successfully?"_

**Answer**: YES - This PRP includes:
- ✅ Complete Sprint 64 pattern documentation (service, models, API, frontend)
- ✅ Pandas EMA/SMA calculation code with documentation URLs
- ✅ OHLCV database schema and query patterns
- ✅ RelationshipCache integration patterns
- ✅ Frontend rendering patterns (JavaScript + CSS)
- ✅ Flask Blueprint registration pattern
- ✅ Test patterns (unit, API, e2e)
- ✅ Performance optimization techniques
- ✅ Known gotchas and solutions
- ✅ Validation gates (4-level)

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer (read-only)

  redis_channels:
    # NOT USED - Breadth metrics calculate on-demand, no Redis pub-sub
    - channel: "N/A"
      purpose: "Feature calculates directly from OHLCV database"

  database_access:
    mode: read-only
    tables:
      - ohlcv_daily       # Primary data source (252 days × N symbols, where N depends on universe)
      - ohlcv_1min        # Intraday data (not used in initial implementation)
      - definition_groups # Universe definitions (SPY, QQQ, dow30, nasdaq100, etc.)
      - group_memberships # Symbol relationships
    queries:
      - "SELECT symbol, date, close FROM ohlcv_daily WHERE symbol = ANY(%s) AND date >= %s ORDER BY symbol, date"
      - "Parameterized query with array operator (symbol = ANY(%s))"
      - "TimescaleDB chunk exclusion optimization via date filter"
      - "Row counts vary by universe:"
      - "  - SPY: ~127,000 rows (252 days × 504 symbols)"
      - "  - QQQ: ~25,700 rows (252 days × 102 symbols)"
      - "  - dow30: ~7,560 rows (252 days × 30 symbols)"

    universe_loading:
      - "RelationshipCache.get_universe_symbols(universe) → list of symbols"
      - "SPY returns 504 stocks (not 500 - confirmed via database query)"
      - "QQQ returns 102 stocks"
      - "dow30 returns 30 stocks"
      - "Works with ANY universe defined in definition_groups table"

  websocket_integration:
    broadcast_to: []  # NOT USED - No WebSocket broadcasting (REST API only)
    message_format: "N/A"
    latency_target: "N/A"

  tickstockpl_api:
    endpoints: []  # NOT USED - No TickStockPL integration
    format: "N/A"

  performance_targets:
    - metric: "Database query (SPY: 252 days × 504 symbols)"
      target: "<30ms"
      validation: "Measure in unit tests with timing decorator"
    - metric: "Database query (QQQ: 252 days × 102 symbols)"
      target: "<15ms"
      validation: "Smaller universe = faster query"
    - metric: "Database query (dow30: 252 days × 30 symbols)"
      target: "<10ms"
      validation: "Smallest universe = fastest query"

    - metric: "All 12 metrics calculation (pandas vectorized)"
      target: "<30ms"
      validation: "Measure in service tests"

    - metric: "Total service calculation (query + calc)"
      target: "<50ms"
      validation: "Measure in e2e tests with @pytest.mark.performance"

    - metric: "API endpoint response (with JSON serialization)"
      target: "<100ms"
      validation: "Measure in API tests"

    - metric: "Frontend rendering (12 rows)"
      target: "<50ms"
      validation: "Manual browser DevTools Performance tab"
```

### Documentation & References

```yaml
# SPRINT 64 PATTERNS (Primary Reference)
- file: src/core/services/threshold_bar_service.py
  why: "Service layer architecture, dependency injection, 5-step pipeline"
  pattern: "ThresholdBarService class with _load_symbols, _query_ohlcv_data, _calculate_percentage_changes, _bin_into_segments, _aggregate_segment_percentages"
  gotcha: "Time column names vary (timestamp vs date vs week_start), must map correctly"
  lines: "Full file analysis in agent af2b487 output"

- file: src/core/models/threshold_bar_models.py
  why: "Pydantic v2 request/response validation patterns"
  pattern: "Field validators, factory methods (from_service_response), sum validation"
  gotcha: "Always validate percentages sum to 100% (within 0.01% tolerance)"

- file: src/api/rest/threshold_bars.py
  why: "Flask Blueprint structure, error handling hierarchy"
  pattern: "ValidationError → 400, ValueError → 400, RuntimeError → 500, Exception → 500"
  gotcha: "@login_required removed for testing (can add back later)"

- file: src/app.py
  lines: 2347-2350
  why: "Blueprint registration pattern"
  pattern: "from src.api.rest.{module} import {module}_bp; app.register_blueprint({module}_bp)"
  gotcha: "Register AFTER cache management routes, BEFORE stock groups routes"

# PANDAS CALCULATIONS (EMA/SMA)
- url: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
  why: "EMA calculation method (.ewm)"
  critical: "Use adjust=False for standard EMA (no forward-looking bias)"
  code: "df['ema'] = df.groupby('symbol')['close'].transform(lambda x: x.ewm(span=period, adjust=False, min_periods=period).mean())"

- url: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html
  why: "SMA calculation method (.rolling)"
  critical: "Set min_periods=period to avoid partial averages (NOT true 50-day SMA with 20 data points)"
  code: "df['sma'] = df.groupby('symbol')['close'].transform(lambda x: x.rolling(window=period, min_periods=period).mean())"

- url: https://pandas.pydata.org/docs/user_guide/user_defined_functions.html
  why: "Performance optimization (vectorized operations)"
  critical: "groupby().transform() is 1,300x faster than apply() with UDF"

# RELATIONSHIP CACHE
- file: src/core/services/relationship_cache.py
  lines: 1-150
  why: "Symbol loading pattern for universes/ETFs"
  pattern: "get_universe_symbols(data_source) returns list[str] with <1ms cache hit"
  gotcha: "Supports multi-universe joins: 'sp500:nasdaq100' → distinct union"

# FRONTEND PATTERNS
- file: web/static/js/components/threshold-bar-renderer.js
  lines: 1-150
  why: "JavaScript API fetch pattern, DOM rendering, error handling"
  pattern: "ThresholdBarRenderer class with fetchThresholdData(), render(), _renderSegments()"
  gotcha: "Use URLSearchParams for query string building"

- file: web/static/css/components/threshold-bars.css
  lines: 1-100
  why: "CSS flexbox horizontal bar layout"
  pattern: "Diverging bar with percentage widths, baseline center line"
  gotcha: "Use var(--text-primary) for theme-aware colors"

# TEST PATTERNS
- file: tests/core/services/test_threshold_bar_service.py
  why: "Unit test structure for service layer"
  pattern: "Dependency injection mocking (relationship_cache, db), pytest fixtures"
  gotcha: "Always test edge cases: empty symbols, missing data, insufficient history"

- file: tests/api/rest/test_threshold_bars_api.py
  why: "API endpoint test structure"
  pattern: "Flask test client, Pydantic validation tests, error response tests"
  gotcha: "Mock service layer to isolate endpoint testing"

- file: tests/integration/test_threshold_bars_e2e.py
  why: "End-to-end test structure"
  pattern: "Real database integration, performance validation, multi-universe joins"
  gotcha: "Use @pytest.mark.performance for timing assertions"

# DATABASE SCHEMA
- file: docs/database/schema.md
  why: "OHLCV table schema and query patterns"
  pattern: "ohlcv_daily uses 'date' column (NOT 'timestamp'), TimescaleDB chunk exclusion"
  gotcha: "Must cast datetime to date for date-based tables"

# USER STORY REFERENCE
- file: docs/planning/sprints/sprint66/userstory.md
  why: "Complete user story with all 12 metrics defined"
  pattern: "Formula specifications, frontend mockup, validation gates"
```

### Current Codebase Tree

```bash
# Run: tree -L 3 -I '__pycache__|*.pyc|node_modules'
# (Output truncated for brevity - key directories shown)

TickStockAppV2/
├── src/
│   ├── api/
│   │   └── rest/
│   │       ├── threshold_bars.py          # Sprint 64 reference
│   │       ├── admin_cache.py            # Cache management (register before breadth)
│   │       └── stock_groups.py           # Stock groups (register after breadth)
│   ├── core/
│   │   ├── models/
│   │   │   └── threshold_bar_models.py   # Pydantic patterns reference
│   │   └── services/
│   │       ├── threshold_bar_service.py  # Primary architecture reference
│   │       └── relationship_cache.py     # Symbol loading pattern
│   └── infrastructure/
│       └── database/
│           └── tickstock_db.py           # Database connection pattern
├── web/
│   ├── static/
│   │   ├── css/
│   │   │   └── components/
│   │   │       └── threshold-bars.css    # CSS flexbox reference
│   │   └── js/
│   │       └── components/
│   │           └── threshold-bar-renderer.js  # Frontend reference
│   └── templates/
│       └── dashboard/
│           ├── index.html                # Dashboard integration
│           └── market_overview.html      # Sprint 64 dashboard section
└── tests/
    ├── core/
    │   └── services/
    │       └── test_threshold_bar_service.py  # Unit test reference
    ├── api/
    │   └── rest/
    │       └── test_threshold_bars_api.py     # API test reference
    └── integration/
        └── test_threshold_bars_e2e.py         # E2E test reference
```

### Desired Codebase Tree with Files to be Added

```bash
TickStockAppV2/
├── src/
│   ├── api/
│   │   └── rest/
│   │       └── breadth_metrics.py                    # NEW: Flask Blueprint for /api/breadth-metrics
│   ├── core/
│   │   ├── models/
│   │   │   └── breadth_metrics_models.py             # NEW: Pydantic request/response models
│   │   └── services/
│   │       └── breadth_metrics_service.py            # NEW: Core calculation service (12 methods)
├── web/
│   ├── static/
│   │   ├── css/
│   │   │   └── components/
│   │   │       └── breadth-metrics.css               # NEW: Horizontal bar chart CSS
│   │   └── js/
│   │       └── components/
│   │           └── breadth-metrics-renderer.js       # NEW: JavaScript renderer
│   └── templates/
│       └── dashboard/
│           └── market_breadth.html                    # NEW: Dashboard section template
└── tests/
    ├── core/
    │   └── services/
    │       └── test_breadth_metrics_service.py       # NEW: 30+ unit tests
    ├── api/
    │   └── rest/
    │       └── test_breadth_metrics_api.py           # NEW: 10+ API tests
    └── integration/
        └── test_breadth_metrics_e2e.py               # NEW: 5+ e2e tests

# MODIFIED FILES:
├── src/app.py                                        # MODIFY: Register breadth_metrics_bp blueprint
├── web/static/js/components/sidebar-navigation-controller.js  # MODIFY: Add navigation item
├── web/templates/dashboard/index.html               # MODIFY: Include market_breadth.html
└── CLAUDE.md                                        # MODIFY: Add Sprint 66 completion entry
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Sprint 64 Patterns - Time Column Naming Variance
# Different OHLCV tables use different column names for time dimension
# Solution: Map timeframes to correct columns BEFORE query
time_column_map = {
    "1min": "timestamp",      # ohlcv_1min
    "hourly": "timestamp",    # ohlcv_hourly
    "daily": "date",          # ohlcv_daily (NOT timestamp!)
    "weekly": "week_start",   # ohlcv_weekly
    "monthly": "month_start", # ohlcv_monthly
}
# LOCATION: src/core/services/threshold_bar_service.py lines 246-254

# CRITICAL: Type Casting for Time Filters
# Comparing datetime to date column fails in PostgreSQL
# Solution: Cast cutoff to appropriate type based on table
if timeframe in ["daily", "weekly", "monthly"]:
    cutoff_value = cutoff_datetime.date()  # Use DATE type
else:
    cutoff_value = cutoff_datetime  # Use TIMESTAMP type
# LOCATION: src/core/services/threshold_bar_service.py lines 260-263

# CRITICAL: Pandas EMA adjust Parameter
# adjust=True (default): Normalized weights (more complex, forward-looking)
# adjust=False (recommended): Recursive formula (standard EMA, no lookahead)
df['ema_20'] = df.groupby('symbol')['close'].transform(
    lambda x: x.ewm(span=20, adjust=False, min_periods=20).mean()
)
# DOCUMENTATION: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html

# CRITICAL: Pandas SMA min_periods Parameter
# Default behavior: min_periods=window (good - avoids partial averages)
# BAD: min_periods=1 creates partial SMAs (NOT true 50-day SMA with 20 data points)
df['sma_50'] = df.groupby('symbol')['close'].transform(
    lambda x: x.rolling(window=50, min_periods=50).mean()
)
# GOTCHA: Always set min_periods=window for true moving averages
# DOCUMENTATION: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html

# CRITICAL: NaN Handling in Percentage Changes
# Single NaN in window creates NaN result
# Symbols with only 1 data point produce NaN pct_change
# Solution: Drop NaN values before binning
latest_changes = latest_changes.dropna(subset=["pct_change"])
# LOCATION: src/core/services/threshold_bar_service.py line 328

# CRITICAL: Data Sorting Before Moving Averages
# Unsorted data produces INCORRECT moving averages
# Solution: ALWAYS sort by [symbol, timestamp] before MA calculation
df = df.sort_values(['symbol', 'timestamp'])
# Then calculate MA
df['ema_20'] = df.groupby('symbol')['close'].transform(...)

# CRITICAL: Performance - groupby().transform() vs apply()
# apply() with UDF: 5.64 seconds (SLOW)
# transform() vectorized: 0.0043 seconds (FAST - 1,300x faster)
# Always use: df.groupby('symbol')['close'].transform(lambda x: ...)
# NEVER use: df.groupby('symbol').apply(lambda x: ...)
# DOCUMENTATION: https://pandas.pydata.org/docs/user_guide/user_defined_functions.html

# CRITICAL: SPY Has 504 Stocks, Not 500
# Common misconception: "S&P 500" name implies 500 stocks
# Reality: SPY ETF actually holds 504 stocks (confirmed via database query)
# ALWAYS use RelationshipCache to get accurate symbol count
symbols = cache.get_universe_symbols('SPY')  # Returns 504 symbols
# CALCULATION: When universe='SPY', metrics calculate based on 504 stocks
# Example: If 345 stocks are up, the response shows {"up": 345, "down": 159, "pct_up": 68.5}
# LOCATION: Database query: SELECT COUNT(*) FROM group_memberships WHERE group_id = (SELECT id FROM definition_groups WHERE name = 'SPY')
# RESULT: 504 rows (not 500)

# CRITICAL: RelationshipCache Multi-Universe Joins
# Supports colon-separated universe keys for distinct unions
# Example: 'sp500:nasdaq100' → ~518 distinct symbols
cache.get_universe_symbols('sp500:nasdaq100')
# LOCATION: src/core/services/relationship_cache.py
# SPRINT: Sprint 61 feature

# CRITICAL: Floating Point Percentage Rounding
# Summing percentages may equal 99.98% or 100.02% due to rounding
# Solution: Use floating point tolerance (np.isclose with atol=0.01)
if not np.isclose(total_pct, 100.0, atol=0.01):
    logger.warning(f"Segment percentages sum to {total_pct:.2f}%")
# LOCATION: src/core/services/threshold_bar_service.py line 423

# CRITICAL: TickStockAppV2 is CONSUMER ONLY
# - Read from OHLCV tables (READ-ONLY)
# - No OHLCV aggregation (belongs in TickStockPL)
# - No pattern detection logic (belongs in TickStockPL)
# - No database writes for market data

# CRITICAL: Flask Blueprint Registration Order
# Register breadth_metrics_bp AFTER admin_cache_bp, BEFORE stock_groups_bp
# LOCATION: src/app.py lines 2347-2356
from src.api.rest.breadth_metrics import breadth_metrics_bp
app.register_blueprint(breadth_metrics_bp)

# CRITICAL: Pydantic v2 Validation
# Use field_validator (NOT validator from Pydantic v1)
from pydantic import BaseModel, Field, field_validator

@field_validator('universe')
@classmethod
def validate_universe(cls, v):
    if not v or not isinstance(v, str):
        raise ValueError("universe must be non-empty string")
    return v.upper()
```

## Implementation Blueprint

### Data Models and Structure

Create Pydantic v2 models for type-safe request/response validation.

```python
# FILE: src/core/models/breadth_metrics_models.py
# PATTERN: Follow threshold_bar_models.py structure exactly
# LINES: ~150-200 lines

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator

# Type aliases
UniverseKey = str  # 'SPY', 'QQQ', 'dow30', 'sp500', etc.

class BreadthMetricsRequest(BaseModel):
    """Request model for breadth metrics calculation.

    Validates query parameters from Flask request.args.
    """
    universe: UniverseKey = Field(
        default='SPY',
        description="Universe key (e.g., 'SPY', 'QQQ', 'dow30')",
        min_length=1,
        max_length=50,
    )

    @field_validator('universe')
    @classmethod
    def validate_universe(cls, v: str) -> str:
        """Validate universe is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("universe cannot be empty or whitespace")
        return v.strip().upper()


class MetricData(BaseModel):
    """Single breadth metric data (up/down counts + percentage).

    Example: Day Change metric shows 345 up, 159 down, 68.5% up.
    """
    up: int = Field(ge=0, description="Count of stocks up/above")
    down: int = Field(ge=0, description="Count of stocks down/below")
    unchanged: int = Field(ge=0, description="Count of stocks unchanged")
    pct_up: float = Field(ge=0.0, le=100.0, description="Percentage up/above")

    @field_validator('pct_up')
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        """Ensure percentage is within valid range."""
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"pct_up must be 0-100, got {v}")
        return round(v, 2)


class BreadthMetricsMetadata(BaseModel):
    """Metadata for breadth metrics response.

    Enables client validation, debugging, and display formatting.
    """
    universe: UniverseKey
    symbol_count: int = Field(ge=0, description="Number of symbols analyzed")
    calculation_time_ms: float = Field(ge=0.0, description="Calculation duration in milliseconds")
    calculated_at: str = Field(description="ISO 8601 timestamp")

    @field_validator('calculated_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e


class BreadthMetricsResponse(BaseModel):
    """Complete breadth metrics API response.

    Structure:
    {
        "metrics": {
            "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
            "week": {"up": 390, "down": 114, "unchanged": 0, "pct_up": 77.4},
            ...
        },
        "metadata": {
            "universe": "SPY",
            "symbol_count": 504,
            "calculation_time_ms": 42.3,
            "calculated_at": "2026-02-07T14:45:00.123456"
        }
    }
    """
    metrics: Dict[str, MetricData]
    metadata: BreadthMetricsMetadata

    @field_validator('metrics')
    @classmethod
    def validate_metrics_keys(cls, v: Dict[str, MetricData]) -> Dict[str, MetricData]:
        """Validate all expected metrics present."""
        expected_keys = {
            'day_change', 'open_change', 'week', 'month', 'quarter',
            'half_year', 'year', 'price_to_ema10', 'price_to_ema20',
            'price_to_sma50', 'price_to_sma200'
        }
        missing_keys = expected_keys - set(v.keys())
        if missing_keys:
            raise ValueError(f"Missing metrics: {missing_keys}")
        return v

    @classmethod
    def from_service_response(cls, service_data: Dict[str, Any]) -> "BreadthMetricsResponse":
        """Factory method to create response from service layer dict.

        Args:
            service_data: Dictionary from BreadthMetricsService.calculate_breadth_metrics()

        Returns:
            Validated BreadthMetricsResponse instance
        """
        return cls(
            metrics=service_data["metrics"],
            metadata=BreadthMetricsMetadata(**service_data["metadata"]),
        )


class BreadthMetricsErrorResponse(BaseModel):
    """Standardized error response model.

    Used for 400 (validation errors) and 500 (server errors).
    """
    error: str = Field(description="Error type (ValidationError, ValueError, RuntimeError, ServerError)")
    message: str = Field(description="Human-readable error message")
    details: Dict[str, Any] | None = Field(default=None, description="Additional error context")

    @classmethod
    def create(cls, error: str, message: str, details: Dict[str, Any] | None = None) -> "BreadthMetricsErrorResponse":
        """Factory method for creating error responses."""
        return cls(error=error, message=message, details=details or {})
```

### Implementation Tasks (Ordered by Dependencies)

```yaml
# PHASE 1: Backend Service Layer (Foundation)

Task 1: CREATE src/core/models/breadth_metrics_models.py
  - IMPLEMENT: Pydantic v2 models for request/response validation
  - FOLLOW pattern: src/core/models/threshold_bar_models.py
  - NAMING: BreadthMetricsRequest, MetricData, BreadthMetricsResponse, BreadthMetricsErrorResponse
  - VALIDATION: field_validator for universe, pct_up, calculated_at, metrics_keys
  - PLACEMENT: src/core/models/ directory
  - DEPENDENCIES: None (foundation file)
  - GOTCHA: Use @classmethod for field_validator (Pydantic v2 syntax)
  - LINES: ~200 lines with docstrings

Task 2: CREATE src/core/services/breadth_metrics_service.py
  - IMPLEMENT: BreadthMetricsService class with 12 calculation methods
  - FOLLOW pattern: src/core/services/threshold_bar_service.py (exact architecture)
  - NAMING: BreadthMetricsService class
  - METHODS:
    - __init__(relationship_cache=None, db=None, config=None)  # Dependency injection
    - calculate_breadth_metrics(universe='SPY') -> dict  # Main orchestration
    - _calculate_day_change(df: pd.DataFrame) -> dict  # Today vs yesterday
    - _calculate_open_change(df: pd.DataFrame) -> dict  # Today close vs today open
    - _calculate_period_change(df: pd.DataFrame, days: int) -> dict  # Generic period
    - _calculate_ema_comparison(df: pd.DataFrame, period: int) -> dict  # Price vs EMA
    - _calculate_sma_comparison(df: pd.DataFrame, period: int) -> dict  # Price vs SMA
    - _query_ohlcv_data(symbols, timeframe='daily', period_days=252) -> pd.DataFrame  # Database query
  - DATABASE: Use TickStockDatabase with context manager (read-only)
  - RELATIONSHIPCACHE: Use get_universe_symbols(universe) for symbol loading
  - PERFORMANCE: Target <50ms for all 12 metrics combined
  - PLACEMENT: src/core/services/ directory
  - DEPENDENCIES: Task 1 (Pydantic models)
  - GOTCHA: Sort DataFrame by [symbol, timestamp] BEFORE calculating moving averages
  - GOTCHA: Use adjust=False for EMA, min_periods=period for SMA
  - GOTCHA: Handle time column name variance (timestamp vs date)
  - LINES: ~400-500 lines with docstrings

Task 3: CREATE tests/core/services/test_breadth_metrics_service.py
  - IMPLEMENT: 30+ unit tests for BreadthMetricsService
  - FOLLOW pattern: tests/core/services/test_threshold_bar_service.py
  - TEST COVERAGE:
    - test_initialization_with_dependency_injection()
    - test_calculate_breadth_metrics_returns_all_12_metrics()
    - test_day_change_calculation()
    - test_open_change_calculation()
    - test_period_change_calculation_week()
    - test_period_change_calculation_month()
    - test_period_change_calculation_quarter()
    - test_period_change_calculation_half_year()
    - test_period_change_calculation_year()
    - test_ema10_comparison()
    - test_ema20_comparison()
    - test_sma50_comparison()
    - test_sma200_comparison()
    - test_empty_symbols_list()
    - test_insufficient_data_for_moving_averages()
    - test_nan_handling_in_percentage_changes()
    - test_database_query_error_handling()
    - test_performance_under_50ms()
  - MOCKING: Mock RelationshipCache and TickStockDatabase
  - ASSERTIONS: Validate up/down/unchanged counts, percentages sum to 100%
  - PLACEMENT: tests/core/services/ directory
  - DEPENDENCIES: Task 2 (service implementation)
  - GOTCHA: Use pytest fixtures for mock data, @pytest.mark.performance for timing tests
  - LINES: ~400-500 lines with test data setup

# PHASE 2: API Layer

Task 4: CREATE src/api/rest/breadth_metrics.py
  - IMPLEMENT: Flask Blueprint for /api/breadth-metrics endpoint
  - FOLLOW pattern: src/api/rest/threshold_bars.py (exact structure)
  - NAMING: breadth_metrics_bp Blueprint
  - ROUTE: GET /api/breadth-metrics?universe=SPY
  - REQUEST VALIDATION: Use BreadthMetricsRequest Pydantic model
  - RESPONSE: JSON with BreadthMetricsResponse structure
  - ERROR HANDLING:
    - ValidationError → 400 (invalid universe parameter)
    - ValueError → 400 (invalid data from service)
    - RuntimeError → 500 (database failure, no data)
    - Exception → 500 (unexpected server error)
  - PLACEMENT: src/api/rest/ directory
  - DEPENDENCIES: Task 1 (models), Task 2 (service)
  - GOTCHA: Do NOT add @login_required yet (causes test failures without Flask-Login setup)
  - LINES: ~120-150 lines with error handling

Task 5: MODIFY src/app.py
  - INTEGRATE: Register breadth_metrics_bp Blueprint
  - FIND pattern: Lines 2347-2350 (threshold_bars_bp registration)
  - ADD AFTER: admin_cache_bp registration (line 2344)
  - ADD BEFORE: stock_groups_bp registration (line 2354)
  - CODE:
    ```python
    logger.info("STARTUP: Registering breadth metrics API...")
    from src.api.rest.breadth_metrics import breadth_metrics_bp
    app.register_blueprint(breadth_metrics_bp)
    logger.info("STARTUP: Breadth metrics API registered successfully")
    ```
  - PLACEMENT: src/app.py main() function
  - DEPENDENCIES: Task 4 (API endpoint)
  - GOTCHA: Must import and register in one block (existing pattern)
  - LINES: +4 lines

Task 6: CREATE tests/api/rest/test_breadth_metrics_api.py
  - IMPLEMENT: 10+ API endpoint tests
  - FOLLOW pattern: tests/api/rest/test_threshold_bars_api.py
  - TEST COVERAGE:
    - test_get_breadth_metrics_success()
    - test_get_breadth_metrics_default_universe()
    - test_get_breadth_metrics_invalid_universe()
    - test_get_breadth_metrics_empty_universe()
    - test_get_breadth_metrics_service_error()
    - test_get_breadth_metrics_validation_error()
    - test_get_breadth_metrics_response_structure()
    - test_get_breadth_metrics_error_response_format()
    - test_get_breadth_metrics_concurrent_requests()
  - MOCKING: Mock BreadthMetricsService to isolate endpoint testing
  - ASSERTIONS: Status codes (200, 400, 500), JSON structure, error messages
  - PLACEMENT: tests/api/rest/ directory
  - DEPENDENCIES: Task 4 (API endpoint)
  - GOTCHA: Use Flask test_client fixture from conftest.py
  - LINES: ~250-300 lines

# PHASE 3: Frontend Display Control

Task 7: CREATE web/static/css/components/breadth-metrics.css
  - IMPLEMENT: CSS flexbox horizontal bar chart layout
  - FOLLOW pattern: web/static/css/components/threshold-bars.css
  - SELECTORS:
    - .breadth-metrics-container  # Outer wrapper
    - .breadth-metrics-section    # Card section with header/controls
    - .metric-row                 # Single metric row (12 total)
    - .metric-label               # Left label (120px width)
    - .metric-bar-container       # Center bar container (flex: 1)
    - .metric-bar-up              # Green bar segment
    - .metric-bar-down            # Red bar segment
    - .metric-counts              # Right counts (120px width)
    - .count-up, .count-down      # Color-coded count text
  - COLORS:
    - Green (up): #28a745 (linear-gradient to #34d058)
    - Red (down): #dc3545 (linear-gradient to #f85149)
    - Background: var(--card-background)
    - Text: var(--text-primary)
  - LAYOUT: Flexbox horizontal bars with percentage widths
  - PLACEMENT: web/static/css/components/ directory
  - DEPENDENCIES: None (independent styling)
  - GOTCHA: Use CSS variables (var(--*)) for theme support
  - LINES: ~200-250 lines

Task 8: CREATE web/static/js/components/breadth-metrics-renderer.js
  - IMPLEMENT: BreadthMetricsRenderer JavaScript class
  - FOLLOW pattern: web/static/js/components/threshold-bar-renderer.js
  - CLASS STRUCTURE:
    - constructor(options = {})  # Initialize with API endpoint
    - async render(containerId, universe = 'SPY')  # Main render method
    - async fetchData(universe)  # API fetch with error handling
    - createMetricsHTML(data)  # Generate 12 metric row HTML
    - createHorizontalBar(metric)  # Create single bar with percentages
    - setupAutoRefresh(containerId, universe)  # 60s interval for intraday
    - _getCSRFToken()  # Extract CSRF token from DOM
  - API ENDPOINT: /api/breadth-metrics?universe={universe}
  - FETCH: Use URLSearchParams for query string, credentials: 'same-origin'
  - ERROR HANDLING: Try-catch with error message display
  - LOADING STATE: Show spinner during fetch
  - PLACEMENT: web/static/js/components/ directory
  - DEPENDENCIES: Task 4 (API endpoint), Task 7 (CSS)
  - GOTCHA: Use await for async fetch, handle JSON parsing errors
  - LINES: ~300-350 lines

Task 9: CREATE web/templates/dashboard/market_breadth.html
  - IMPLEMENT: Reusable dashboard template with configurable parameters
  - FOLLOW pattern: web/templates/dashboard/market_overview.html (Sprint 64)
  - PARAMETERS (Jinja2):
    - instance_id: Unique identifier for this instance (e.g., 'spy', 'qqq', 'dow')
    - universe: Universe key (e.g., 'SPY', 'QQQ', 'dow30')
    - title: Display title (e.g., 'S&P 500 Breadth', 'NASDAQ 100 Breadth')
    - show_controls: Boolean to show/hide universe selector and refresh button
  - STRUCTURE:
    - <div class="breadth-metrics-section" data-breadth-instance="{{ instance_id }}">
      - <div class="section-header">
        - <h2>{{ title | default('Market Breadth') }}</h2>
        - {% if show_controls %}<select class="breadth-universe-select">{% endif %}
        - {% if show_controls %}<button class="breadth-refresh-btn">{% endif %}
      - <div id="breadth-metrics-container-{{ instance_id }}">  # Rendered by JS
      - <div class="section-footer">  # Legend and last update time
  - SCRIPT:
    - window['initializeBreadthMetrics_' + instanceId] = function() { ... }
    - Instantiate BreadthMetricsRenderer with config
    - Setup event handlers (refresh button, universe selector) if show_controls
  - USAGE EXAMPLES:
    - {% include 'dashboard/market_breadth.html' with instance_id='spy', universe='SPY', title='S&P 500 Breadth' %}
    - {% include 'dashboard/market_breadth.html' with instance_id='qqq', universe='QQQ', title='NASDAQ 100 Breadth' %}
  - PLACEMENT: web/templates/dashboard/ directory
  - DEPENDENCIES: Task 7 (CSS), Task 8 (JavaScript)
  - GOTCHA: Each instance needs unique instance_id to avoid DOM conflicts
  - LINES: ~200-250 lines

Task 10: MODIFY web/static/js/components/sidebar-navigation-controller.js
  - INTEGRATE: Add "Market Breadth" navigation item
  - FIND pattern: Existing navigation sections array
  - ADD:
    ```javascript
    {
        id: 'market-breadth',
        label: 'Market Breadth',
        icon: 'fas fa-chart-bar',
        initFunction: 'initializeBreadthMetrics_default'
    }
    ```
  - PLACEMENT: Add after 'market-overview' section, before future sections
  - DEPENDENCIES: Task 9 (HTML template)
  - GOTCHA: Ensure initFunction matches window function name in template
  - LINES: +5 lines

Task 11: MODIFY web/templates/dashboard/index.html
  - INTEGRATE: Include market_breadth.html content
  - FIND pattern: Existing template includes (search for {% include %})
  - ADD AFTER: market_overview.html include
  - CODE:
    ```html
    <!-- Sprint 66: Market Breadth Metrics -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components/breadth-metrics.css') }}">
    <script src="{{ url_for('static', filename='js/components/breadth-metrics-renderer.js') }}"></script>
    {% include 'dashboard/market_breadth.html' with instance_id='default', universe='SPY', title='Market Breadth' %}
    ```
  - PLACEMENT: web/templates/dashboard/index.html <head> and hidden content sections
  - DEPENDENCIES: Task 9 (HTML template), Task 7 (CSS), Task 8 (JavaScript)
  - GOTCHA: Keep content hidden (display: none) until navigation activates
  - NOTE: Default instance uses SPY (504 stocks), but title is generic "Market Breadth"
  - LINES: +4 lines

# PHASE 4: Integration Testing (MANDATORY)

Task 12: CREATE tests/integration/test_breadth_metrics_e2e.py
  - IMPLEMENT: 5+ end-to-end integration tests
  - FOLLOW pattern: tests/integration/test_threshold_bars_e2e.py
  - TEST COVERAGE:
    - test_e2e_full_breadth_calculation()  # Full flow: Cache → DB → Service → API
    - test_e2e_performance_validation()  # Validate <50ms calculation time
    - test_e2e_all_12_metrics_present()  # Verify all metrics in response
    - test_e2e_moving_averages_accuracy()  # Validate EMA/SMA calculations
    - test_e2e_multiple_universes()  # Test SPY, QQQ, dow30 switching
  - DATABASE: Use real TickStockDatabase (not mocked)
  - CACHE: Use real RelationshipCache (not mocked)
  - PERFORMANCE: Use @pytest.mark.performance for timing assertions
  - PLACEMENT: tests/integration/ directory
  - DEPENDENCIES: All previous tasks (full stack integration)
  - GOTCHA: Tests require database with OHLCV data populated
  - LINES: ~250-300 lines

# PHASE 5: Documentation & Validation (Sprint Completion)

Task 13: UPDATE CLAUDE.md
  - MODIFY: Add Sprint 66 completion entry
  - FIND: Current Implementation Status section
  - ADD AFTER: Sprint 64 entry
  - CONTENT:
    ```markdown
    ### Sprint 66 - COMPLETE ✅ (February 2026)
    **Market Breadth Metrics: Reusable Multi-Universe Display Control**
    - ✅ BreadthMetricsService with 12 calculation methods (universe-agnostic)
    - ✅ REST API endpoint /api/breadth-metrics (supports any universe: SPY, QQQ, dow30, etc.)
    - ✅ Reusable frontend component with configurable title, universe, and controls
    - ✅ Multi-instance support: Same page can show multiple universes simultaneously
    - ✅ Moving averages: EMA10, EMA20, SMA50, SMA200 (vectorized pandas)
    - ✅ Performance: <50ms calculation for 500+ symbols, <100ms API response
    - ✅ Tests: 45+ passing (unit + API + e2e)
    - ✅ SPY universe: 504 stocks (not 500)
    - See: `docs/planning/sprints/sprint66/SPRINT66_COMPLETE.md`
    ```
  - PLACEMENT: CLAUDE.md System Integration Points section
  - DEPENDENCIES: All tasks complete
  - LINES: +8 lines

Task 14: CREATE docs/planning/sprints/sprint66/SPRINT66_COMPLETE.md
  - IMPLEMENT: Sprint completion summary document
  - FOLLOW pattern: docs/planning/sprints/sprint64/SPRINT64_COMPLETE.md
  - SECTIONS:
    - Sprint Goal
    - Deliverables (all 5 phases)
    - Performance Metrics (table with actual vs target)
    - Success Criteria (checklist - all checked)
    - Files Modified/Created (list with line counts)
    - Technical Decisions (rationale for key choices)
    - Known Limitations (if any)
    - Next Steps (future enhancements)
    - References (links to PRP, agent outputs, documentation)
  - PLACEMENT: docs/planning/sprints/sprint66/ directory
  - DEPENDENCIES: All tasks complete
  - LINES: ~400-500 lines (comprehensive documentation)
```

### Implementation Patterns & Key Details

```python
# PATTERN 1: BreadthMetricsService Core Calculation
# Location: src/core/services/breadth_metrics_service.py

from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np

from src.core.services.relationship_cache import get_relationship_cache
from src.infrastructure.database.tickstock_db import TickStockDatabase

logger = logging.getLogger(__name__)

class BreadthMetricsService:
    """Service for calculating S&P 500 breadth metrics.

    Calculates 12 metrics showing up/down counts across time periods
    and moving average relationships for market breadth analysis.

    Performance targets:
    - Full 12-metric calculation: <50ms
    - Database query: <30ms
    - Pandas calculation: <20ms
    """

    def __init__(self, relationship_cache=None, db=None, config=None):
        """Dependency injection pattern for testability."""
        self.relationship_cache = relationship_cache or get_relationship_cache()

        if db is not None:
            self.db = db
        elif config is not None:
            self.db = TickStockDatabase(config)
        else:
            try:
                from config.app_config import load_config
                app_config = load_config()
                self.db = TickStockDatabase(app_config)
            except Exception:
                self.db = TickStockDatabase({})

        logger.info("BreadthMetricsService initialized")

    def calculate_breadth_metrics(self, universe: str = 'SPY') -> dict:
        """Calculate all 12 breadth metrics in one pass.

        Args:
            universe: Universe key (default: 'SPY' for S&P 500)

        Returns:
            Dictionary with structure:
            {
                "metrics": {
                    "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
                    ...
                },
                "metadata": {
                    "universe": "SPY",
                    "symbol_count": 504,
                    "calculation_time_ms": 42.3,
                    "calculated_at": "2026-02-07T14:45:00Z"
                }
            }

        Raises:
            ValueError: If universe empty or invalid
            RuntimeError: If no symbols found or database failure
        """
        start_time = datetime.now()

        # Validation
        if not universe or not isinstance(universe, str):
            raise ValueError(f"universe must be non-empty string, got: {universe}")

        logger.info(f"Calculating breadth metrics for {universe}")

        # Step 1: Load symbols via RelationshipCache
        symbols = self.relationship_cache.get_universe_symbols(universe)

        if not symbols:
            raise RuntimeError(f"No symbols found for universe: {universe}")

        logger.debug(f"Loaded {len(symbols)} symbols for {universe}")

        # Step 2: Fetch 252 days of OHLCV data (covers all periods up to 1 year)
        df = self._query_ohlcv_data(symbols, timeframe='daily', period_days=252)

        if df.empty:
            raise RuntimeError(
                f"No OHLCV data available for {universe} "
                f"(symbols={len(symbols)}, period_days=252). "
                f"Check if daily OHLCV data exists for these symbols."
            )

        logger.debug(f"Queried {len(df)} OHLCV rows")

        # Step 3: Calculate all 12 metrics from same DataFrame
        metrics = {
            'day_change': self._calculate_day_change(df),
            'open_change': self._calculate_open_change(df),
            'week': self._calculate_period_change(df, 5),
            'month': self._calculate_period_change(df, 21),
            'quarter': self._calculate_period_change(df, 63),
            'half_year': self._calculate_period_change(df, 126),
            'year': self._calculate_period_change(df, 252),
            'price_to_ema10': self._calculate_ema_comparison(df, 10),
            'price_to_ema20': self._calculate_ema_comparison(df, 20),
            'price_to_sma50': self._calculate_sma_comparison(df, 50),
            'price_to_sma200': self._calculate_sma_comparison(df, 200),
        }

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Calculated breadth metrics for {universe} in {elapsed_ms:.1f}ms "
            f"({len(symbols)} symbols)"
        )

        return {
            "metrics": metrics,
            "metadata": {
                "universe": universe,
                "symbol_count": len(symbols),
                "calculation_time_ms": round(elapsed_ms, 2),
                "calculated_at": datetime.now().isoformat(),
            }
        }

    def _calculate_day_change(self, df: pd.DataFrame) -> dict:
        """Calculate day change: Today close vs yesterday close.

        Formula: (close_today - close_yesterday) / close_yesterday
        """
        df_sorted = df.sort_values(['symbol', 'date'])

        # Calculate percentage change per symbol
        df_sorted['pct_change'] = df_sorted.groupby('symbol')['close'].transform(
            lambda x: x.pct_change() * 100
        )

        # Get latest change per symbol
        latest = df_sorted.groupby('symbol').last().reset_index()
        latest = latest.dropna(subset=['pct_change'])

        # Count up/down/unchanged
        up_count = (latest['pct_change'] > 0).sum()
        down_count = (latest['pct_change'] < 0).sum()
        unchanged_count = (latest['pct_change'] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            'up': int(up_count),
            'down': int(down_count),
            'unchanged': int(unchanged_count),
            'pct_up': round(pct_up, 2)
        }

    def _calculate_open_change(self, df: pd.DataFrame) -> dict:
        """Calculate open change: Today close vs today open.

        Formula: (close_today - open_today) / open_today
        """
        latest = df.groupby('symbol').last().reset_index()

        # Calculate intraday change
        latest['pct_change'] = (
            (latest['close'] - latest['open']) / latest['open'] * 100
        )
        latest = latest.dropna(subset=['pct_change'])

        # Count up/down/unchanged
        up_count = (latest['pct_change'] > 0).sum()
        down_count = (latest['pct_change'] < 0).sum()
        unchanged_count = (latest['pct_change'] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            'up': int(up_count),
            'down': int(down_count),
            'unchanged': int(unchanged_count),
            'pct_up': round(pct_up, 2)
        }

    def _calculate_period_change(self, df: pd.DataFrame, days: int) -> dict:
        """Generic period change calculation.

        Args:
            df: OHLCV DataFrame
            days: Lookback period (5=week, 21=month, 63=quarter, 126=half_year, 252=year)

        Formula: (close_latest - close_N_days_ago) / close_N_days_ago
        """
        df_sorted = df.sort_values(['symbol', 'date'])

        # Calculate change from N days ago
        df_sorted['pct_change'] = df_sorted.groupby('symbol')['close'].transform(
            lambda x: ((x.iloc[-1] - x.iloc[-days]) / x.iloc[-days] * 100)
            if len(x) >= days else np.nan
        )

        # Get latest value per symbol
        latest = df_sorted.groupby('symbol').last().reset_index()
        latest = latest.dropna(subset=['pct_change'])

        # Count up/down/unchanged
        up_count = (latest['pct_change'] > 0).sum()
        down_count = (latest['pct_change'] < 0).sum()
        unchanged_count = (latest['pct_change'] == 0).sum()

        total = len(latest)
        pct_up = (up_count / total * 100) if total > 0 else 0.0

        return {
            'up': int(up_count),
            'down': int(down_count),
            'unchanged': int(unchanged_count),
            'pct_up': round(pct_up, 2)
        }

    def _calculate_ema_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Calculate price vs EMA comparison.

        Args:
            df: OHLCV DataFrame
            period: EMA period (10 or 20)

        Formula: close > EMA(period) → above, close < EMA(period) → below
        """
        df_sorted = df.sort_values(['symbol', 'date'])

        # Calculate EMA per symbol (adjust=False for standard EMA)
        df_sorted['ema'] = df_sorted.groupby('symbol')['close'].transform(
            lambda x: x.ewm(span=period, adjust=False, min_periods=period).mean()
        )

        # Get latest values
        latest = df_sorted.groupby('symbol').last().reset_index()
        latest = latest.dropna(subset=['ema'])

        # Count above/below EMA
        above_count = (latest['close'] > latest['ema']).sum()
        below_count = (latest['close'] < latest['ema']).sum()
        equal_count = (latest['close'] == latest['ema']).sum()

        total = len(latest)
        pct_above = (above_count / total * 100) if total > 0 else 0.0

        return {
            'up': int(above_count),  # 'up' = above EMA
            'down': int(below_count),  # 'down' = below EMA
            'unchanged': int(equal_count),
            'pct_up': round(pct_above, 2)
        }

    def _calculate_sma_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Calculate price vs SMA comparison.

        Args:
            df: OHLCV DataFrame
            period: SMA period (50 or 200)

        Formula: close > SMA(period) → above, close < SMA(period) → below
        """
        df_sorted = df.sort_values(['symbol', 'date'])

        # Calculate SMA per symbol (min_periods=period for true SMA)
        df_sorted['sma'] = df_sorted.groupby('symbol')['close'].transform(
            lambda x: x.rolling(window=period, min_periods=period).mean()
        )

        # Get latest values
        latest = df_sorted.groupby('symbol').last().reset_index()
        latest = latest.dropna(subset=['sma'])

        # Count above/below SMA
        above_count = (latest['close'] > latest['sma']).sum()
        below_count = (latest['close'] < latest['sma']).sum()
        equal_count = (latest['close'] == latest['sma']).sum()

        total = len(latest)
        pct_above = (above_count / total * 100) if total > 0 else 0.0

        return {
            'up': int(above_count),  # 'up' = above SMA
            'down': int(below_count),  # 'down' = below SMA
            'unchanged': int(equal_count),
            'pct_up': round(pct_above, 2)
        }

    def _query_ohlcv_data(
        self, symbols: list[str], timeframe: str = 'daily', period_days: int = 252
    ) -> pd.DataFrame:
        """Query OHLCV data from TimescaleDB.

        CRITICAL: Uses 'date' column for ohlcv_daily (NOT 'timestamp')
        PATTERN: Follow threshold_bar_service.py lines 266-287 exactly
        """
        table_name = 'ohlcv_daily'
        time_column = 'date'  # CRITICAL: ohlcv_daily uses 'date' column

        cutoff_datetime = datetime.now() - timedelta(days=period_days)
        cutoff_value = cutoff_datetime.date()  # Cast to date for date-based table

        query = f"""
            SELECT
                symbol,
                {time_column} as date,
                open,
                high,
                low,
                close,
                volume
            FROM {table_name}
            WHERE symbol = ANY(%s)
              AND {time_column} >= %s
            ORDER BY symbol, {time_column}
        """

        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=(symbols, cutoff_value))

            logger.debug(
                f"Queried {len(df)} rows from {table_name} "
                f"for {len(symbols)} symbols (period_days={period_days})"
            )

            return df

        except Exception as e:
            logger.error(f"Database query failed for {table_name}: {e}")
            raise RuntimeError(f"Failed to query {table_name}") from e


# PATTERN 2: Flask API Endpoint
# Location: src/api/rest/breadth_metrics.py

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
import logging

from src.core.models.breadth_metrics_models import (
    BreadthMetricsErrorResponse,
    BreadthMetricsRequest,
    BreadthMetricsResponse,
)
from src.core.services.breadth_metrics_service import BreadthMetricsService

logger = logging.getLogger(__name__)

breadth_metrics_bp = Blueprint("breadth_metrics", __name__)

@breadth_metrics_bp.route("/api/breadth-metrics", methods=["GET"])
# @login_required  # Can be enabled later (causes test failures without Flask-Login)
def get_breadth_metrics():
    """Calculate S&P 500 breadth metrics.

    Query Parameters:
        universe (str): Universe key (default: 'SPY')

    Returns:
        JSON response with metrics and metadata

    Status Codes:
        200: Success
        400: Validation error (invalid universe)
        500: Server error (database failure, no data)

    Example:
        GET /api/breadth-metrics?universe=SPY

        Response:
        {
            "metrics": {
                "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
                ...
            },
            "metadata": {
                "universe": "SPY",
                "symbol_count": 504,
                "calculation_time_ms": 42.3,
                "calculated_at": "2026-02-07T14:45:00Z"
            }
        }
    """
    try:
        # Extract and validate query parameters
        request_data = BreadthMetricsRequest(
            universe=request.args.get("universe", "SPY")
        )

        logger.info(f"Breadth metrics request: {request_data.universe}")

        # Calculate metrics
        service = BreadthMetricsService()
        result = service.calculate_breadth_metrics(universe=request_data.universe)

        # Validate response
        response = BreadthMetricsResponse.from_service_response(result)

        return jsonify(response.model_dump()), 200

    except ValidationError as e:
        # Pydantic validation errors (invalid parameters)
        logger.warning(f"Breadth metrics validation error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="ValidationError",
            message="Invalid request parameters",
            details={"validation_errors": e.errors()},
        )
        return jsonify(error_response.model_dump()), 400

    except ValueError as e:
        # Service-level validation errors
        logger.warning(f"Breadth metrics value error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="ValueError",
            message=str(e),
        )
        return jsonify(error_response.model_dump()), 400

    except RuntimeError as e:
        # Service-level runtime errors (no data, query failure)
        logger.error(f"Breadth metrics runtime error: {e}")
        error_response = BreadthMetricsErrorResponse.create(
            error="RuntimeError",
            message=str(e),
        )
        return jsonify(error_response.model_dump()), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in breadth metrics endpoint: {e}", exc_info=True)
        error_response = BreadthMetricsErrorResponse.create(
            error="ServerError",
            message="An unexpected error occurred",
        )
        return jsonify(error_response.model_dump()), 500


# PATTERN 3: Frontend JavaScript Renderer
# Location: web/static/js/components/breadth-metrics-renderer.js

class BreadthMetricsRenderer {
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/api/breadth-metrics';
        this.csrfToken = options.csrfToken || this._getCSRFToken();
        this.refreshInterval = 60000; // 60 seconds
        this.refreshTimer = null;
    }

    async render(containerId, universe = 'SPY') {
        const container = document.getElementById(containerId);

        if (!container) {
            console.error(`Container element not found: ${containerId}`);
            return;
        }

        // Clear container
        container.innerHTML = '';
        container.className = 'breadth-metrics-container loading';

        try {
            // Fetch data from API
            const data = await this.fetchData(universe);

            // Remove loading state
            container.classList.remove('loading');

            // Render 12 metric rows
            const html = this.createMetricsHTML(data);
            container.innerHTML = html;

            // Setup auto-refresh (60s for intraday data)
            this.setupAutoRefresh(containerId, universe);

        } catch (error) {
            // Remove loading state
            container.classList.remove('loading');

            // Show error state
            container.classList.add('error');
            container.innerHTML = `
                <div class="breadth-metrics-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Error loading breadth metrics: ${error.message}</p>
                </div>
            `;

            console.error('Breadth metrics rendering error:', error);
        }
    }

    async fetchData(universe) {
        const params = new URLSearchParams({ universe });
        const url = `${this.apiEndpoint}?${params}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
            },
            credentials: 'same-origin',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `API error: ${response.status}`);
        }

        return await response.json();
    }

    createMetricsHTML(data) {
        const metrics = data.metrics;
        const metricLabels = {
            'day_change': 'Day Chg',
            'open_change': 'Open Chg',
            'week': 'Week',
            'month': 'Month',
            'quarter': 'Quarter',
            'half_year': 'Half Year',
            'year': 'Year',
            'price_to_ema10': 'Price/EMA10',
            'price_to_ema20': 'Price/EMA20',
            'price_to_sma50': 'Price/SMA50',
            'price_to_sma200': 'Price/SMA200',
        };

        let html = '';

        for (const [key, label] of Object.entries(metricLabels)) {
            const metric = metrics[key];
            if (!metric) continue;

            const barHTML = this.createHorizontalBar(metric, label);
            html += barHTML;
        }

        return html;
    }

    createHorizontalBar(metric, label) {
        const { up, down, pct_up } = metric;
        const pct_down = 100 - pct_up;

        // Calculate bar widths (percentage-based)
        const upWidth = pct_up;
        const downWidth = pct_down;

        return `
            <div class="metric-row">
                <div class="metric-label">${label}</div>
                <div class="metric-bar-container">
                    <div class="metric-bar-up" style="width: ${upWidth}%"></div>
                    <div class="metric-bar-down" style="width: ${downWidth}%"></div>
                </div>
                <div class="metric-counts">
                    <span class="count-up">${up}</span> /
                    <span class="count-down">${down}</span>
                </div>
            </div>
        `;
    }

    setupAutoRefresh(containerId, universe) {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Setup new timer (60s interval)
        this.refreshTimer = setInterval(() => {
            this.render(containerId, universe);
        }, this.refreshInterval);
    }

    cleanup() {
        // Clear refresh timer on component unmount
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    _getCSRFToken() {
        // Extract CSRF token from meta tag or cookie
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Fallback: cookie-based CSRF token
        const name = 'csrf_token=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookieParts = decodedCookie.split(';');

        for (let part of cookieParts) {
            part = part.trim();
            if (part.indexOf(name) === 0) {
                return part.substring(name.length);
            }
        }

        return '';
    }
}
```

### Integration Points

```yaml
# NO REDIS CHANNELS - Feature does not use Redis pub-sub
REDIS_CHANNELS:
  - subscribe_in: "N/A"
    channel_pattern: "N/A"
    message_format: "N/A"
    reason: "Breadth metrics calculate on-demand from OHLCV database"

# DATABASE QUERIES
DATABASE:
  - query_location: "src/core/services/breadth_metrics_service.py"
  - query_method: "_query_ohlcv_data()"
  - query_pattern: |
      SELECT symbol, date, open, high, low, close, volume
      FROM ohlcv_daily
      WHERE symbol = ANY(%s) AND date >= %s
      ORDER BY symbol, date
  - performance: "<30ms for 252 days × 504 symbols = 127k rows"
  - optimization: "TimescaleDB chunk exclusion via date filter, indexed symbol array lookup"

# NO WEBSOCKET BROADCASTING - REST API only
WEBSOCKET:
  - event_handler: "N/A"
  - event_name: "N/A"
  - broadcast_method: "N/A"
  - reason: "Feature uses REST API polling (60s auto-refresh), no real-time WebSocket events"

# FLASK BLUEPRINT REGISTRATION
FLASK_BLUEPRINTS:
  - blueprint_file: "src/api/rest/breadth_metrics.py"
  - blueprint_name: "breadth_metrics_bp"
  - register_in: "src/app.py"
  - registration_pattern: |
      # Lines 2351-2354 (AFTER admin_cache_bp, BEFORE stock_groups_bp)
      logger.info("STARTUP: Registering breadth metrics API...")
      from src.api.rest.breadth_metrics import breadth_metrics_bp
      app.register_blueprint(breadth_metrics_bp)
      logger.info("STARTUP: Breadth metrics API registered successfully")

# FRONTEND NAVIGATION INTEGRATION
NAVIGATION:
  - navigation_file: "web/static/js/components/sidebar-navigation-controller.js"
  - navigation_item: |
      {
          id: 'market-breadth',
          label: 'Market Breadth',
          icon: 'fas fa-chart-bar',
          initFunction: 'initializeBreadthMetrics_default'
      }
  - placement: "Add after 'market-overview' section"

# DASHBOARD TEMPLATE INTEGRATION
TEMPLATES:
  - template_file: "web/templates/dashboard/market_breadth.html"
  - include_in: "web/templates/dashboard/index.html"
  - include_pattern: |
      <!-- Sprint 66: Market Breadth Metrics -->
      <link rel="stylesheet" href="{{ url_for('static', filename='css/components/breadth-metrics.css') }}">
      <script src="{{ url_for('static', filename='js/components/breadth-metrics-renderer.js') }}"></script>
      {% include 'dashboard/market_breadth.html' %}

# NO TICKSTOCKPL API INTEGRATION
TICKSTOCKPL_API:
  - api_client: "N/A"
  - endpoint: "N/A"
  - reason: "Feature calculates directly from OHLCV database, no TickStockPL jobs triggered"

# NO STARTUP SERVICE INITIALIZATION
STARTUP:
  - startup_file: "N/A"
  - initialization: "N/A"
  - reason: "Service instantiated on-demand per API request (stateless)"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# Run after each file creation - fix before proceeding

# File-specific validation
ruff check src/core/services/breadth_metrics_service.py --fix
ruff check src/core/models/breadth_metrics_models.py --fix
ruff check src/api/rest/breadth_metrics.py --fix
ruff format src/

# Project-wide validation (final check)
ruff check src/ --fix
ruff format src/

# Expected: Zero errors
# If errors exist, READ output and fix before proceeding
```

### Level 2: Unit Tests (Component Validation)

```bash
# Test each component as it's created

# Service tests (30+ tests)
pytest tests/core/services/test_breadth_metrics_service.py -v

# API tests (10+ tests)
pytest tests/api/rest/test_breadth_metrics_api.py -v

# Full unit test suite
pytest tests/unit/ -v

# Coverage validation (optional)
pytest tests/core/services/test_breadth_metrics_service.py --cov=src.core.services.breadth_metrics_service --cov-report=term-missing

# Expected: All tests pass
# TickStock Standard: Aim for >80% coverage on business logic
# If failing, debug root cause and fix implementation
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
# CRITICAL: Must run before ANY commit

# Primary integration test runner
python run_tests.py

# Alternative detailed runner
python tests/integration/run_integration_tests.py

# Expected Output:
# - 2+ tests passing (pattern flow tests + breadth metrics e2e)
# - ~30-40 second runtime
# - Pattern flow tests still passing (zero regression)
# - Breadth metrics e2e tests passing

# NOTE: RLock warning can be ignored (known asyncio quirk)

# Breadth metrics specific integration tests
pytest tests/integration/test_breadth_metrics_e2e.py -v

# Expected: 5+ e2e tests passing
# - test_e2e_full_breadth_calculation
# - test_e2e_performance_validation
# - test_e2e_all_12_metrics_present
# - test_e2e_moving_averages_accuracy
# - test_e2e_multiple_universes

# Performance validation (must use @pytest.mark.performance)
pytest tests/integration/test_breadth_metrics_e2e.py::test_e2e_performance_validation -v

# Expected: Calculation time <50ms, API response <100ms

# Service startup validation (if testing full stack)
python start_all_services.py &
sleep 5  # Allow services to initialize

# Health check validation
curl -f http://localhost:5000/health || echo "TickStockAppV2 health check failed"

# API endpoint validation
curl -f "http://localhost:5000/api/breadth-metrics?universe=SPY" | jq '.' || echo "Breadth metrics API failed"

# Expected: 200 OK, JSON with metrics and metadata

# Database connection validation
PGPASSWORD=your_password psql -U app_readwrite -d tickstock -c "SELECT COUNT(*) FROM ohlcv_daily;" || echo "Database connection failed"

# Expected: Row count > 0 (OHLCV data exists)
```

### Level 4: TickStock-Specific Validation

```bash
# Architecture Compliance Validation

# 1. Consumer Role Validation (No database writes)
grep -r "INSERT INTO ohlcv\|UPDATE ohlcv\|DELETE FROM ohlcv" src/core/services/breadth_metrics_service.py
# Expected: No matches (consumer is read-only)

grep -r "INSERT INTO daily_patterns\|UPDATE daily_patterns\|DELETE FROM daily_patterns" src/api/rest/breadth_metrics.py
# Expected: No matches (pattern writes belong in TickStockPL)

# 2. Sprint 64 Pattern Compliance
diff -u <(grep -A 5 "def _query_ohlcv_data" src/core/services/threshold_bar_service.py) \
        <(grep -A 5 "def _query_ohlcv_data" src/core/services/breadth_metrics_service.py)
# Expected: Similar structure (parameterized query, context manager, error handling)

# 3. Performance Benchmarking
pytest tests/integration/test_breadth_metrics_e2e.py::test_e2e_performance_validation -v --durations=10
# Expected: <50ms calculation time, <100ms API response

# 4. Zero Regression Validation
pytest tests/integration/test_pattern_flow_complete.py -v
# Expected: Pattern flow tests still pass (no breaking changes)

python run_tests.py
# Expected: All existing tests still pass

# 5. Security Validation (if security-related changes)
# Check for hardcoded credentials
grep -r "password\|secret\|api_key" src/core/services/breadth_metrics_service.py | grep -v "# " | grep -v "getenv"
# Expected: No matches (no hardcoded secrets)

# 6. Code Quality Validation
# Structure limits
wc -l src/core/services/breadth_metrics_service.py
# Expected: <500 lines per file

# Function complexity (manual check for functions >50 lines)
grep -n "^    def " src/core/services/breadth_metrics_service.py
# Expected: Each function <50 lines

# 7. Documentation Validation
# Verify docstrings present
grep -c '"""' src/core/services/breadth_metrics_service.py
# Expected: Count >= number of methods (each method has docstring)

# 8. Agent Execution Validation (if needed)
# Run domain-specific specialist agents:
# - tickstock-test-specialist: For test coverage validation
# - database-query-specialist: For database query optimization
# - architecture-validation-specialist: MANDATORY for architecture compliance
# - integration-testing-specialist: MANDATORY at end of implementation

# Expected: All validations pass, no architectural violations detected
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] Unit tests pass: `pytest tests/unit/ -v` (30+ tests)
- [ ] API tests pass: `pytest tests/api/rest/test_breadth_metrics_api.py -v` (10+ tests)
- [ ] E2E tests pass: `pytest tests/integration/test_breadth_metrics_e2e.py -v` (5+ tests)

### Feature Validation

- [ ] All success criteria from "What" section met
- [ ] API endpoint `/api/breadth-metrics?universe=SPY` returns valid JSON
- [ ] All 12 metrics present in response (day_change, week, month, quarter, half_year, year, price_to_ema10, price_to_ema20, price_to_sma50, price_to_sma200)
- [ ] Moving averages match expected pandas calculations (EMA10, EMA20, SMA50, SMA200)
- [ ] Percentages sum to 100% (within 0.01% tolerance)
- [ ] Frontend renders 12 metric rows as horizontal bar charts
- [ ] Color coding correct: Green (#28a745) for up/above, Red (#dc3545) for down/below
- [ ] Auto-refresh works (60s interval for intraday data)
- [ ] Universe selector switches data source (SPY, QQQ, dow30)
- [ ] Error cases handled gracefully with proper error messages
- [ ] Integration points work as specified
- [ ] User persona requirements satisfied

### TickStock Architecture Validation

- [ ] Component role respected (Consumer - read-only)
- [ ] No Redis pub-sub channels used (N/A for this feature)
- [ ] Database access mode followed (read-only enforcement)
- [ ] Performance targets achieved (<50ms calculation, <100ms API)
- [ ] Sprint 64 pattern followed exactly (service structure, API endpoint, frontend)
- [ ] No architectural violations detected by architecture-validation-specialist
- [ ] Zero regression: Pattern flow tests still pass

### Code Quality Validation

- [ ] Follows existing codebase patterns and naming conventions
- [ ] File placement matches desired codebase tree structure
- [ ] Anti-patterns avoided (check against Anti-Patterns section below)
- [ ] Dependencies properly managed and imported
- [ ] Configuration changes properly integrated (N/A - no config changes)
- [ ] Code structure limits followed (max 500 lines/file, 50 lines/function)
- [ ] Naming conventions: snake_case functions, PascalCase classes, UPPER_SNAKE_CASE constants
- [ ] Pandas calculations use vectorized operations (groupby().transform(), not apply())
- [ ] Moving averages: EMA uses adjust=False, SMA uses min_periods=period
- [ ] Data sorted by [symbol, timestamp] before MA calculations

### Documentation & Deployment

- [ ] Code is self-documenting with clear variable/function names
- [ ] Logs are informative but not verbose
- [ ] Environment variables documented if new ones added (N/A - no new env vars)
- [ ] No "Generated by Claude" comments in code or commits
- [ ] CLAUDE.md updated with Sprint 66 completion entry
- [ ] SPRINT66_COMPLETE.md created with comprehensive summary
- [ ] API documentation updated (docs/api/endpoints.md)

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't create new patterns when existing ones work (Sprint 64 pattern is proven)
- ❌ Don't skip validation because "it should work" (4-level validation is MANDATORY)
- ❌ Don't ignore failing tests - fix them immediately
- ❌ Don't use sync functions in async context (N/A - no async in this feature)
- ❌ Don't hardcode values that should be config (no config needed, but avoid hardcoding)
- ❌ Don't catch all exceptions - be specific (ValueError, RuntimeError, ValidationError)

### TickStock-Specific Anti-Patterns (CRITICAL)

#### Architecture Violations
- ❌ **Don't mix TickStockApp and TickStockPL roles**
  - AppV2 = Consumer (reads from OHLCV, no writes)
  - PL = Producer (writes to OHLCV, aggregates data)
  - Violation: Adding OHLCV aggregation to BreadthMetricsService

- ❌ **Don't query pattern tables directly in TickStockAppV2**
  - Pattern data comes via Redis pub-sub from TickStockPL (NOT applicable here)
  - This feature queries OHLCV tables only (correct Consumer behavior)

- ❌ **Don't use database writes for OHLCV data in AppV2**
  - OHLCV data writes belong in TickStockPL
  - BreadthMetricsService is read-only (correct)

#### Data Handling
- ❌ **Don't mix typed events and dicts after Worker boundary**
  - NOT applicable (no Worker processes in this feature)

- ❌ **Don't skip data sorting before moving averages**
  - ALWAYS sort by [symbol, timestamp] before MA calculations
  - Violation: Calculating EMA/SMA without df.sort_values(['symbol', 'date'])

- ❌ **Don't use pandas apply() instead of transform()**
  - apply() is 1,300x slower than transform()
  - Use: df.groupby('symbol')['close'].transform(lambda x: ...)
  - Violation: df.groupby('symbol').apply(lambda x: x['close'].ewm(...))

#### Performance
- ❌ **Don't skip performance benchmarking**
  - Database query: <30ms
  - Calculation: <30ms
  - Total: <50ms
  - Violation: Not measuring actual performance in tests

- ❌ **Don't use partial moving averages**
  - EMA: adjust=False (standard EMA)
  - SMA: min_periods=period (true 50-day SMA, not 20-day partial)
  - Violation: min_periods=1 creates invalid SMAs

#### Testing & Validation
- ❌ **Don't skip integration tests before commits**
  - `python run_tests.py` is MANDATORY
  - Violation: Committing without running integration tests

- ❌ **Don't skip Sprint 64 pattern validation**
  - Service structure MUST match threshold_bar_service.py
  - Violation: Creating different architecture without justification

#### Code Quality
- ❌ **Don't exceed structure limits**
  - Max 500 lines per file
  - Max 50 lines per function
  - Violation: 800-line service class

- ❌ **Don't add "Generated by Claude" to code or commits**
  - Keep code and commits clean
  - Violation: Comments like "# Generated with Claude Code"

- ❌ **Don't use center=True for moving averages**
  - Creates forward-looking bias (invalid for backtesting)
  - Always use center=False (default)
  - Violation: df['sma'].rolling(window=50, center=True)

---

## Performance Targets & Validation

| Metric | Target | Validation Method | Critical? |
|--------|--------|-------------------|-----------|
| Database query (252 days × 504 symbols) | <30ms | Measure in unit tests with timing decorator | ✅ Yes |
| All 12 metrics calculation | <30ms | Measure in service tests | ✅ Yes |
| Total service calculation | <50ms | Measure in e2e tests with @pytest.mark.performance | ✅ Yes |
| API endpoint response (with JSON) | <100ms | Measure in API tests | ✅ Yes |
| Frontend rendering (12 rows) | <50ms | Manual browser DevTools Performance tab | No |
| Memory usage (DataFrame) | <100MB | Monitor during tests with memory_profiler | No |
| Cache hit rate (RelationshipCache) | >90% | Check cache statistics after 10 requests | No |

---

## Success Metrics

**Confidence Score**: 9/10 for one-pass implementation success likelihood

**Rationale**:
- ✅ Complete Sprint 64 pattern documentation (proven architecture)
- ✅ Pandas EMA/SMA calculations with documentation URLs
- ✅ Database query patterns with exact SQL
- ✅ Frontend rendering patterns with CSS/JavaScript code
- ✅ Test patterns with examples
- ✅ Performance targets with validation methods
- ✅ Known gotchas and solutions documented
- ✅ "No Prior Knowledge" test passes
- ⚠️ -1 point: Pandas edge cases (NaN handling) may require debugging iteration

---

## References

- **Sprint 64 Complete**: `docs/planning/sprints/sprint64/SPRINT64_COMPLETE.md`
- **User Story**: `docs/planning/sprints/sprint66/userstory.md`
- **ThresholdBarService**: `src/core/services/threshold_bar_service.py`
- **RelationshipCache**: `src/core/services/relationship_cache.py`
- **Database Schema**: `docs/database/schema.md`
- **Pandas EWM Docs**: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html
- **Pandas Rolling Docs**: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html
- **Agent Outputs**:
  - Sprint 64 Patterns: Agent af2b487
  - Pandas EMA/SMA Research: Agent af1b756
  - Architecture Analysis: Agent ac782c6

---

**PRP Quality Score**: 95/100

**Breakdown**:
- Context Completeness: 100/100 (passes "No Prior Knowledge" test)
- Pattern Documentation: 95/100 (comprehensive Sprint 64 + pandas examples)
- Implementation Tasks: 95/100 (dependency-ordered, file-specific)
- Validation Gates: 100/100 (4-level validation with exact commands)
- Information Density: 90/100 (specific URLs, line numbers, code snippets)

**Ready for Execution**: ✅ YES
