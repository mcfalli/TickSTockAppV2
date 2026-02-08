# Sprint 67 - Market Breadth Multi-Instance Enhancement & Reusability

**Status**: Planning
**Priority**: Medium
**Type**: Enhancement & Documentation
**Dependencies**: Sprint 66 (Market Breadth Metrics - Complete)

---

## Sprint Goal

Document and enhance the Market Breadth component for widespread reuse throughout TickStockAppV2, enabling multiple instances per page, creating comparison views, and establishing patterns for similar reusable components.

---

## Current State (Sprint 66 Delivered)

### ✅ What Works Now
- Single instance on "Market Breadth" navigation page
- Template supports multi-instance via `instance_id` parameter
- Universe selector: SPY, QQQ, dow30, nasdaq100
- 12 metrics with auto-refresh (60s)
- Grey striped bar for insufficient data
- Accurate calculations verified against database

### 🎯 What's Possible But Not Yet Implemented
- **Multiple instances on same page** (template supports it, not yet used)
- **Custom titles per instance** (parameter exists, not yet used)
- **Hide controls per instance** (show_controls parameter exists, not yet used)
- **Side-by-side index comparison** (SPY vs QQQ vs dow30)

---

## Proposed Enhancements

### Phase 1: Documentation & Examples (Priority 1)

#### 1.1 Multi-Instance Usage Guide
**File**: `docs/guides/components/market-breadth-usage.md`

**Contents**:
```markdown
# Market Breadth Component - Usage Guide

## Single Instance (Current)
{percent set instance_id='default' percent}
{percent set universe='SPY' percent}
{percent set title='Market Breadth' percent}
{percent include 'dashboard/market_breadth.html' percent}

## Multiple Instances (Side-by-Side)
<!-- SPY Instance -->
{percent set instance_id='spy' percent}
{percent set universe='SPY' percent}
{percent set title='S&P 500 Breadth' percent}
{percent set show_controls=False percent}
{percent include 'dashboard/market_breadth.html' percent}

<!-- QQQ Instance -->
{percent set instance_id='qqq' percent}
{percent set universe='QQQ' percent}
{percent set title='NASDAQ 100 Breadth' percent}
{percent set show_controls=False percent}
{percent include 'dashboard/market_breadth.html' percent}

<!-- dow30 Instance -->
{percent set instance_id='dow' percent}
{percent set universe='dow30' percent}
{percent set title='Dow 30 Breadth' percent}
{percent set show_controls=False percent}
{percent include 'dashboard/market_breadth.html' percent}
```

**Parameters**:
- `instance_id` (required): Unique identifier (e.g., 'spy', 'qqq', 'custom')
- `universe` (required): Universe key (SPY, QQQ, dow30, nasdaq100, russell2000)
- `title` (optional): Display title (default: 'Market Breadth')
- `show_controls` (optional): Show universe selector/refresh (default: True)

**Use Cases**:
1. **Single instance with controls**: Main Market Breadth page (current)
2. **Multiple instances without controls**: Index comparison page
3. **Embedded in other pages**: Stock group analysis, sector rotation
4. **Custom universe**: Theme-specific breadth (e.g., crypto_miners breadth)

#### 1.2 Component API Documentation
**File**: `docs/api/components.md`

**Document**:
- Template parameters
- JavaScript initialization (window.initializeBreadthMetrics_{instance_id})
- API endpoint contract (`/api/breadth-metrics?universe=X`)
- CSS customization points
- Performance characteristics

### Phase 2: Index Comparison Page (Priority 2)

#### 2.1 Create "Index Comparison" Page
**File**: `web/templates/dashboard/index_comparison.html`

**Features**:
- 3-column layout: SPY | QQQ | dow30
- Side-by-side breadth metrics (no controls)
- Highlight divergences (when SPY up but QQQ down, etc.)
- Responsive: Stack vertically on mobile

**Navigation**:
- Add to sidebar under "Market Overview" section
- Icon: fas fa-columns
- Title: "Index Comparison"

**Value Proposition**:
- **Quick divergence spotting**: See when large-cap (SPY) diverges from tech (QQQ)
- **Sector rotation clues**: SPY strong + QQQ weak = defensive rotation
- **Market breadth confirmation**: All indices showing strong breadth = healthy market

#### 2.2 Divergence Highlighting
**Enhancement**: Add visual indicators when indices diverge significantly

**Example**:
- If SPY "Day Chg" is >70% up, but QQQ is <50% up, show warning icon
- Color-code metric rows: Green (all agree), Yellow (divergence), Red (severe divergence)

**Implementation**:
- JavaScript comparison logic after all instances render
- CSS classes: `.metric-divergence`, `.metric-agreement`
- Tooltip: "NASDAQ 100 underperforming S&P 500 by 25%"

### Phase 3: Additional Use Cases (Priority 3)

#### 3.1 Stock Group Breadth
**Location**: Stock Groups page (Sprint 65)

**Enhancement**: When user selects a stock group (ETF/sector/theme), show breadth metrics for that group

**Example**:
- User selects "crypto_miners" theme
- Below the stock list, show breadth metrics for those 20 stocks
- Helps answer: "Are crypto mining stocks broadly moving up or just a few leaders?"

#### 3.2 Sector Rotation Dashboard
**New Page**: `web/templates/dashboard/sector_rotation.html`

**Features**:
- 11 sector breadth metrics in grid (3x4 layout)
- Each sector shows mini breadth chart (Day/Week/Month only)
- Sort by strength (% up descending)
- Identify rotating sectors (Week down, Month up = potential reversal)

**Sectors**:
- Information Technology
- Healthcare
- Financials
- Consumer Discretionary
- Industrials
- Communication Services
- Consumer Staples
- Energy
- Utilities
- Real Estate
- Materials

#### 3.3 Watchlist Breadth
**Location**: User watchlists

**Enhancement**: Show breadth metrics for user's custom watchlist

**Example**:
- User has 50-stock custom watchlist
- Pass `universe=watchlist:{watchlist_id}` to API
- Service loads symbols from user's watchlist table
- Shows breadth metrics for those 50 stocks

**API Enhancement Needed**:
```python
# Support user watchlists in BreadthMetricsService
if universe.startswith('watchlist:'):
    watchlist_id = universe.split(':')[1]
    symbols = self._load_watchlist_symbols(user_id, watchlist_id)
```

### Phase 4: Advanced Features (Priority 4)

#### 4.1 Historical Breadth Comparison
**Feature**: Compare current breadth to previous day/week

**Display**:
- Show delta arrows: ↑ +5% vs yesterday
- Color code: Green (improving), Red (deteriorating)
- Identify trend: "Breadth improving for 3 consecutive days"

#### 4.2 Export Functionality
**Feature**: Export breadth data to CSV/PDF

**Button**: Add to section-controls (when show_controls=True)

**Export Format**:
```csv
Metric,Up,Down,Total,Pct_Up,Universe,Date
Day Chg,400,103,503,79.52,SPY,2026-02-07
Open Chg,364,137,501,72.37,SPY,2026-02-07
...
```

#### 4.3 Threshold Alerts
**Feature**: Alert when breadth crosses thresholds

**Example**:
- Alert when "Day Chg" drops below 40% (bearish breadth)
- Alert when "Price/SMA200" crosses above 60% (bull market confirmed)
- User-configurable thresholds per metric

#### 4.4 Intraday Updates
**Feature**: Show intraday breadth (updated every 5 minutes)

**Current**: Uses daily closes (updates overnight)
**Enhanced**: Uses current prices during market hours

**Implementation**:
- New API param: `timeframe=intraday`
- Service queries live prices from WebSocket tick data
- Auto-refresh every 60s becomes meaningful during market hours

---

## Technical Implementation Details

### Multi-Instance Pattern (Already Implemented)

**Template** (`web/templates/dashboard/market_breadth.html`):
```html
<div class="breadth-metrics-section" data-breadth-instance="{{ instance_id }}">
    <div id="breadth-metrics-container-{{ instance_id }}">...</div>
</div>

<script>
    window['initializeBreadthMetrics_' + instanceId] = function() {
        const renderer = new BreadthMetricsRenderer();
        renderer.render('breadth-metrics-container-' + instanceId, {
            universe: universe,
            title: title,
            showControls: showControls
        });
    };
</script>
```

**JavaScript** (`web/static/js/components/breadth-metrics-renderer.js`):
- Each instance gets unique container ID
- Each instance gets unique initialization function
- Independent refresh timers per instance
- No shared state between instances

**CSS** (`web/static/css/components/breadth-metrics.css`):
- Scoped by container ID
- Theme-aware (light/dark mode)
- Responsive (mobile breakpoints)

### Performance Considerations

**Multiple Instances**:
- 3 instances = 3 API calls = ~150ms total (parallel)
- Each instance refreshes independently (60s stagger)
- Database query cached for 5-10s (avoid duplicate work)

**Optimization Opportunities**:
1. **Batch API**: Single call returns multiple universes
   ```javascript
   GET /api/breadth-metrics?universes=SPY,QQQ,dow30
   // Returns: { SPY: {...}, QQQ: {...}, dow30: {...} }
   ```

2. **Shared Renderer**: Single renderer manages multiple containers
   ```javascript
   const renderer = new BreadthMetricsRenderer();
   renderer.renderMultiple(['spy', 'qqq', 'dow'], configs);
   ```

3. **WebSocket Updates**: Push updates instead of polling
   ```javascript
   socket.on('breadth_update', (data) => {
       renderer.update(data.universe, data.metrics);
   });
   ```

---

## CSS Layout Patterns

### Side-by-Side (3 Columns)
```css
.index-comparison-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin: 20px 0;
}

@media (max-width: 1200px) {
    .index-comparison-grid {
        grid-template-columns: 1fr; /* Stack on tablets/mobile */
    }
}
```

### Compact Mode (Mini Breadth)
```css
.breadth-metrics-container.compact .metric-row {
    height: 30px; /* Reduced from 40px */
    margin-bottom: 5px; /* Reduced from 10px */
}

.breadth-metrics-container.compact .metric-label {
    width: 80px; /* Reduced from 120px */
    font-size: 11px; /* Reduced from 13px */
}
```

---

## Testing Strategy

### Multi-Instance Tests
**File**: `tests/frontend/test_breadth_metrics_multi_instance.py`

**Scenarios**:
1. Load page with 3 instances (SPY, QQQ, dow30)
2. Verify each instance makes separate API call
3. Verify each instance renders independently
4. Verify refresh timers don't conflict
5. Verify changing universe in one doesn't affect others

### Performance Tests
**Target**: 3 instances load in <500ms total

**Metrics**:
- API response time: <50ms per universe
- Parallel API calls: 3 concurrent, ~150ms total
- DOM rendering: <100ms per instance
- Total time to interactive: <500ms

---

## Documentation Deliverables

### Files to Create
1. `docs/guides/components/market-breadth-usage.md` - Usage guide
2. `docs/guides/components/market-breadth-examples.md` - Code examples
3. `docs/api/components.md` - Component API reference
4. `docs/planning/sprints/sprint67/index-comparison-design.md` - Design doc
5. `docs/planning/sprints/sprint67/SPRINT67_COMPLETE.md` - Completion doc

### Updates to Existing Files
1. `docs/guides/features.md` - Add Market Breadth section
2. `docs/api/endpoints.md` - Document /api/breadth-metrics
3. `CLAUDE.md` - Add Sprint 67 status
4. `README.md` - Add Market Breadth to feature list

---

## Sprint 67 Success Criteria

### Phase 1 (Documentation) - Must Have
- ✅ Multi-instance usage guide published
- ✅ Component API documented
- ✅ Example code for 3+ use cases
- ✅ Developer guide for adding breadth to new pages

### Phase 2 (Index Comparison) - Should Have
- ✅ Index Comparison page created
- ✅ 3-column side-by-side layout (SPY, QQQ, dow30)
- ✅ Navigation integration
- ✅ Mobile responsive
- ✅ Zero regression (existing breadth page still works)

### Phase 3 (Integration) - Could Have
- ✅ Stock Group breadth integration
- ✅ Sector rotation dashboard (11 sectors)
- ⚠️ Watchlist breadth (requires API enhancement)

### Phase 4 (Advanced) - Won't Have (Future)
- ⏸️ Historical comparison (deferred to Sprint 68)
- ⏸️ Export functionality (deferred to Sprint 68)
- ⏸️ Threshold alerts (deferred to Sprint 69)
- ⏸️ Intraday updates (deferred to Sprint 70)

---

## Estimated Effort

**Phase 1 (Documentation)**: 1-2 hours
- Create usage guide, examples, API docs
- No coding, just documentation

**Phase 2 (Index Comparison)**: 2-3 hours
- Create index_comparison.html template
- Update sidebar navigation
- Test 3-instance layout
- Mobile responsive adjustments

**Phase 3 (Integrations)**: 3-4 hours
- Stock Group breadth integration
- Sector rotation dashboard (11 instances)
- Grid layout and mini-breadth CSS

**Phase 4 (Advanced)**: 8-12 hours (deferred)
- Historical comparison logic
- Export functionality
- Threshold alerts system
- Intraday data pipeline

**Total Sprint 67 (Phase 1-3)**: 6-9 hours

---

## References

- **Sprint 66**: `docs/planning/sprints/sprint66/SPRINT66_COMPLETE.md`
- **Sprint 64 Pattern**: `docs/planning/sprints/sprint64/threshold-bars.md` (similar reusable component)
- **Template**: `web/templates/dashboard/market_breadth.html`
- **Renderer**: `web/static/js/components/breadth-metrics-renderer.js`
- **Service**: `src/core/services/breadth_metrics_service.py`
- **API**: `src/api/rest/breadth_metrics.py`

---

## Next Steps

1. **Get user approval** on Sprint 67 scope (Phase 1-3)
2. **Close Sprint 66** (feature complete, tests deferred)
3. **Start Sprint 67 Phase 1** (documentation)
4. **Implement Phase 2** (Index Comparison page)
5. **Evaluate Phase 3** (based on user priorities)
6. **Plan Sprint 68** (Advanced features if needed)
