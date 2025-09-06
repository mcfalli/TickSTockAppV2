# Pattern Discovery UI Design: Three-Tiered Dashboard

**Date**: 2025-09-04  
**Sprint**: 18 - Planning Phase  
**Status**: Initial Design Concept  

## User Story Overview

As a TickStock.ai trader, I want a modern, intuitive pattern discovery dashboard that leverages the three-tiered pattern detection architecture (daily, intraday, combo) so that I can efficiently discover trading opportunities, filter by pattern types and indicators, and visualize setups with comprehensive chart analysis—transforming pre-computed pattern and indicator data into actionable trading insights.

**Acceptance Criteria**:
- Three distinct tabs corresponding to Daily Patterns, Intraday Signals, and Combo Alerts
- Read-only consumption of pre-computed pattern/indicator tables from TickStockPL
- Advanced filtering by pattern types, indicator thresholds, and symbol criteria
- Interactive charting with pattern annotations and indicator overlays
- Real-time updates via WebSocket for new pattern detections
- Sub-50ms query performance leveraging indexed pattern/indicator tables
- Responsive design supporting desktop and tablet usage

## Architecture Context

### Data Flow (Read-Only UI Model)
The UI operates as a **pure consumer** of pre-computed data:
- **TickStockPL** (Producer): Populates pattern/indicator tables via three-tiered engines
- **TickStockAppV2** (Consumer): Queries tables for display, no heavy computation
- **Real-time Updates**: WebSocket notifications when new patterns detected
- **Chart Data**: Combines pattern metadata with OHLCV data from TimescaleDB

### Data Sources
```
UI Data Sources:
├── Pre-Computed Tables (from TickStockPL)
│   ├── daily_patterns & daily_indicators
│   ├── intraday_patterns & intraday_indicators  
│   └── daily_intraday_patterns & combo_indicators
├── Historical Data (TimescaleDB)
│   ├── ohlcv_daily (for daily charts)
│   └── ohlcv_minute (for intraday charts)
└── Real-time Data (Optional)
    └── WebSocket feed for live price updates
```

## UI Design Concept

### Navigation Structure
**Primary Tabs** (redesigned for efficiency):
1. **Pattern Scanner** - Search/filter all patterns with dense table view
2. **Market Breadth** - Index ETF analysis (SPY, QQQ, IWM, etc.) with sector rotation
3. **My Focus** - Personal watchlists and saved filter sets with real-time updates

### Modern Layout Architecture

#### High-Density Layout System
```
┌─────────────────────────────────────────────────────────────┐
│              [Pattern Scanner] [Market Breadth] [My Focus]  │
├─────────────────────────────────────────────────────────────┤
│ 🎛️ Filters │          Dense Results Table                   │
│ (Collapsible│          (High Information Density)          │
│     18%)    │                   (82%)                       │
│             │                                               │
│ ┌─────────┐ │ Symbol│Pattern │Conf│ RS │Vol │Price│Time │▲│ │
│ │ PATTERN │ │ AAPL  │WeeklyBO│.92 │1.4x│2.1x│185.5│2hr │📊│ │
│ │ ☑Breakout│ │ NVDA  │BullFlag│.95 │1.6x│3.2x│485.7│1hr │📊│ │
│ │ ☑Volume  │ │ MSFT  │Trendlin│.88 │1.1x│1.8x│415.2│4hr │📊│ │
│ │ ☐Gap     │ │ TSLA  │VolSpike│.94 │1.2x│4.2x│242.8│2m  │📊│ │
│ │         │ │ [25 more rows visible...]                     │
│ │ SCOPE   │ │                                               │
│ │ ●Daily   │ │ [Pagination: 1 2 3 ... 15]                  │
│ │ ●Intraday│ │                                               │
│ │ ●Combo   │ │                                               │
│ │         │ │                                               │
│ │ SYMBOLS │ │                                               │
│ │ 🔍Search │ │                                               │
│ │ □Tech    │ │                                               │
│ │ □Finance │ │                                               │
│ └─────────┘ │                                               │
├─────────────┴───────────────────────────────────────────────┤
│ 📈 CHART - Click row to load • Currently: AAPL Weekly BO   │
│ [Chart loads below table when row selected]                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Filter Control Panel (Left Sidebar)
**Collapsible sidebar** with sections:
- **Pattern Filters**:
  - Checkboxes: Breakouts, Volume Spikes, Trendlines, Gaps
  - Confidence threshold slider (0.5 - 1.0)
- **Indicator Filters**:
  - Relative Strength: > 1.0, > 1.2, > 1.5
  - Volume: > 1.5x, > 2x, > 3x average
  - RSI: Overbought (>70), Oversold (<30), Custom range
- **Symbol Selection**:
  - Search autocomplete
  - Watchlist dropdown
  - Sector/market cap filters
- **Time Controls**:
  - Pattern age: Today, 3 days, 1 week
  - Expiration: Active only, Include expired

#### 2. Results Grid (Center-Top)
**Card-based layout** with infinite scroll:
- **Pattern Cards** (150px height):
  ```
  ┌─────────────────────────────────────────┐
  │ AAPL  📈 Weekly Breakout    Conf: 0.92 │
  │ $185.50 (+2.3%)                        │
  │ RS: 1.4x  Vol: 2.1x  [Sparkline Chart] │
  │ 2hrs ago • Expires: 3 days             │
  └─────────────────────────────────────────┘
  ```
- **Sort Options**: Confidence, Time, Volume, Relative Strength
- **View Modes**: Cards, List, Compact
- **Quick Actions**: Add to watchlist, Set alert, View details

#### 3. Interactive Chart Panel (Center-Bottom)
**Multi-pane charting** with:
- **Primary Chart**: 
  - Candlestick/bar chart with pattern annotations
  - Support/resistance levels highlighted
  - Pattern trigger points marked
- **Indicator Panes**:
  - Volume histogram with relative volume overlay
  - RSI with overbought/oversold zones
  - Custom indicator based on pattern type
- **Timeline Integration**:
  - Daily tab: Shows daily bars with weekly context
  - Intraday tab: Shows minute bars with daily reference line
  - Combo tab: Dual-timeframe view (daily + intraday sync)

#### 4. Live Activity Feed (Right Sidebar - Optional)
**Real-time updates** via WebSocket:
- **New Pattern Alerts**: "TSLA - Intraday volume spike detected"
- **Pattern Updates**: "AAPL - Weekly breakout confidence increased to 0.95"
- **Expiration Notices**: "NVDA - Daily trendline pattern expires in 1hr"

## Technical Implementation Notes

### Performance Optimizations
- **Lazy Loading**: Load chart data only when pattern card clicked
- **Pagination**: 20-50 pattern cards per page with infinite scroll
- **Caching**: Redis cache for frequent symbol/pattern queries
- **Indexes**: Optimized queries on `symbol + pattern_type + timestamp`

### Real-time Integration
```python
# WebSocket pattern updates
@socketio.on('pattern_update')
def handle_pattern_update(data):
    # Update UI card without full page refresh
    emit('pattern_updated', {
        'symbol': data['symbol'],
        'pattern_type': data['type'],
        'confidence': data['confidence'],
        'timestamp': data['detected_at']
    })
```

### Responsive Design
- **Desktop**: Full three-panel layout
- **Tablet**: Collapsible sidebar, stacked chart below results
- **Mobile**: Single column with tabbed navigation

## User Experience Flow

### Daily Patterns Tab
1. User opens Daily tab → Loads persistent patterns from `daily_patterns` table
2. Applies filters → SQL query with indexed WHERE clauses
3. Clicks pattern card → Loads daily OHLCV chart with pattern annotations
4. Views indicator overlays → Displays pre-computed values from `daily_indicators`

### Intraday Signals Tab  
1. User opens Intraday tab → Loads recent patterns from `intraday_patterns` table
2. Real-time updates → WebSocket pushes new detections as they occur
3. Clicks pattern → Shows minute-bar chart with pattern trigger point
4. Auto-refresh → Cards update confidence/expiration in real-time

### Combo Alerts Tab
1. User opens Combo tab → Loads hybrid patterns from `daily_intraday_patterns`
2. Shows context → Displays related daily setup + intraday confirmation
3. Multi-timeframe view → Synchronized daily and intraday charts
4. Advanced filtering → Combines daily and intraday criteria

## Next Steps
- Create detailed wireframe document with visual mockups
- Define REST API endpoints for pattern/indicator queries
- Plan WebSocket event schema for real-time updates
- Design responsive breakpoints and mobile experience
- Prototype pattern card interaction patterns

This design leverages the three-tiered architecture for efficient, real-time pattern discovery while maintaining the TickStockAppV2 consumer role.