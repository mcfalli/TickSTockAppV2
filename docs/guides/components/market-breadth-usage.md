# Market Breadth Component - Usage Guide

**Sprint 66/67**: Reusable market breadth metrics component

---

## Overview

The Market Breadth Component displays up/down participation metrics across 12 timeframes and technical indicators for any stock universe. It visualizes market health and trend strength through horizontal bar charts showing the percentage of stocks moving up versus down.

### What It Shows

- **Day/Open Changes**: Intraday and overnight movements
- **Period Changes**: Week, month, quarter, half-year, year performance
- **Moving Average Positions**: Price vs EMA10, EMA20, SMA50, SMA200

### When to Use It

- **Single Instance**: Main Market Breadth page with universe selector
- **Multiple Instances**: Index Comparison page (SPY vs QQQ vs dow30)
- **Embedded**: Stock group analysis, sector rotation dashboards
- **Custom Universes**: Theme-specific breadth (e.g., crypto miners, semiconductors)

---

## Component Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `instance_id` | string | Yes | N/A | Unique identifier for this instance (e.g., 'default', 'spy', 'qqq') |
| `universe` | string | Yes | N/A | Universe key: SPY, QQQ, dow30, nasdaq100, russell2000, etc. |
| `title` | string | No | 'Market Breadth' | Display title for the breadth metrics section |
| `show_controls` | boolean | No | True | Show/hide universe selector and refresh button |

---

## Usage Examples

### Example 1: Single Instance with Controls (Current Market Breadth Page)

Use this pattern for a standalone page where users can change universes.

```jinja2
<!-- In your template (e.g., market_breadth.html) -->
{% set instance_id='default' %}
{% set universe='SPY' %}
{% set title='Market Breadth' %}
<!-- show_controls defaults to True, showing universe selector -->
{% include 'dashboard/market_breadth.html' %}
```

**Features**:
- Universe selector visible (SPY, QQQ, dow30, nasdaq100)
- Refresh button available
- Auto-refresh every 60 seconds
- User can switch between universes

---

### Example 2: Multiple Instances Side-by-Side (Index Comparison)

Use this pattern to compare breadth across multiple indices simultaneously.

```jinja2
<!-- In your template (e.g., index_comparison.html) -->
<div class="index-comparison-grid">
    <!-- S&P 500 Column -->
    <div class="index-column">
        {% set instance_id='spy' %}
        {% set universe='SPY' %}
        {% set title='S&P 500 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>

    <!-- NASDAQ 100 Column -->
    <div class="index-column">
        {% set instance_id='qqq' %}
        {% set universe='QQQ' %}
        {% set title='NASDAQ 100 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>

    <!-- Dow 30 Column -->
    <div class="index-column">
        {% set instance_id='dow' %}
        {% set universe='dow30' %}
        {% set title='Dow 30 Breadth' %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>
</div>
```

**Features**:
- Fixed universes (no selectors)
- Each instance independent with separate API calls
- Auto-refresh works for all instances
- Parallel API fetching for performance

**CSS Required**:
```css
.index-comparison-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

@media (max-width: 1200px) {
    .index-comparison-grid {
        grid-template-columns: 1fr; /* Stack on mobile */
    }
}
```

---

### Example 3: Embedded in Stock Group Page

Use this pattern to show breadth metrics for a selected stock group.

```jinja2
<!-- When user selects a stock group -->
<div class="stock-group-breadth">
    {% set instance_id='group_breadth' %}
    {% set universe=selected_group_key %}  <!-- e.g., 'crypto_miners' -->
    {% set title='{{ selected_group_name }} Breadth' %}
    {% set show_controls=False %}
    {% include 'dashboard/market_breadth.html' %}
</div>
```

**Use Case**: Show breadth metrics for the 20 stocks in a selected theme (e.g., "Are crypto mining stocks broadly moving up or just a few leaders?")

---

### Example 4: Sector Rotation Dashboard (11 Sectors)

Use this pattern to create a grid of breadth metrics for all sectors.

```jinja2
<!-- In sector_rotation.html template -->
<div class="sector-grid">
    {% for sector in sectors %}
    <div class="sector-card">
        {% set instance_id='sector_' ~ loop.index %}
        {% set universe=sector.key %}
        {% set title=sector.name %}
        {% set show_controls=False %}
        {% include 'dashboard/market_breadth.html' %}
    </div>
    {% endfor %}
</div>
```

**CSS**:
```css
.sector-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 15px;
}
```

---

### Example 5: Custom Universe (Theme Breadth)

Use this pattern for custom universes like themes or watchlists.

```jinja2
<!-- Crypto miners theme breadth -->
{% set instance_id='crypto_breadth' %}
{% set universe='crypto_miners' %}
{% set title='Crypto Miners Breadth' %}
{% set show_controls=False %}
{% include 'dashboard/market_breadth.html' %}
```

**Supported Universes**:
- **ETFs**: SPY, QQQ, IWM, DIA
- **Index Universes**: nasdaq100, sp500, dow30, russell2000
- **Sectors**: information_technology, healthcare, financials, etc.
- **Themes**: crypto_miners, semiconductors, ev_companies, etc.

---

## JavaScript Initialization

Each instance creates a unique initialization function:

```javascript
// For instance_id='spy'
window.initializeBreadthMetrics_spy = function() {
    const renderer = new BreadthMetricsRenderer();
    renderer.render('breadth-metrics-container-spy', {
        universe: 'SPY',
        title: 'S&P 500 Breadth',
        showControls: false
    });
};

// Call after content is loaded
setTimeout(() => {
    if (typeof window.initializeBreadthMetrics_spy === 'function') {
        window.initializeBreadthMetrics_spy();
    }
}, 200);
```

**Multiple Instances**:
```javascript
// Initialize all 3 instances after content is loaded
setTimeout(() => {
    window.initializeBreadthMetrics_spy?.();
    window.initializeBreadthMetrics_qqq?.();
    window.initializeBreadthMetrics_dow?.();
}, 200);
```

---

## Performance Considerations

### API Calls

- **Single Instance**: 1 API call, ~100ms response time
- **3 Instances (Parallel)**: 3 API calls, ~150-300ms total (parallel fetch)
- **11 Instances (Sectors)**: 11 API calls, ~500-800ms total

**Optimization**: API responses are fast (<100ms per universe), so parallel fetching is acceptable for up to ~10 instances.

### Auto-Refresh

- Each instance has independent 60-second refresh timer
- Timers may fire simultaneously (acceptable, API can handle concurrent requests)
- No refresh coordination needed

### Caching

- Service calculates metrics on-the-fly (no pre-computed cache)
- Database queries optimized with RelationshipCache (<1ms symbol loading)
- Vectorized pandas operations for fast calculations

---

## Troubleshooting

### Issue: Instance ID Collision

**Symptom**: Multiple instances show same data or only last instance renders

**Cause**: Non-unique `instance_id` values

**Fix**: Ensure each include has unique `instance_id`
```jinja2
<!-- WRONG -->
{% set instance_id='default' %}{% include ... %}
{% set instance_id='default' %}{% include ... %}

<!-- CORRECT -->
{% set instance_id='spy' %}{% include ... %}
{% set instance_id='qqq' %}{% include ... %}
```

---

### Issue: Initialization Function Not Found

**Symptom**: Console error: "initializeBreadthMetrics_xxx is not a function"

**Cause**: Content not loaded or incorrect `instance_id` in initialization call

**Fix**: Verify `instance_id` matches between template and initialization:
```javascript
// Template: instance_id='spy'
// Initialization: window.initializeBreadthMetrics_spy()
```

---

### Issue: API Returns 400 Error

**Symptom**: Breadth metrics show "Error loading data"

**Cause**: Invalid universe key

**Fix**: Verify universe key exists in RelationshipCache:
```bash
# Valid keys: SPY, QQQ, dow30, nasdaq100, russell2000, etc.
# Check: src/core/services/relationship_cache.py
```

---

### Issue: Metrics Show All Zeros

**Symptom**: All 12 metrics show 0 up, 0 down, 0.0% up

**Cause**: Insufficient historical data for universe

**Fix**:
- Requires 252 trading days of OHLCV data
- Check `ohlcv_daily` table for data coverage
- SMA200 requires 200+ days, year metric requires 252+ days

---

### Issue: Auto-Refresh Not Working

**Symptom**: Metrics don't update after 60 seconds

**Cause**: Initialization function not called or renderer error

**Fix**: Check browser console for errors, verify initialization:
```javascript
// Should see: "BreadthMetricsRenderer initialized for breadth-metrics-container-spy"
```

---

## Related Documentation

- **Component API Reference**: [docs/api/components.md](../../api/components.md)
- **API Endpoint Documentation**: [docs/api/endpoints.md](../../api/endpoints.md)
- **Sprint 66 Implementation**: [docs/planning/sprints/sprint66/SPRINT66_COMPLETE.md](../../planning/sprints/sprint66/SPRINT66_COMPLETE.md)
- **Sprint 67 Multi-Instance**: [docs/planning/sprints/sprint67/SPRINT67_COMPLETE.md](../../planning/sprints/sprint67/SPRINT67_COMPLETE.md)

---

## Support

For issues or questions:
1. Check browser console for errors
2. Verify universe key exists in RelationshipCache
3. Test API endpoint directly: `GET /api/breadth-metrics?universe=SPY`
4. Review Sprint 66/67 documentation for implementation details
