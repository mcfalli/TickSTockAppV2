# Market Breadth Component API

**Sprint 66/67**: Component API reference for Market Breadth Metrics

---

## Overview

The Market Breadth Component provides a reusable UI for displaying up/down participation metrics across 12 timeframes and technical indicators. This document describes the JavaScript API, template parameters, REST endpoints, and CSS customization points.

---

## JavaScript API

### BreadthMetricsRenderer Class

The main JavaScript class for rendering breadth metrics.

#### Constructor

```javascript
const renderer = new BreadthMetricsRenderer();
```

**Parameters**: None

**Returns**: BreadthMetricsRenderer instance

---

#### Methods

##### `async render(containerId, config)`

Renders breadth metrics into the specified container.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `containerId` | string | Yes | DOM element ID where metrics will be rendered |
| `config` | object | Yes | Configuration object |
| `config.universe` | string | Yes | Universe key (SPY, QQQ, dow30, etc.) |
| `config.title` | string | No | Section title (default: 'Market Breadth') |
| `config.showControls` | boolean | No | Show universe selector and refresh button (default: true) |

**Returns**: Promise<void>

**Example**:
```javascript
const renderer = new BreadthMetricsRenderer();
await renderer.render('breadth-metrics-container-spy', {
    universe: 'SPY',
    title: 'S&P 500 Breadth',
    showControls: false
});
```

---

##### `async fetchData(universe)`

Fetches breadth metrics data from the API.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `universe` | string | Yes | Universe key (SPY, QQQ, etc.) |

**Returns**: Promise<object> - API response with metrics and metadata

**Example**:
```javascript
const data = await renderer.fetchData('SPY');
console.log(data.metrics.day_change); // {up: 400, down: 103, unchanged: 0, pct_up: 79.52}
```

---

##### `createMetricsHTML(metrics, metadata)`

Generates HTML for the 12 metric rows.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metrics` | object | Yes | Metrics data from API |
| `metadata` | object | Yes | Metadata with symbol count |

**Returns**: string - HTML for metric rows

**Example**:
```javascript
const html = renderer.createMetricsHTML(data.metrics, data.metadata);
document.getElementById('metrics-container').innerHTML = html;
```

---

##### `setupAutoRefresh(universe, config)`

Sets up auto-refresh timer (60-second interval).

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `universe` | string | Yes | Universe key to refresh |
| `config` | object | Yes | Render configuration |

**Returns**: void

**Note**: Each instance has independent refresh timer. Timers are cleared on re-initialization to prevent memory leaks.

---

##### `_getCSRFToken()`

Extracts CSRF token from meta tag or cookies (internal method).

**Parameters**: None

**Returns**: string - CSRF token or empty string

**Usage**: Automatically called by `fetchData()` for API authentication.

---

## Template API

### market_breadth.html Parameters

The Jinja2 template accepts the following parameters via `{% set %}` directives.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `instance_id` | string | **Yes** | N/A | Unique identifier for this instance. MUST be unique per include to avoid DOM collisions. |
| `universe` | string | **Yes** | N/A | Universe key: SPY, QQQ, dow30, nasdaq100, russell2000, etc. |
| `title` | string | No | 'Market Breadth' | Display title for the breadth metrics section |
| `show_controls` | boolean | No | True | Show/hide universe selector and refresh button. Set to False for fixed-universe displays. |

#### Parameter Details

**`instance_id`** (Critical):
- Creates unique DOM IDs: `breadth-metrics-container-{instance_id}`
- Creates unique initialization function: `window.initializeBreadthMetrics_{instance_id}`
- Must be unique across all includes on the same page
- Examples: 'default', 'spy', 'qqq', 'dow', 'group_breadth'

**`universe`**:
- Valid keys: SPY, QQQ, dow30, nasdaq100, russell2000, IWM, DIA
- Also supports: sector keys, theme keys, custom universe keys
- Case-insensitive (normalized to uppercase by API)

**`title`**:
- Displayed in section header
- Keep concise (2-4 words recommended)
- Examples: 'Market Breadth', 'S&P 500 Breadth', 'Crypto Miners'

**`show_controls`**:
- True: Shows universe selector and refresh button (default)
- False: Hides controls for fixed-universe displays (Index Comparison, embedded views)

---

### Usage Example

```jinja2
{% set instance_id='spy' %}
{% set universe='SPY' %}
{% set title='S&P 500 Breadth' %}
{% set show_controls=False %}
{% include 'dashboard/market_breadth.html' %}
```

---

## REST API

### GET /api/breadth-metrics

Retrieves breadth metrics for the specified universe.

**Endpoint**: `GET /api/breadth-metrics?universe={key}`

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `universe` | string | No | 'SPY' | Universe key (SPY, QQQ, dow30, etc.) |

**Response** (200 OK):

```json
{
    "metrics": {
        "day_change": {"up": 400, "down": 103, "unchanged": 0, "pct_up": 79.52},
        "open_change": {"up": 364, "down": 137, "unchanged": 0, "pct_up": 72.37},
        "week": {"up": 332, "down": 170, "unchanged": 0, "pct_up": 66.0},
        "month": {"up": 329, "down": 174, "unchanged": 0, "pct_up": 65.41},
        "quarter": {"up": 356, "down": 146, "unchanged": 0, "pct_up": 70.92},
        "half_year": {"up": 333, "down": 167, "unchanged": 0, "pct_up": 66.6},
        "year": {"up": 0, "down": 0, "unchanged": 0, "pct_up": 0.0},
        "price_to_ema10": {"up": 352, "down": 151, "unchanged": 0, "pct_up": 69.98},
        "price_to_ema20": {"up": 348, "down": 155, "unchanged": 0, "pct_up": 69.18},
        "price_to_sma50": {"up": 342, "down": 161, "unchanged": 0, "pct_up": 67.99},
        "price_to_sma200": {"up": 0, "down": 0, "unchanged": 0, "pct_up": 0.0}
    },
    "metadata": {
        "universe": "SPY",
        "symbol_count": 503,
        "calculation_time_ms": 45.2,
        "calculated_at": "2026-02-08T12:00:00Z"
    }
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 400 | ValidationError | Invalid universe key or parameter format |
| 400 | ValueError | Universe key not found in RelationshipCache |
| 500 | RuntimeError | Database query error or calculation failure |
| 500 | Exception | Unexpected server error |

**Example Error (400)**:

```json
{
    "error": "ValueError",
    "message": "Universe 'INVALID' not found",
    "status": 400
}
```

**Performance**:
- Target: <100ms per request
- Typical: 45-70ms for 500-symbol universe
- Database query: <30ms
- Calculation: <50ms

**Full API Documentation**: See [endpoints.md](endpoints.md) for complete REST API reference.

---

## CSS Classes

### Customization Points

The breadth metrics component uses scoped CSS classes that can be customized.

| Class | Purpose | Customizable Properties |
|-------|---------|-------------------------|
| `.breadth-metrics-section` | Main container | `margin`, `padding`, `background` |
| `.section-header` | Header with title and controls | `padding`, `border`, `background` |
| `.metric-row` | Individual metric row | `height`, `margin`, `padding`, `border` |
| `.metric-label` | Metric name label | `width`, `font-size`, `color` |
| `.metric-bar-container` | Bar chart container | `flex`, `height`, `border` |
| `.metric-bar-up` | Green up bar | `background`, `gradient`, `color` |
| `.metric-bar-down` | Red down bar | `background`, `gradient`, `color` |
| `.metric-counts` | Up/down count display | `width`, `font-size`, `color` |
| `.metric-insufficient-data` | Grey striped bar for missing data | `background`, `opacity` |

### Theme Support

The component respects the application's light/dark theme:

```css
/* Light theme variables */
:root {
    --breadth-bg-color: #ffffff;
    --breadth-text-color: #212529;
    --breadth-border-color: #dee2e6;
}

/* Dark theme variables */
[data-theme="dark"] {
    --breadth-bg-color: #1a1d23;
    --breadth-text-color: #e9ecef;
    --breadth-border-color: #495057;
}
```

### Compact Mode (Multi-Instance Pages)

For Index Comparison and sector grids, use compact styling:

```css
.index-comparison-grid .metric-row {
    height: 35px; /* Reduced from 40px */
    margin-bottom: 8px; /* Reduced from 10px */
}

.index-comparison-grid .metric-label,
.index-comparison-grid .metric-counts {
    width: 110px; /* Reduced from 120px */
    font-size: 12px; /* Reduced from 13px */
}
```

### Responsive Breakpoints

```css
/* Mobile adjustments */
@media (max-width: 768px) {
    .metric-row {
        height: 40px;
    }
    .metric-label {
        width: 80px;
        font-size: 11px;
    }
}

/* Tablet and up */
@media (min-width: 768px) {
    .metric-row {
        height: 40px;
    }
}

/* Desktop */
@media (min-width: 1200px) {
    .index-comparison-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
```

---

## Complete Usage Examples

### Example 1: Standalone Page with Controls

```html
<!-- HTML Template -->
{% set instance_id='default' %}
{% set universe='SPY' %}
{% set title='Market Breadth' %}
{% include 'dashboard/market_breadth.html' %}
```

**JavaScript**: Initialization auto-generated by template

**Features**: Universe selector, refresh button, auto-refresh

---

### Example 2: Index Comparison (3 Instances)

```html
<!-- HTML Template -->
<div class="index-comparison-grid">
    <div class="index-column">
        {% set instance_id='spy' %}
        {% set universe='SPY' %}
        {% set title='S&P 500 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>
    <div class="index-column">
        {% set instance_id='qqq' %}
        {% set universe='QQQ' %}
        {% set title='NASDAQ 100 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>
    <div class="index-column">
        {% set instance_id='dow' %}
        {% set universe='dow30' %}
        {% set title='Dow 30 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>
</div>
```

**JavaScript**: Initialize all 3 instances

```javascript
setTimeout(() => {
    window.initializeBreadthMetrics_spy?.();
    window.initializeBreadthMetrics_qqq?.();
    window.initializeBreadthMetrics_dow?.();
}, 200);
```

**CSS**: Grid layout with responsive breakpoint

```css
.index-comparison-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

@media (max-width: 1200px) {
    .index-comparison-grid {
        grid-template-columns: 1fr;
    }
}
```

---

### Example 3: Programmatic Rendering

```javascript
// Create renderer instance
const renderer = new BreadthMetricsRenderer();

// Render into specific container
await renderer.render('my-container-id', {
    universe: 'nasdaq100',
    title: 'NASDAQ 100 Breadth',
    showControls: false
});

// Setup auto-refresh (optional)
renderer.setupAutoRefresh('nasdaq100', {
    universe: 'nasdaq100',
    title: 'NASDAQ 100 Breadth',
    showControls: false
});
```

---

## Related Documentation

- **Usage Guide**: [guides/components/market-breadth-usage.md](../guides/components/market-breadth-usage.md)
- **API Endpoints**: [api/endpoints.md](endpoints.md)
- **Sprint 66 Implementation**: [planning/sprints/sprint66/SPRINT66_COMPLETE.md](../planning/sprints/sprint66/SPRINT66_COMPLETE.md)
- **Sprint 67 Multi-Instance**: [planning/sprints/sprint67/SPRINT67_COMPLETE.md](../planning/sprints/sprint67/SPRINT67_COMPLETE.md)

---

## Support

For issues or questions:
1. Check browser console for JavaScript errors
2. Verify universe key exists in RelationshipCache
3. Test API endpoint directly: `curl "http://localhost:5000/api/breadth-metrics?universe=SPY"`
4. Review component source: `web/static/js/components/breadth-metrics-renderer.js`
