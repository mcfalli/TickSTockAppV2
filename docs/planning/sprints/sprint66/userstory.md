# Sprint 66: Market Breadth Metrics Display Control

**Status**: Planning
**Created**: 2026-02-07
**Sprint Type**: Feature Implementation (Reusable Component)
**Estimated Effort**: 2-3 days (PRP-enhanced workflow)

---

## User Story

> **As a** broad-market context trader,
> **I want** a reusable market breadth display control showing up/down metrics across various time periods and moving average relationships for any stock universe (S&P 500, NASDAQ 100, Dow 30, etc.)
> **so I can** quickly assess participation breadth and trend health across different market segments at a glance.

**Multi-Page Reusable Component**: This control will appear on multiple pages throughout the application (Market Overview, Sector Analysis, Index Comparison, etc.), each instance displaying breadth metrics for different universes.

**Acceptance Criteria**:
- ✅ Display shows 12 metric rows: Day Chg, Open Chg, Week, Month, QTR, Half Year, Year, Price/EMA10, Price/EMA20, Price/SMA50, Price/SMA200
- ✅ Each metric shows up count, down count, and percentage
- ✅ Rendered as compact horizontal bar chart grid
- ✅ Color-coded: Green (up/above), Red (down/below)
- ✅ Configurable universe parameter (SPY, QQQ, dow30, nasdaq100, etc.)
- ✅ Reusable component can appear multiple times on same page with different universes
- ✅ Optional title parameter for customization ("S&P 500 Breadth", "NASDAQ 100 Breadth", etc.)
- ✅ Auto-refresh every 60 seconds for intraday updates
- ✅ Performance: <50ms calculation, <100ms API response
- ✅ Mobile-responsive layout

---

## Architecture Analysis Summary

### Database State (No Changes Required ✅)

**Existing Infrastructure (Ready to Use)**:
- ✅ `definition_groups` + `group_memberships` - Multiple universes available (SPY: 504 stocks, QQQ: 102 stocks, dow30: 30 stocks, nasdaq100: 102 stocks, etc.)
- ✅ `ohlcv_daily` table - Complete historical price data (252+ days)
- ✅ `ohlcv_1min`, `ohlcv_hourly` - Intraday data for real-time updates
- ✅ `RelationshipCache` - Sub-millisecond symbol loading for any universe
- ⚠️ `daily_indicators`, `intraday_indicators` - Tables exist but are **EMPTY** (not used)

**Key Finding**: No database schema changes required. All necessary data exists in current OHLCV tables.

**Default Universe for Development**: SPY (504 stocks) - easily configurable to any universe via `universe` parameter.

### Architecture Decision: On-the-Fly Calculation (Sprint 64 Pattern)

**Rationale**:

| Factor | On-the-Fly (✅ Recommended) | Pre-Calculation (❌ Not Recommended) |
|--------|----------------------------|-------------------------------------|
| **Architecture Compliance** | ✅ Consumer read-only | ❌ Requires Producer writes |
| **Sprint 64 Consistency** | ✅ Identical pattern | ❌ Diverges from proven pattern |
| **Performance** | ✅ <50ms proven | ~Equal, adds complexity |
| **Database Schema** | ✅ Zero changes | ❌ New indicator tables |
| **Data Freshness** | ✅ Always current | ⚠️ Depends on refresh schedule |
| **Maintenance** | ✅ Simple service layer | ❌ Producer job + cache management |
| **Scalability** | ✅ Stateless | ❌ Stateful cache requires sync |

**Sprint 64 Validation**: ThresholdBarService proves <50ms for 500+ symbol aggregations using identical architecture.

---

## Technical Specifications

### 12 Metric Rows (Breadth Indicators)

#### Category 1: Price Change Comparisons (7 metrics)

| Metric Row | Calculation | Data Needed | Formula |
|------------|-------------|-------------|---------|
| **Day Chg** | Today close vs yesterday close | 2 days OHLCV | `(close_today - close_yesterday) / close_yesterday` |
| **Open Chg** | Today close vs today open | 1 day OHLCV | `(close_today - open_today) / open_today` |
| **Week** | Close vs 5 trading days ago | 5 days OHLCV | `(close_latest - close_5d_ago) / close_5d_ago` |
| **Month** | Close vs 21 trading days ago | 21 days OHLCV | `(close_latest - close_21d_ago) / close_21d_ago` |
| **Quarter** | Close vs 63 trading days ago | 63 days OHLCV | `(close_latest - close_63d_ago) / close_63d_ago` |
| **Half Year** | Close vs 126 trading days ago | 126 days OHLCV | `(close_latest - close_126d_ago) / close_126d_ago` |
| **Year** | Close vs 252 trading days ago | 252 days OHLCV | `(close_latest - close_252d_ago) / close_252d_ago` |

**Logic**: Count stocks where `pct_change > 0` (up) vs `pct_change < 0` (down)

#### Category 2: Moving Average Comparisons (4 metrics)

| Metric Row | Calculation | Data Needed | Formula |
|------------|-------------|-------------|---------|
| **Price/EMA10** | Price above/below 10-day EMA | 10 days OHLCV | `close > EMA(10)` |
| **Price/EMA20** | Price above/below 20-day EMA | 20 days OHLCV | `close > EMA(20)` |
| **Price/SMA50** | Price above/below 50-day SMA | 50 days OHLCV | `close > SMA(50)` |
| **Price/SMA200** | Price above/below 200-day SMA | 200 days OHLCV | `close > SMA(200)` |

**EMA Formula** (Exponential Moving Average):
```python
df['ema'] = df.groupby('symbol')['close'].transform(
    lambda x: x.ewm(span=period, adjust=False).mean()
)
```

**SMA Formula** (Simple Moving Average):
```python
df['sma'] = df.groupby('symbol')['close'].transform(
    lambda x: x.rolling(window=period, min_periods=period).mean()
)
```

**Logic**: Count stocks where `close > ema/sma` (above) vs `close < ema/sma` (below)

### Performance Optimization Strategy

**Single Query Approach** (Fetch Once, Calculate All):
1. Load universe symbols via RelationshipCache: `get_universe_symbols(universe)`
   - Example: `get_universe_symbols('SPY')` → **504 symbols** (SPY has 504 holdings, not 500)
   - Works with any universe: QQQ (102), dow30 (30), nasdaq100 (102), etc.
2. Query 252 days of OHLCV data for those symbols
   - SPY example: `252 days × 504 symbols = 127,008 rows` (one query)
   - QQQ example: `252 days × 102 symbols = 25,704 rows`
3. Calculate all 12 metrics from same DataFrame using pandas vectorized operations
4. Return up/down/unchanged counts per metric based on the actual universe constituents

**Expected Performance** (using SPY as baseline):
- Database query: <30ms (TimescaleDB chunk exclusion optimization)
- Calculation (all 12 metrics): <30ms (vectorized pandas operations)
- Total calculation time: **<50ms** (proven achievable by Sprint 64)
- API response (with JSON serialization): <100ms
- Frontend rendering: <50ms

**Calculation Example** (SPY universe):
- When universe="SPY", the service calculates metrics based on the 504 stocks that constitute the SPY ETF
- If 345 stocks are up and 159 are down for "Day Change", the response shows: `{"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5}`

---

## Implementation Approach (Option 1: Traditional Workflow)

### Phase 1: Backend Service Layer

**Files to Create**:

#### 1. `src/core/services/breadth_metrics_service.py` (~300 lines)

**Class Structure**:
```python
class BreadthMetricsService:
    """Service for calculating market breadth metrics for any stock universe.

    Calculates 12 metrics showing up/down counts across time periods
    and moving average relationships for market breadth analysis.

    Supports any universe: SPY (504 stocks), QQQ (102 stocks), dow30 (30 stocks), etc.

    Performance targets:
    - Full 12-metric calculation: <50ms
    - Database query: <30ms
    - API endpoint response: <100ms
    """

    def __init__(self, relationship_cache=None, db=None, config=None):
        """Initialize with dependency injection (for testing)."""
        self.relationship_cache = relationship_cache or get_relationship_cache()
        self.db = db or TickStockDatabase(config or load_config())

    def calculate_breadth_metrics(self, universe: str = 'SPY') -> dict:
        """Calculate all 12 breadth metrics in one pass.

        Args:
            universe: Universe key (default: 'SPY' for S&P 500)

        Returns:
            Dictionary with structure:
            {
                "metrics": {
                    "day_change": {"up": 345, "down": 159, "unchanged": 0, "pct_up": 68.5},
                    "week": {"up": 390, "down": 114, "unchanged": 0, "pct_up": 77.4},
                    ...
                },
                "metadata": {
                    "symbol_count": 504,
                    "calculation_time_ms": 42.3,
                    "calculated_at": "2026-02-07T14:45:00Z"
                }
            }
        """
        # Step 1: Load symbols via RelationshipCache
        symbols = self.relationship_cache.get_universe_symbols(universe)

        # Step 2: Fetch 252 days of OHLCV data (covers all periods up to 1 year)
        df = self._query_ohlcv_data(symbols, timeframe='daily', period_days=252)

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

        return {"metrics": metrics, "metadata": {...}}

    def _calculate_day_change(self, df: pd.DataFrame) -> dict:
        """Today close vs yesterday close."""

    def _calculate_open_change(self, df: pd.DataFrame) -> dict:
        """Today close vs today open."""

    def _calculate_period_change(self, df: pd.DataFrame, days: int) -> dict:
        """Generic period change (5=week, 21=month, etc.)."""

    def _calculate_ema_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Price vs EMA (10 or 20 day)."""

    def _calculate_sma_comparison(self, df: pd.DataFrame, period: int) -> dict:
        """Price vs SMA (50 or 200 day)."""

    def _query_ohlcv_data(self, symbols: list, timeframe: str, period_days: int) -> pd.DataFrame:
        """Query OHLCV data from TimescaleDB (reuse from ThresholdBarService)."""
```

**Pattern Reference**: Follow `src/core/services/threshold_bar_service.py` exactly (Sprint 64)

#### 2. `src/core/models/breadth_metrics_models.py` (~150 lines)

**Pydantic v2 Models**:
```python
from pydantic import BaseModel, Field, field_validator

class BreadthMetricsRequest(BaseModel):
    """Request model for breadth metrics API."""
    universe: str = Field(default='SPY', description="Universe key (e.g., 'SPY', 'QQQ')")

    @field_validator('universe')
    def validate_universe(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("universe must be non-empty string")
        return v.upper()

class MetricData(BaseModel):
    """Single metric data."""
    up: int = Field(ge=0, description="Count of stocks up/above")
    down: int = Field(ge=0, description="Count of stocks down/below")
    unchanged: int = Field(ge=0, description="Count of stocks unchanged")
    pct_up: float = Field(ge=0.0, le=100.0, description="Percentage up/above")

class BreadthMetricsResponse(BaseModel):
    """Response model for breadth metrics API."""
    metrics: dict[str, MetricData]
    metadata: dict

class BreadthMetricsErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str | None = None
```

#### 3. `src/api/rest/breadth_metrics.py` (~120 lines)

**Flask Blueprint**:
```python
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

breadth_metrics_bp = Blueprint('breadth_metrics', __name__, url_prefix='/api')

@breadth_metrics_bp.route('/breadth-metrics', methods=['GET'])
def get_breadth_metrics():
    """Calculate S&P 500 breadth metrics.

    Query Parameters:
        universe (str): Universe key (default: 'SPY')

    Returns:
        JSON response with metrics and metadata

    Status Codes:
        200: Success
        400: Validation error (invalid universe)
        500: Server error (database failure, calculation error)
    """
    try:
        # Validate request
        req = BreadthMetricsRequest(universe=request.args.get('universe', 'SPY'))

        # Calculate metrics
        service = BreadthMetricsService()
        result = service.calculate_sp500_breadth(universe=req.universe)

        return jsonify(result), 200

    except ValidationError as e:
        return jsonify(BreadthMetricsErrorResponse(error="Validation error", detail=str(e)).dict()), 400
    except ValueError as e:
        return jsonify(BreadthMetricsErrorResponse(error="Invalid request", detail=str(e)).dict()), 400
    except RuntimeError as e:
        return jsonify(BreadthMetricsErrorResponse(error="Server error", detail=str(e)).dict()), 500
```

**Blueprint Registration** (`src/app.py`):
```python
from src.api.rest.breadth_metrics import breadth_metrics_bp
app.register_blueprint(breadth_metrics_bp)
```

#### 4. `tests/core/services/test_breadth_metrics_service.py` (~350 lines)

**Test Coverage**:
- Service initialization (dependency injection)
- Symbol loading via RelationshipCache
- OHLCV data querying
- Day change calculation
- Open change calculation
- Period change calculation (week, month, quarter, etc.)
- EMA calculation and comparison
- SMA calculation and comparison
- Edge cases (empty symbols, missing data, insufficient history)
- Error handling (ValueError, RuntimeError)

#### 5. `tests/api/rest/test_breadth_metrics_api.py` (~200 lines)

**Test Coverage**:
- Blueprint registration
- Request validation (valid/invalid universe keys)
- Default parameters (universe='SPY')
- Response structure validation
- Error responses (400, 500)
- Service mocking (isolated endpoint testing)

### Phase 2: Frontend Display Control

**Files to Create**:

#### 6. `web/static/js/components/breadth-metrics-renderer.js` (~250 lines)

**JavaScript Module** (Reusable Component):
```javascript
class BreadthMetricsRenderer {
    constructor(options = {}) {
        this.apiEndpoint = '/api/breadth-metrics';
        this.csrfToken = options.csrfToken || '';
        this.refreshInterval = 60000; // 60 seconds
    }

    async render(containerId, config = {}) {
        // config = { universe: 'SPY', title: 'S&P 500 Breadth', showControls: true }
        const universe = config.universe || 'SPY';
        const title = config.title || 'Market Breadth';
        const showControls = config.showControls !== false;

        // Fetch data from API
        const data = await this.fetchData(universe);

        // Render 12 metric rows as horizontal bar charts
        const container = document.getElementById(containerId);
        container.innerHTML = this.createMetricsHTML(data, title, showControls);

        // Setup auto-refresh
        this.setupAutoRefresh(containerId, config);
    }

    createMetricsHTML(data, title, showControls) {
        // Generate HTML with flexbox horizontal bars
        // Each metric = one row with green (up) and red (down) segments
        // Title is configurable per instance
    }

    createHorizontalBar(metric) {
        // Create diverging bar with percentage widths
        // Green (left-to-right for up), Red (right-to-left for down)
    }
}

// Usage examples:
// Instance 1: renderer.render('container1', { universe: 'SPY', title: 'S&P 500 Breadth' });
// Instance 2: renderer.render('container2', { universe: 'QQQ', title: 'NASDAQ 100 Breadth' });
// Instance 3: renderer.render('container3', { universe: 'dow30', title: 'Dow 30 Breadth', showControls: false });
```

#### 7. `web/static/css/components/breadth-metrics.css` (~200 lines)

**CSS Flexbox Layout**:
```css
.breadth-metrics-container {
    width: 100%;
    padding: 20px;
    background: var(--card-background);
    border-radius: 8px;
}

.metric-row {
    display: flex;
    align-items: center;
    height: 35px;
    margin-bottom: 8px;
}

.metric-label {
    width: 120px;
    font-weight: 600;
    font-size: 13px;
    color: var(--text-primary);
}

.metric-bar-container {
    flex: 1;
    display: flex;
    align-items: center;
    height: 24px;
    background: var(--bar-background);
    border-radius: 4px;
    overflow: hidden;
}

.metric-bar-up {
    background: linear-gradient(90deg, #28a745, #34d058);
    transition: width 0.3s ease;
}

.metric-bar-down {
    background: linear-gradient(90deg, #dc3545, #f85149);
    transition: width 0.3s ease;
}

.metric-counts {
    width: 120px;
    text-align: right;
    font-size: 12px;
    font-weight: 600;
}

.count-up { color: #28a745; }
.count-down { color: #dc3545; }
```

#### 8. `web/templates/dashboard/market_breadth.html` (~180 lines)

**Reusable Dashboard Section Template**:
```html
<!-- Reusable component - can appear multiple times with different configurations -->
<div class="breadth-metrics-section" data-breadth-instance="{{ instance_id }}">
    <div class="section-header">
        <h2>{{ title | default('Market Breadth') }}</h2>
        {% if show_controls %}
        <div class="section-controls">
            <button class="breadth-refresh-btn btn btn-sm btn-primary">
                <i class="fas fa-sync-alt"></i> Refresh
            </button>
            <select class="breadth-universe-select form-select form-select-sm">
                <option value="SPY" {% if universe == 'SPY' %}selected{% endif %}>S&P 500 (SPY)</option>
                <option value="QQQ" {% if universe == 'QQQ' %}selected{% endif %}>NASDAQ 100 (QQQ)</option>
                <option value="dow30" {% if universe == 'dow30' %}selected{% endif %}>Dow 30</option>
                <option value="nasdaq100" {% if universe == 'nasdaq100' %}selected{% endif %}>NASDAQ 100</option>
            </select>
        </div>
        {% endif %}
    </div>

    <div id="breadth-metrics-container-{{ instance_id }}" class="breadth-metrics-container">
        <!-- Rendered by breadth-metrics-renderer.js -->
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i> Calculating breadth metrics...
        </div>
    </div>

    <div class="section-footer">
        <span class="text-muted">
            <i class="fas fa-info-circle"></i>
            Green = Above/Up | Red = Below/Down | Auto-refresh: 60s
        </span>
        <span class="breadth-last-update text-muted"></span>
    </div>
</div>

<script>
// Initialize this instance
(function() {
    const instanceId = '{{ instance_id }}';
    const universe = '{{ universe | default("SPY") }}';
    const title = '{{ title | default("Market Breadth") }}';

    window['initializeBreadthMetrics_' + instanceId] = function() {
        const renderer = new BreadthMetricsRenderer();
        renderer.render('breadth-metrics-container-' + instanceId, {
            universe: universe,
            title: title,
            showControls: {{ 'true' if show_controls else 'false' }}
        });

        // Only attach event handlers if controls are shown
        {% if show_controls %}
        const section = document.querySelector('[data-breadth-instance="' + instanceId + '"]');
        section.querySelector('.breadth-refresh-btn').addEventListener('click', () => {
            const currentUniverse = section.querySelector('.breadth-universe-select').value;
            renderer.render('breadth-metrics-container-' + instanceId, {
                universe: currentUniverse,
                title: title
            });
        });

        section.querySelector('.breadth-universe-select').addEventListener('change', (e) => {
            renderer.render('breadth-metrics-container-' + instanceId, {
                universe: e.target.value,
                title: title
            });
        });
        {% endif %}
    };

    // Auto-initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window['initializeBreadthMetrics_' + instanceId]);
    } else {
        window['initializeBreadthMetrics_' + instanceId]();
    }
})();
</script>

<!--
USAGE EXAMPLES:

Example 1: S&P 500 with controls
{% include 'dashboard/market_breadth.html' with instance_id='spy', universe='SPY', title='S&P 500 Breadth', show_controls=True %}

Example 2: NASDAQ 100 without controls (compact display)
{% include 'dashboard/market_breadth.html' with instance_id='qqq', universe='QQQ', title='NASDAQ 100 Breadth', show_controls=False %}

Example 3: Dow 30 on Market Overview page
{% include 'dashboard/market_breadth.html' with instance_id='dow', universe='dow30', title='Dow 30 Breadth' %}

Multiple instances on same page:
{% include 'dashboard/market_breadth.html' with instance_id='breadth1', universe='SPY', title='S&P 500 Breadth' %}
{% include 'dashboard/market_breadth.html' with instance_id='breadth2', universe='QQQ', title='NASDAQ 100 Breadth' %}
{% include 'dashboard/market_breadth.html' with instance_id='breadth3', universe='dow30', title='Dow 30 Breadth' %}
-->
```

**Navigation Integration** (`web/static/js/components/sidebar-navigation-controller.js`):
```javascript
// Add to navigation sections
{
    id: 'market-breadth',
    label: 'Market Breadth',
    icon: 'fas fa-chart-bar',
    initFunction: 'initializeBreadthMetrics_default'  // Default instance
}
```

### Phase 3: Integration Testing

#### 9. `tests/integration/test_breadth_metrics_e2e.py` (~200 lines)

**End-to-End Tests**:
```python
class TestBreadthMetricsE2E:
    def test_e2e_full_breadth_calculation(self):
        """Test full flow: RelationshipCache → DB → Service → API → Response"""

    def test_e2e_performance_validation(self):
        """Validate <50ms calculation time for 500+ symbols"""

    def test_e2e_all_12_metrics(self):
        """Verify all 12 metrics return valid up/down counts"""

    def test_e2e_moving_averages(self):
        """Validate EMA/SMA calculations match expected values"""

    def test_e2e_multiple_universes(self):
        """Test SPY, QQQ, dow30 universe switching"""
```

### Phase 4: Documentation

#### 10. Update Documentation Files

**Files to Update**:
- `CLAUDE.md` - Add Sprint 66 completion entry
- `docs/planning/sprints/sprint66/SPRINT66_COMPLETE.md` - Create completion summary
- `docs/api/endpoints.md` - Document `/api/breadth-metrics` endpoint
- `docs/guides/features.md` - Add S&P 500 Breadth Metrics feature description

---

## Validation Gates (4-Level)

### Level 1: Syntax & Style
```bash
ruff check src/core/services/breadth_metrics_service.py --fix
ruff check src/api/rest/breadth_metrics.py --fix
ruff format src/
```

### Level 2: Unit Tests
```bash
pytest tests/core/services/test_breadth_metrics_service.py -v
pytest tests/api/rest/test_breadth_metrics_api.py -v
# Expected: 30+ tests passing
```

### Level 3: Integration Tests (MANDATORY)
```bash
python run_tests.py
# Expected: Pattern flow tests + breadth metrics e2e tests passing
```

### Level 4: Architecture Validation
```bash
# Run architecture-validation-specialist
# Verify:
# - No database write operations (grep for INSERT/UPDATE/DELETE)
# - RelationshipCache used for symbol loading
# - Read-only database access via context manager
# - Performance target met (<50ms)
# - Sprint 64 pattern followed exactly
```

---

## Performance Targets (Non-Negotiable)

| Operation | Target | Validation Method |
|-----------|--------|-------------------|
| Database query (252 days × 504 symbols) | <30ms | Measure in unit tests |
| All 12 metrics calculation | <30ms | Measure in service tests |
| Total service calculation | <50ms | Measure in e2e tests |
| API endpoint response (with JSON) | <100ms | Measure in API tests |
| Frontend rendering (12 rows) | <50ms | Manual browser testing |

---

## Success Criteria

- [x] BreadthMetricsService calculates all 12 metrics correctly
- [x] Moving averages (EMA10, EMA20, SMA50, SMA200) calculated accurately
- [x] API endpoint validates requests with Pydantic v2
- [x] API returns proper error responses (400, 500)
- [x] Frontend renders 12 metric rows as horizontal bar charts
- [x] Color coding: Green (up/above), Red (down/below)
- [x] Auto-refresh every 60 seconds
- [x] Universe selector (SPY, QQQ, dow30)
- [x] Unit tests passing (30+ tests)
- [x] Integration tests passing (5+ e2e tests)
- [x] Performance targets met (<50ms calculation, <100ms API)
- [x] Ruff linting clean (0 violations)
- [x] Documentation updated (CLAUDE.md, API docs)
- [x] Zero regression: Existing tests still pass

---

## Files to Create/Modify Summary

### New Files (9 files)
1. `src/core/services/breadth_metrics_service.py` (300 lines) - Generic service for any universe
2. `src/core/models/breadth_metrics_models.py` (150 lines) - Pydantic v2 models with universe parameter
3. `src/api/rest/breadth_metrics.py` (120 lines) - REST API endpoint accepting universe parameter
4. `web/static/js/components/breadth-metrics-renderer.js` (250 lines) - Reusable renderer component
5. `web/static/css/components/breadth-metrics.css` (200 lines) - Generic styles
6. `web/templates/dashboard/market_breadth.html` (200 lines) - Reusable template with instance_id, universe, and title parameters
7. `tests/core/services/test_breadth_metrics_service.py` (350 lines)
8. `tests/api/rest/test_breadth_metrics_api.py` (200 lines)
9. `tests/integration/test_breadth_metrics_e2e.py` (200 lines)

### Modified Files (4 files)
1. `src/app.py` (register breadth_metrics_bp blueprint)
2. `web/static/js/components/sidebar-navigation-controller.js` (add "Market Breadth" navigation item)
3. `web/templates/dashboard/index.html` (include market_breadth.html with default SPY instance)
4. `CLAUDE.md` (add Sprint 66 completion entry)

**Total**: 13 files (~2,000 lines of code including tests)

**Design Notes**:
- All file names are generic (breadth_metrics, market_breadth)
- No "S&P 500" or "SPY" in file names or class names
- Component is fully reusable via template parameters
- Multiple instances can coexist on same page
- SPY used as default development example (504 stocks)

---

## Next Steps (After Review)

1. **User Reviews This Document** - Validate goals, metrics, and approach
2. **Run PRP Creation** - `/prp-new-create sp500-breadth-metrics`
   - Agent will research Sprint 64 patterns
   - Generate implementation-ready PRP with complete context
   - Include all formulas, schemas, and gotchas
3. **Execute PRP** - `/prp-new-execute sp500-breadth-metrics.md`
   - One-pass implementation with progressive validation
   - Follows Sprint 64 proven architecture
   - 4-level validation gates built-in

---

## References

- **Sprint 64 (Threshold Bars)**: `docs/planning/sprints/sprint64/SPRINT64_COMPLETE.md`
- **ThresholdBarService**: `src/core/services/threshold_bar_service.py`
- **RelationshipCache**: `src/core/services/relationship_cache.py`
- **Database Schema**: `docs/database/schema.md`
- **Architecture Analysis**: Agent ac782c6 (2026-02-07 analysis session)

---

**Sprint 66 Ready for PRP Process** ✅
