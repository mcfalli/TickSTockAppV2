# Pattern Discovery Tab User Guide

**Date**: 2025-09-07  
**Version**: Production Guide  
**Status**: Active Feature - Sprint 23 Complete  
**Dashboard URL**: `/dashboard` (Pattern Discovery Tab)  
**Primary JavaScript**: `/web/static/js/services/pattern-discovery.js`  
**Supporting Services**: See Table Column Analysis section below

---

## Overview

The **Pattern Discovery Dashboard** is TickStock.ai's primary interface for real-time pattern scanning and analysis. It provides high-performance access to pattern data through a unified, information-dense interface designed for efficient market scanning and opportunity identification.

### Core Purpose
- **Real-time Pattern Scanning**: Discover trading patterns across thousands of symbols with <50ms response times
- **Advanced Filtering**: Filter patterns by type, confidence, relative strength, volume, and custom criteria
- **Interactive Visualization**: View pattern charts with annotations and technical indicators
- **WebSocket Integration**: Receive real-time pattern alerts and updates as they occur

### Architecture Overview
The dashboard operates as a **consumer** in TickStock.ai's architecture:
- **Data Source**: Consumes pre-computed pattern data from TickStockPL via Redis pub-sub
- **Performance**: Multi-layer Redis caching ensures <50ms API responses with >85% cache hit ratios
- **Real-time Updates**: WebSocket connections provide instant pattern alerts and status updates
- **Database Access**: Read-only access for symbols and user data (zero direct pattern table queries)

---

## Dashboard Access and Navigation

### Accessing the Dashboard
1. **Login** to your TickStock.ai account at `/login`
2. **Navigate** to the main dashboard at `/dashboard`
3. **Select** the "Pattern Discovery" tab (active by default)

### Main Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ TickStock.ai                        🔍 Search   👤 Profile     │
├─────────────────────────────────────────────────────────────────┤
│    [Pattern Discovery*] [Analytics] [Backtesting] [Alerts]     │
├─────────────────┬───────────────────────────────────────────────┤
│ 🎛️ FILTERS      │        PATTERN RESULTS TABLE                 │
│ (Collapsible)   │        High-Density View                     │
│                 │                                               │
│ Pattern Types   │ Symbol│Pattern│Conf│RS│Vol│Price│Time│Chart   │
│ ☑ Breakouts     │ AAPL  │Weekly │.92 │1.4│2.1│185.5│2hr │ 📊   │
│ ☑ Volume        │ NVDA  │Bull   │.95 │1.6│3.2│485.7│1hr │ 📊   │
│ ☑ Trendlines    │ MSFT  │Trend  │.88 │1.1│1.8│415.2│4hr │ 📊   │
│ ☐ Gaps          │                                               │
│                 │ [Pagination and Export Controls]              │
│ Confidence      │                                               │
│ ●●●○ > 0.85     │                                               │
│ ●●○○ > 0.70     │                                               │
│                 │                                               │
│ Filters...      │                                               │
├─────────────────┴───────────────────────────────────────────────┤
│ 📈 INTERACTIVE CHART - Click any row to load                   │
│ [Pattern annotations, indicators, and analysis tools]          │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Interface Components

### 1. Filter Panel (Left Sidebar)

The collapsible filter panel provides comprehensive pattern filtering capabilities:

#### Pattern Type Filters
- **Breakouts** ☑: Weekly breakouts, daily breakouts, resistance breaks
- **Volume** ☑: Volume spikes, unusual volume, volume confirmations  
- **Trendlines** ☐: Trendline breaks, support/resistance tests
- **Gaps** ☐: Gap fills, gap plays, opening gaps
- **Reversals** ☐: Reversal patterns, momentum shifts

#### Confidence Levels
- **High Confidence** ●●●○ (> 0.85): Strongest pattern signals
- **Medium Confidence** ●●○○ (> 0.70): Solid pattern signals  
- **Low Confidence** ●○○○ (> 0.50): Emerging pattern signals

#### Technical Indicators
- **Relative Strength**: Filter by RS multiples (>1.0x, >1.2x, >1.5x)
- **Volume**: Filter by volume multiples (>1.5x, >2.0x, >3.0x average)
- **RSI Ranges**: Custom RSI ranges (30-70, >70 overbought, <30 oversold)

#### Symbol Selection
- **Search Box** 🔍: Autocomplete symbol search
- **Watchlists**: Filter by personal watchlists
- **Universe Selection**: Market Leaders, Tech, Healthcare, Finance sectors
- **Market Cap**: Large cap, mid cap, small cap filters

#### Time Controls
- **Pattern Age**: Last 4 hours, Today, 3 days, 1 week
- **Expiration**: Active only, I)nclude expired patterns
- **Timeframe**: All, Daily only, Intraday only, Combo patterns

### 2. Pattern Results Table (Center

**High-density tabular display** optimized for rapid scanning:

| Column | Description | Example |
|--------|-------------|---------|
| **Symbol** | Stock ticker | AAPL, NVDA, MSFT |
| **Pattern** | Pattern type (abbreviated) | WeeklyBO, BullFlag, VolSpike |
| **Conf** | Confidence score (0-1) | 0.92, 0.88, 0.75 |
| **RS** | Relative strength multiple | 1.4x, 0.9x, 2.1x |
| **Vol** | Volume multiple vs average | 2.1x, 1.8x, 4.2x |
| **Price** | Current/trigger price | $185.50, $485.75 |
| **Chg** | Price change percentage | +2.3%, -0.8% |
| **Time** | Pattern detection time | 2hr, 15m, 1d |
| **Exp** | Pattern expiration | 3d, 4h, 1w |
| **Chart** | Quick chart access | 📊 (clickable) |

#### Table Features
- **Sortable Columns**: Click column headers to sort by any field
- **Row Selection**: Click rows to load charts and detailed analysis
- **Pagination**: Navigate through large result sets (30 per page default)
- **Export**: Download results as CSV or JSON
- **Auto-refresh**: Configurable auto-refresh (15s, 30s, 1m, 5m intervals)

## Table Column Analysis

The Pattern Discovery table uses a **dynamic column enhancement system** where multiple JavaScript services contribute additional columns beyond the base 9 columns. This creates a rich, information-dense interface.

### Base Columns (9 columns)
**Source**: `/web/static/js/services/pattern-discovery.js` (lines 205-213)

The foundation table structure includes:

| Column | Description | Data Source |
|--------|-------------|-------------|
| **Symbol** | Stock ticker symbol | Pattern API data |
| **Pattern** | Pattern type abbreviation | Pattern API data |
| **Confidence** | Pattern confidence score (0-1) | Pattern API data |
| **Price** | Current/trigger price | Pattern API data |
| **Change** | Price change percentage | Pattern API data |
| **RS** | Relative strength multiple | Pattern API data |
| **Volume** | Volume multiple vs average | Pattern API data |
| **Detected** | Pattern detection timestamp | Pattern API data |
| **Actions** | Chart/analysis actions | UI controls |

### Enhanced Columns (3 additional columns)
**Source**: `/web/static/js/services/pattern-visualization.js` (PatternVisualizationService)

The Pattern Visualization service dynamically adds three enhanced columns **before the Detected column**:

#### 1. Trend Momentum Column
- **Header**: "Trend" with "Momentum" subtitle
- **Icon**: Chart line icon (`fas fa-chart-line`)
- **Content**: Trend direction indicators (up/down/sideways arrows)
- **Implementation**: `createTrendCell()` method (line 433)
- **Data Source**: Enhanced pattern data from API or mock generation

#### 2. Context Column  
- **Header**: "Context" with "Market Info" subtitle  
- **Icon**: Info circle icon (`fas fa-info-circle`)
- **Content**: Market condition badges (bullish/bearish/neutral)
- **Implementation**: `createContextCell()` method (line 457)
- **Data Source**: Market condition analysis data

#### 3. Performance Column
- **Header**: "Performance" with "Success Rate" subtitle
- **Icon**: Trophy icon (`fas fa-trophy`) 
- **Content**: Pattern quality indicators and success metrics
- **Implementation**: `createPerformanceCell()` method (line 478)
- **Data Source**: Historical pattern performance data

### Column Integration System

#### Service Loading Order
**HTML Template**: `/web/templates/dashboard/index.html` (lines 412-435)

Services are loaded in this sequence:
1. `pattern-discovery.js` - Creates base table structure
2. `pattern-visualization.js` - Adds enhanced columns
3. Other analytics services - Loaded but don't modify main table

#### Dynamic Enhancement Process

**Initialization Flow**:
```javascript
// 1. PatternVisualizationService auto-initializes on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    window.patternVisualization = new PatternVisualizationService();
});

// 2. Service checks for pattern table and enhances it
checkPatternDiscovery() {
    const patternTable = document.getElementById('pattern-table');
    if (patternTable) {
        this.enhancePatternTable(patternTable);
    }
}

// 3. Columns are added to header and existing rows enhanced
enhancePatternTable(table) {
    const thead = table.querySelector('thead tr');
    const tbody = table.querySelector('tbody');
    
    this.addEnhancedColumns(thead);      // Add 3 column headers
    this.enhancePatternRows(patterns);   // Add cells to existing rows
}
```

#### Column Insertion Logic
**File**: `/web/static/js/services/pattern-visualization.js` (lines 241-248, 401-404)

Enhanced columns are strategically inserted **before the "Detected" column**:
```javascript
// Header insertion (reverse order for correct positioning)
if (actionsHeader) {
    thead.insertBefore(performanceHeader, actionsHeader);
    thead.insertBefore(contextHeader, actionsHeader);
    thead.insertBefore(trendHeader, actionsHeader);
}

// Row cell insertion (before 8th column - "Detected")
const detectedCell = allCells[7]; // 0-based index
if (detectedCell) {
    row.insertBefore(performanceCell, detectedCell);
    row.insertBefore(contextCell, detectedCell);
    row.insertBefore(trendCell, detectedCell);
}
```

### Final Table Structure (12 columns total)

| Index | Column | Source | Enhancement |
|-------|--------|--------|-------------|
| 0 | Symbol | pattern-discovery.js | Base |
| 1 | Pattern | pattern-discovery.js | Base |
| 2 | Confidence | pattern-discovery.js | Base |
| 3 | Price | pattern-discovery.js | Base |
| 4 | Change | pattern-discovery.js | Base |
| 5 | RS | pattern-discovery.js | Base |
| 6 | Volume | pattern-discovery.js | Base |
| 7 | **Trend Momentum** | pattern-visualization.js | **Enhanced** |
| 8 | **Context** | pattern-visualization.js | **Enhanced** |
| 9 | **Performance** | pattern-visualization.js | **Enhanced** |
| 10 | Detected | pattern-discovery.js | Base |
| 11 | Actions | pattern-discovery.js | Base |

### Service Coordination

#### Non-Modifying Services
These services are loaded but **do not modify the main pattern table**:
- **pattern-comparison.js** - Creates separate comparison modals/tables
- **pattern-correlations.js** - Creates separate correlation matrix tables
- **pattern-temporal.js** - No table modifications found
- **pattern-analytics.js** - Creates separate analytics displays

#### Enhancement Detection
The visualization service uses **CSS class markers** to prevent duplicate enhancements:
```javascript
// Check if already enhanced before adding columns
if (thead.querySelector('.trend-header')) return;
if (row.querySelector('.trend-cell')) return;
```

#### Performance Characteristics
- **Column Addition**: Happens during page load, no runtime performance impact
- **Row Enhancement**: Applied to existing rows when new patterns are loaded
- **Memory Efficiency**: Uses CSS classes for state management
- **No Column Conflicts**: Only visualization service modifies main table structure

This architecture allows the Pattern Discovery table to start with a lean 9-column structure and be dynamically enhanced with rich analytical columns, providing users with comprehensive market intelligence while maintaining clean separation of concerns between services.

### 3. Interactive Chart Panel (Bottom)

**Advanced charting** with pattern annotations and technical analysis:

#### Chart Features
- **Pattern Annotations**: Visual markers for pattern trigger points, targets, and stop levels
- **Technical Indicators**: RSI, Volume, Moving Averages, Relative Strength overlays  
- **Multiple Timeframes**: Switch between 1m, 5m, 15m, 1h, 4h, daily, weekly views
- **Drawing Tools**: Add custom trendlines, support/resistance levels
- **Pattern Metadata**: Confidence scores, target prices, risk levels displayed

#### Chart Interaction
- **Click Table Row**: Automatically loads chart for selected pattern
- **Zoom & Pan**: Mouse wheel zoom, click-and-drag navigation
- **Indicator Toggle**: Show/hide various technical indicators
- **Export Options**: Save charts as PNG, PDF, or data export

#### Real-time Updates
- **Live Price Data**: Real-time price updates via WebSocket
- **Pattern Updates**: Pattern confidence and status updates
- **Alert Integration**: Visual alerts when patterns trigger or expire

---

## Core Functionality

### Pattern Scanning Workflow

1. **Set Filters**: Configure pattern types, confidence levels, and symbol criteria
2. **Review Results**: Scan high-density table for interesting patterns
3. **Analyze Charts**: Click patterns to view detailed chart analysis
4. **Take Action**: Add to watchlists, set alerts, or export data

### Real-time Pattern Alerts

The dashboard provides **live WebSocket updates** for:
- **New Pattern Detections**: Instant alerts when new patterns are found
- **Pattern Updates**: Confidence score changes and status updates  
- **Expiration Notices**: Alerts when patterns approach expiration
- **Price Action**: Real-time price movements for tracked patterns

### Advanced Filtering Capabilities

#### Combination Filters
- **Multi-pattern Logic**: Find symbols with multiple pattern confirmations
- **Cross-timeframe Analysis**: Daily patterns confirmed by intraday signals
- **Sector Rotation**: Patterns within specific sectors or industries
- **Market Breadth**: ETF and index patterns for broader market context

#### Saved Filter Sets
- **Personal Presets**: Save frequently used filter combinations
- **Quick Access**: One-click access to saved searches
- **Sharing**: Export filter sets for team collaboration

---

## Performance and Technical Details

### Response Time Characteristics
- **Pattern Scanning**: <25ms typical response (target: <50ms)
- **Chart Loading**: <100ms for pattern visualization
- **WebSocket Updates**: <100ms end-to-end latency
- **Filter Application**: Real-time with 300ms debouncing

### Data Freshness
- **Pattern Cache**: 1-hour TTL for pattern entries
- **API Cache**: 30-second TTL for API responses  
- **Real-time Events**: Immediate WebSocket delivery
- **Database Sync**: Symbols and user data updated every 10 seconds

### Concurrent User Support
- **Simultaneous Users**: 250+ concurrent dashboard users
- **WebSocket Connections**: 500+ real-time connections supported
- **Redis Operations**: 10,000+ operations/second sustained performance

---

## Integration with Other Services

### WebSocket Event Integration

The dashboard subscribes to multiple **Redis pub-sub channels**:

```javascript
// Real-time pattern updates
socket.on('pattern_alert', (data) => {
    // Update pattern table with new detections
    updatePatternTable(data.event.data);
    showNotification(`New ${data.pattern} pattern on ${data.symbol}`);
});

// Pattern expiration alerts  
socket.on('pattern_expiring', (data) => {
    // Highlight patterns approaching expiration
    highlightExpiringPattern(data.symbol, data.pattern);
});
```

### API Integration

**REST API endpoints** consumed by the dashboard:

- **GET /api/patterns/scan**: Main pattern scanning with advanced filtering
- **GET /api/patterns/summary**: High-level pattern statistics  
- **GET /api/symbols**: Symbol metadata and search functionality
- **GET /api/users/universe**: Universe and watchlist management
- **GET /api/pattern-discovery/health**: Service health monitoring

### Database Relationships

The dashboard accesses **read-only database views**:
- **symbols table**: Stock metadata, names, exchanges, market cap data
- **user_universe**: Personal watchlists and universe selections  
- **cache_entries**: Universe definitions and criteria
- **Redis cache**: All pattern data consumed via Redis (zero direct pattern table queries)

---

## Mobile and Responsive Design

### Responsive Breakpoints

#### Desktop (≥1200px)
- **Full Layout**: Three-panel layout with sidebar, table, and chart
- **All Features**: Complete functionality with advanced filtering
- **High Density**: Maximum information density for power users

#### Tablet (768px - 1199px)  
- **Collapsible Sidebar**: Filters collapse to maximize table space
- **Card Layout**: Pattern results switch to card-based layout
- **Touch Optimization**: Larger touch targets for mobile interaction

#### Mobile (≤767px)
- **Single Column**: Stacked layout optimized for small screens
- **Simplified Filters**: Essential filters with dropdown selection
- **Swipe Navigation**: Touch-friendly navigation between patterns

### Mobile-Specific Features
- **Pull-to-Refresh**: Refresh pattern data with pull gesture
- **Infinite Scroll**: Load more patterns by scrolling down
- **One-Tap Actions**: Quick access to charts, watchlists, alerts

---

## Troubleshooting and Support

### Common Issues

#### **Pattern Data Not Loading**
- **Check Connection**: Verify WebSocket connection status in top-right
- **Refresh Page**: Hard refresh (Ctrl+F5) to reload cached data  
- **Clear Filters**: Reset filters if no results are showing
- **Browser Console**: Check for JavaScript errors in Developer Tools

#### **Charts Not Displaying**
- **Symbol Selection**: Ensure a pattern row is selected in the table
- **Data Availability**: Some symbols may have limited chart data
- **Browser Compatibility**: Use modern browsers (Chrome, Firefox, Safari, Edge)

#### **Real-time Updates Missing**
- **WebSocket Status**: Check connection indicator in navigation bar
- **Firewall Settings**: Ensure WebSocket connections are not blocked
- **Page Refresh**: Reconnect WebSocket by refreshing the page

#### **Performance Issues**
- **Filter Scope**: Reduce filter scope to limit result set size
- **Browser Resources**: Close unnecessary tabs to free memory
- **Network Connection**: Verify stable internet connection for real-time data

### Performance Monitoring

**Built-in monitoring displays:**
- **API Response Times**: Shown in pattern table footer
- **Cache Hit Ratios**: Displayed in filter panel
- **WebSocket Status**: Connection indicator in navigation
- **Pattern Count**: Real-time pattern statistics

### Support Resources

- **User Stories**: See [`user_stories.md`](../planning/user_stories.md) for detailed feature requirements
- **API Documentation**: [`pattern-discovery-api.md`](../api/pattern-discovery-api.md) for technical API details  
- **System Architecture**: [`system-architecture.md`](../architecture/system-architecture.md) for overall system design
- **Integration Guide**: [`integration-guide.md`](integration-guide.md) for TickStockPL integration details

---

## Advanced Features

### Pattern Alert System

Set up **automated alerts** for pattern discoveries:
- **Custom Criteria**: Define specific pattern types, confidence levels, symbols
- **Multiple Delivery**: Email, SMS, WebSocket, webhook notifications
- **Alert History**: Track and review past pattern alerts
- **Snooze/Mute**: Temporarily disable alerts for specific symbols

### Export and Data Analysis

**Export capabilities** for external analysis:
- **CSV Export**: Pattern data with all metadata fields
- **JSON Export**: Structured data for programmatic analysis  
- **Chart Export**: Save charts as PNG/PDF for reporting
- **API Access**: Direct API access for custom integrations

### Backtesting Integration

**Connect patterns to backtesting**:
- **Historical Performance**: View historical success rates for pattern types
- **Pattern Validation**: Backtest specific patterns over historical data
- **Strategy Building**: Use pattern discoveries to build automated strategies

---

## Related Documentation

This guide is part of TickStock.ai's comprehensive documentation suite:

**Core Documentation:**
- **[Project Overview](../planning/project-overview.md)** - Complete system vision, requirements, and architecture principles
- **[System Architecture](../architecture/system-architecture.md)** - Detailed role separation between TickStockApp and TickStockPL
- **[User Stories](../planning/user_stories.md)** - User-focused requirements and functionality specifications

**Technical Documentation:**  
- **[Pattern Discovery API](../api/pattern-discovery-api.md)** - Complete REST API reference with endpoints and examples
- **[Integration Guide](integration-guide.md)** - TickStockPL integration setup and configuration
- **[Administration System](administration-system.md)** - System administration and monitoring procedures

**Development Documentation:**
- **[Sprint History](../planning/sprint_history/)** - Evolution of Pattern Discovery across sprints 18-23
- **[Wireframes](../planning/sprint_history/sprint18/wireframe-pattern-discovery-dashboard.md)** - Original visual design specifications
- **[UI Design](../planning/sprint_history/sprint18/pattern-discovery-ui-design.md)** - Technical design concepts and implementation approach

---

**Last Updated**: 2025-09-07  
**Version**: Production Guide v1.0  
**Contact**: TickStock.ai Development Team  
**Status**: Active Production Feature ✅